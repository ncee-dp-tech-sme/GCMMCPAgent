# AGENTS.md

This file provides guidance to agents when working with code in this repository.

## Repository Type
Full-stack Python application - IBM Guardium Cryptography Manager MCP Server integration with LangGraph agent.

## Recent Updates (2026-06-06)

### OpenAI LLM Support Added
- Added OpenAI as an alternative LLM provider alongside WatsonX
- New configuration models: `OpenAIConfig`, `LLMConfig` in `config_manager.py`
- Agent now supports both providers via `llm_provider` parameter
- Environment variables: `LLM_PROVIDER`, `OPENAI_API_KEY`, `OPENAI_MODEL`, `OPENAI_TEMPERATURE`, `OPENAI_MAX_TOKENS`
- Easy switching between providers via configuration

### Connection Stability Analysis
**Investigation Result: Architecture is CORRECT - No bug found**

After thorough analysis of the intermittent 500/SSL errors reported after the first operation:

1. **Token Lifecycle Management is Properly Implemented:**
   - `GCMAuthenticator` tracks token expiration with 60-second buffer
   - `_check_and_refresh_token()` called before ALL MCP operations (connect, get_tools, execute_tool)
   - Token refresh properly recreates MCP client with new factory via `reconnect_with_new_factory()`
   - Token info updated after refresh with new expiration time

2. **MCP Client Reuse is Correct:**
   - Single MCP client instance created during agent initialization
   - Same client reused for all tool calls throughout session
   - No unnecessary recreation between tool calls
   - Client only recreated when token expires (which is correct behavior)

3. **x-gcm-hostname Header Propagation is Fixed:**
   - Header injected at factory level in `_client_factory()`
   - Persists through token refresh cycles
   - Passed to factory during both initial creation and token refresh

**Potential Issues to Monitor:**
- If errors persist, they may be server-side (GCM server instability)
- Network connectivity issues between client and GCM server
- Token refresh timing edge cases (though 60-second buffer should prevent this)

**Recommendation:** Test with both WatsonX and OpenAI to isolate whether issues are LLM-specific or MCP-specific.

## Non-Obvious Integration Patterns

### GCM MCP Server Authentication (Two-Step Flow)
- **Critical**: Must obtain OAuth2 token from Keycloak FIRST, then authorize with GCM user management endpoint
- Token must be injected into httpx.AsyncClient headers via custom `_client_factory()`
- Both steps required - missing either causes silent auth failure

### GCM Hostname Header Requirement
- **Critical**: MCP server requires `x-gcm-hostname` header to construct internal API URLs
- Without this header, internal calls use placeholder hostname (e.g., `asset`) causing 400/500 errors
- Must pass actual GCM hostname (not full URL) in MCP client headers
- Example: `"x-gcm-hostname": "gcm.example.com"` for URL `https://gcm.example.com:9443`

**Root Cause of Header Propagation Bug:**
- Header was only configured in MCP client initialization (`GCMMCPClient.__init__`)
- MCP protocol layer creates its own httpx.AsyncClient instances for API calls
- Header was NOT injected into the httpx client factory, causing it to be lost
- Result: GCM server received requests without hostname, defaulted to placeholder `asset`

**The Fix (3 files modified):**
1. [`gcm_agent/auth/gcm_auth.py`](gcm_agent/auth/gcm_auth.py):
   - Added `gcm_hostname` parameter to `_client_factory()` method
   - Factory now injects `x-gcm-hostname` header into ALL httpx requests
   - Updated docstring to document hostname parameter
2. [`gcm_agent/auth/__init__.py`](gcm_agent/auth/__init__.py):
   - Updated `get_client_factory()` to pass `gcm_config.hostname` to factory
3. [`gcm_agent/mcp/client.py`](gcm_agent/mcp/client.py):
   - Updated `reconnect_with_new_factory()` to pass `self.gcm_hostname` during token refresh
   - Ensures header persists through token refresh cycles

**How It Works:**
- Header injected at factory level (not just MCP config level)
- Factory creates httpx.AsyncClient with header pre-configured
- All HTTP requests (initial + token refresh) include correct hostname
- Pattern ensures header survives token lifecycle management

