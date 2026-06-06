# AGENTS.md

This file provides guidance to agents when working with code in this repository.

## Repository Type
Full-stack Python application - IBM Guardium Cryptography Manager MCP Server integration with LangGraph agent.

## Recent Updates (2026-06-06)

### Investigated 405 Method Not Allowed and Execute JSON Parsing Errors (2026-06-06 05:43 UTC)

**Root Cause Summary:**

1. **`policy_violations_dashboard` 405 is server-side, not client-side**
   - The tool exists and is exposed in both discovery and standard modes
   - Runtime logs show the remote MCP server calling:
     `GET /ibm/gempolicyengine/api/v1/violations/dashboards/policy-violations`
   - The local client does **not** choose the REST method; `langchain-mcp-adapters` forwards MCP tool calls to the MCP server, and the MCP server/tool schema determines the backend HTTP method
   - Repository reference files also map `violations.dashboard` to `GET`, so the 405 indicates a mismatch between the remote server's tool mapping and what the backend currently accepts

2. **`execute` JSON parsing errors were caused by malformed workflow payloads**
   - The `execute` tool receives workflow definitions from the LLM
   - Local client code previously forwarded these payloads without validating or normalizing JSON-string workflow bodies
   - Errors like:
     - `Expected a newline after line continuation character`
     - `Expected '}', found ')'`
     indicate malformed JSON generated before or during tool invocation, not an HTTP transport issue

**Client-Side Fix Applied (`gcm_agent/mcp/client.py`):**
- Added `_normalize_execute_arguments()` to:
  - validate execute payload shape
  - parse JSON strings under common wrapper keys (`workflow`, `input`, `payload`)
  - reject malformed JSON early with actionable byte-position errors
  - require a workflow object containing at least `tool_name`
- Enhanced `execute_tool()` logging to record normalized payloads and failure context
- Added targeted error enrichment for `policy_violations_dashboard` 405 failures so logs clearly indicate likely remote MCP server schema/method mismatch

**What This Fix Does NOT Change:**
- It does **not** change the HTTP method used for `policy_violations_dashboard`
- That method is controlled by the remote GCM MCP server/tool schema, not by `GCMMCPClient`

**Verification:**
- `python -m py_compile gcm_agent/mcp/client.py` ✓
- `python test_execute_tool_fix_unit.py` ✓
- `python test_tuple_result_fix.py` ✓

**Operational Recommendation:**
- For `policy_violations_dashboard`, verify and correct the remote GCM MCP server tool mapping/schema for `/ibm/gempolicyengine/api/v1/violations/dashboards/policy-violations`
- For discovery mode `execute`, keep prompts steering the LLM away from `execute` for simple retrieval queries and rely on the new client-side validation for malformed workflow payloads
### Fixed Intermittent SSL Certificate Verification Error (2026-06-06 07:30 UTC)

**Root Cause:**
The intermittent SSL certificate verification error (`[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: self-signed certificate`) was caused by `KeycloakAuthenticator` in `gcm_agent/auth/keycloak_auth.py` explicitly passing `verify=self.verify_ssl` to `httpx.AsyncClient()` on lines 104 and 174.

**Why This Caused Intermittent Errors:**
1. The module-level SSL bypass patch in `gcm_agent/__init__.py` only applies when the `verify` parameter is NOT in kwargs or is None
2. When `verify_ssl=True` (the default), `keycloak_auth.py` was passing `verify=True` explicitly
3. This overrode the module-level SSL bypass patch, causing SSL verification to be enabled
4. The "randomness" was due to timing - errors occurred when Keycloak authentication happened (token request/refresh)
5. `gcm_auth.py` was already fixed (SSL_BYPASS_FIX.md), but `keycloak_auth.py` was missed

**The Error Chain:**
```
KeycloakAuthenticator.get_token() or .refresh_token()
  ↓
httpx.AsyncClient(verify=self.verify_ssl)  # verify=True overrides module-level patch
  ↓
SSL verification enabled despite module-level bypass
  ↓
[SSL: CERTIFICATE_VERIFY_FAILED] for self-signed certificates
```