**Verification:**
- Test script: [`test_gcm_hostname_fix.py`](test_gcm_hostname_fix.py) validates header propagation
- Confirms header present in both initial requests and post-refresh requests

### SSL Bypass Implementation (Module-Level)
- **Critical**: SSL bypass MUST be applied at module import time in `gcm_agent/__init__.py`
- MCP library creates its own httpx.AsyncClient instances for protocol connections (SSE transport)
- Application-level `_client_factory()` only affects GCM API calls, NOT MCP handshake
- Solution: Patch `httpx.AsyncClient.__init__` globally before any MCP imports
- Patch automatically sets `verify=False` unless explicitly overridden with `verify=True`
- Applied in `gcm_agent/__init__.py` so ALL imports benefit (tests, app, modules)
- Without module-level patch: SSL errors occur during MCP protocol handshake

### MCP Client Configuration Gotchas
- `langchain-mcp-adapters` requires `streamable_http` transport for remote GCM server
- SSL verification enabled by default - handled by module-level SSL bypass in `gcm_agent/__init__.py`
- Custom `_client_factory()` still needed for token injection and header management

### LangChain MCP Adapter Parameter Wrapping
- **Critical**: LangChain MCP adapter wraps tool parameters in nested `{"params": {...}}` structure
- GCM MCP server expects flat parameters: `{"arg1": val1, "arg2": val2}`
- Without unwrapping, causes Pydantic validation errors: "Field required" for all parameters
- Fix: `_unwrap_params()` method in `GCMMCPClient.execute_tool()` automatically detects and flattens
- Unwrapping is transparent - handles both wrapped and flat parameter structures
- Example: `{"params": {"asset_category": "key"}}` → `{"asset_category": "key"}`

### Tool Loading Pattern
- GCM MCP exposes 26 tools via `MultiServerMCPClient.get_tools()`
- Tools must be loaded during agent initialization, not runtime (performance)
- Multiple MCP servers (e.g., GCM + Slack) combine tools via list concatenation

### Discovery Mode (x-mcp-code-mode header)
- `true`: Returns 4 discovery tools + 1 execute tool (search, get_schema, list_tools, tags, execute)
- `false`/omitted: Returns all 26 application tools (standard mode)
- Discovery tools enable dynamic tool loading - agent searches/loads only needed tools
- Execute tool runs workflows in sandboxed environment with RBAC enforcement

### LangGraph Agent Structure
- Must use `create_agent()` wrapper, not raw LLM
- Agent node must be async: `async def agent_node(state: MessagesState)`
- Graph structure: START → agent → END (no tool node needed - handled internally)
- History management: append HumanMessage, extract AI messages without tool_calls

### System Prompt Requirements
- Must explicitly instruct to "present ACTUAL VALUES" not field descriptions
- Without this, LLM paraphrases schema instead of showing real data
- Multi-server prompts must specify which tools for which system

### Environment Variables
- GCM requires: GCM_URL, GCM_HOSTNAME, USERNAME, PASSWORD, CLIENT_ID, CLIENT_SECRET
- Keycloak: KEYCLOAK_PORT (default 443), REALM (default "master")
- WatsonX: LLM_WATSONX_API_KEY, LLM_WATSONX_PROJECT_ID, WATSONX_MODEL
- Slack (if used): SLACK_BOT_TOKEN, SLACK_TEAM_ID

### Token Lifecycle Management
- **Critical**: OAuth2 tokens expire and must be refreshed to maintain operation
- Token expiration tracked in `GCMAuthenticator` with 60-second buffer before expiry
- Automatic refresh via `_check_and_refresh_token()` called before all MCP operations
- Authenticator instance passed through stack: `get_client_factory()` → `GCMMCPClient.__init__()`
- `_client_factory()` uses current token from authenticator (not cached at factory creation)
- When token expires, `reconnect_with_new_factory()` recreates MCP client with fresh token
- Pattern prevents intermittent SSL/500 errors after 5-15 minutes of operation
- Token refresh is transparent - no user intervention required

### RBAC Configuration (charts/aim-mcp-server/values.yaml)
- `default_behaviour: enabled` - all tools visible by default
- Tag-level control: enable/disable entire OpenAPI tag groups
- Exclusion lists: allow/disallow specific tools within enabled tags
- Applied at tool call time, not discovery time