**The Fix (gcm_agent/auth/keycloak_auth.py):**
Modified two methods to NOT pass `verify` parameter when `verify_ssl=False`:

1. `get_token()` (lines 103-112): Only passes `verify=True` when `verify_ssl=True`
2. `refresh_token()` (lines 173-182): Only passes `verify=True` when `verify_ssl=True`

**Key Pattern (matches gcm_auth.py):**
```python
# WRONG - Always overrides module-level patch
client = httpx.AsyncClient(verify=self.verify_ssl)

# CORRECT - Let module-level patch apply when verify_ssl=False
client_kwargs = {}
if self.verify_ssl:
    client_kwargs["verify"] = True  # Only when explicitly needed
client = httpx.AsyncClient(**client_kwargs)
```

**Verification:**
- Test script: `test_keycloak_ssl_bypass_fix.py` ✓
- Confirms `get_token()` and `refresh_token()` respect module-level SSL bypass
- Confirms SSL verification can still be enabled when needed (production)

**Complete SSL Bypass Coverage:**
All httpx.AsyncClient creation points now respect module-level SSL bypass:
- ✓ `gcm_agent/__init__.py` - Module-level patch applied at import time
- ✓ `gcm_agent/auth/gcm_auth.py` - Fixed in SSL_BYPASS_FIX.md (2026-06-06 07:17 UTC)
- ✓ `gcm_agent/auth/keycloak_auth.py` - Fixed in this update (2026-06-06 07:30 UTC)
- ✓ `gcm_agent/mcp/client.py` - No direct httpx.AsyncClient creation (uses factory)


### Fixed SSL Certificate Verification Error (2026-06-06 07:17 UTC)

**Root Cause:**
The `_client_factory()` method in `gcm_auth.py` was explicitly passing `verify=verify_ssl` to `httpx.AsyncClient()`, which overrode the module-level SSL bypass patch when `verify_ssl=True` (the default). The module-level patch in `gcm_agent/__init__.py` only applies when the `verify` parameter is NOT in kwargs or is None.

**The Error:**
```
Error calling tool 'gcm_AssetInventoryService_FetchCryptoObjectDetails':
Request error (ConnectError): [SSL: CERTIFICATE_VERIFY_FAILED]
certificate verify failed: self-signed certificate (_ssl.c:1004)
```

**The Fix (gcm_agent/auth/gcm_auth.py):**
Modified three methods to NOT pass `verify` parameter when SSL bypass is needed:

1. `_client_factory()` (lines 374-407): Only passes `verify=True` when `verify_ssl=True`
2. `authorize()` (lines 180-196): Only passes `verify=True` when `verify_ssl=True`
3. `create_authenticated_client()` (lines 228-247): Only passes `verify=True` when `verify_ssl=True`

**Key Pattern:**
```python
# WRONG - Always overrides module-level patch
client = httpx.AsyncClient(verify=verify_ssl)

# CORRECT - Let module-level patch apply when verify_ssl=False
client_kwargs = {}
if verify_ssl:
    client_kwargs["verify"] = True  # Only when explicitly needed
client = httpx.AsyncClient(**client_kwargs)
```

**Verification:**
- Test script: `test_ssl_bypass_fix.py` ✓
- All three methods now respect module-level SSL bypass
- SSL verification can still be enabled when needed (production)

### Fixed AttributeError: 'coroutine' object has no attribute 'value'

**Root Cause:**
The `execute_tool()` method in `GCMMCPClient` was not properly handling the return format from `langchain-mcp-adapters` tools. The library returns a `(content, artifact)` tuple when `response_format="content_and_artifact"` is set, but the code was trying to access a non-existent `.value` attribute.

**The Error Chain:**
1. `tool.ainvoke()` returns a tuple: `(content, artifact)`
2. Old code tried to access `result.value` → AttributeError
3. Error message: "AttributeError: 'coroutine' object has no attribute 'value'"

**The Fix (gcm_agent/mcp/client.py lines 441-470):**
```python
# Execute the tool with unwrapped arguments
result = await tool.ainvoke(unwrapped_arguments)

# Check if result is a coroutine and await it
if inspect.iscoroutine(result):
    result = await result

# LangChain MCP adapter returns (content, artifact) tuple
# Extract just the content part for the agent
if isinstance(result, tuple) and len(result) == 2:
    content, artifact = result
    actual_result = content
else:
    actual_result = result

return actual_result
```

**What Changed:**
1. Added coroutine detection and awaiting (handles async tools)
2. Added tuple unpacking to extract `content` from `(content, artifact)`
3. Removed incorrect `.value` attribute access
4. Added detailed logging to debug result structure

**Verification:**
- Unit tests: `test_execute_tool_fix_unit.py` ✓
- Integration tests: `test_tuple_result_fix.py` ✓
- Handles both standard and discovery mode tools
- Works with coroutines that return tuples

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

### Fixed "Need More Steps" Issue for Broad Queries

**Root Cause:**
The agent was hitting recursion limits when processing broad queries like "show me all keys" or "list all assets". The default `max_iterations=10` was insufficient for discovery mode workflows, which require ~15-20 iterations for complex queries that involve multiple tool calls and data aggregation.

**The Fix (Hybrid Approach):**
Applied a two-part solution in [`gcm_agent/config/config_manager.py`](gcm_agent/config/config_manager.py):

1. **Increased `max_iterations` from 10 to 20** (line 203)
   - Allows complex queries to complete without hitting recursion limit
   - Discovery mode workflows typically need 15-20 iterations
   - Handles broad queries like "all keys/assets" that require multiple tool calls

2. **Changed `discovery_mode` default from True to False** (line 197)
   - Reduces iteration count for common queries (standard mode loads all tools upfront)
   - Discovery mode now opt-in for complex scenarios requiring dynamic tool loading
   - Provides faster responses for typical use cases

**When to Enable Discovery Mode:**
- Complex queries requiring dynamic tool selection
- Workflows that benefit from sandboxed execution with RBAC
- Scenarios where loading all 26 tools upfront is unnecessary

**When to Keep Discovery Mode Disabled (Default):**
- Standard queries with known tool requirements
- Performance-critical scenarios requiring fast responses
- Simple operations that don't need dynamic tool loading

**Configuration:**
### Fixed Discovery Mode Execute Tool Misuse (2026-06-06)

**Root Cause:**
The LLM was incorrectly using the `execute` tool for simple data retrieval queries like "get all certificates" or "fetch policy violations dashboard". The `execute` tool is meant for complex multi-step workflows, not simple queries. This caused errors:
- "Unknown tool: list_tools" - execute tool trying to call non-existent tools
- "NameError: name 'params' is not defined" - bugs in execute tool's internal code

**The Problem:**
The discovery mode prompt was instructing the LLM to use the workflow:
1. search_tools → 2. get_schema → 3. **execute** (WRONG for simple queries)

**The Fix:**
Updated discovery mode prompt in [`gcm_agent/agent/prompts.py`](gcm_agent/agent/prompts.py) to clarify:
- **Simple queries**: search_tools → get_schema → **call tool directly**
- **Complex workflows**: use execute tool for multi-step operations
- Added explicit warning: "DO NOT use execute tool for simple data retrieval"
- Added example workflow showing direct tool calls

**Impact:**
- LLM now calls tools directly for simple queries (faster, more reliable)
- Execute tool reserved for advanced scenarios requiring sandboxed execution
- Eliminates "Unknown tool" and "NameError" errors from execute tool bugs

**Recommendation:**
Keep discovery mode disabled (default) for most use cases. Enable only when:
- Dynamic tool discovery is required
- Complex workflows need sandboxed execution
- RBAC enforcement at tool execution level is needed

Users can override defaults via the configuration UI or by modifying `AgentConfig` in stored configuration.

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