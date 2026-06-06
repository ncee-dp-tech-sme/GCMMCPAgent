# AGENTS.md

This file provides guidance to agents when working with code in this repository.

## Repository Type
Documentation-only repository - contains IBM Guardium Cryptography Manager MCP Server integration guides. No executable code.

## Non-Obvious Integration Patterns

### GCM MCP Server Authentication (Two-Step Flow)
- **Critical**: Must obtain OAuth2 token from Keycloak FIRST, then authorize with GCM user management endpoint
- Token must be injected into httpx.AsyncClient headers via custom `_client_factory()`
- Both steps required - missing either causes silent auth failure

### GCM Hostname Header Requirement
- **Critical**: MCP server requires `x-gcm-hostname` header to construct internal API URLs
- Without this header, internal calls use placeholder hostname (e.g., `asset`) causing 500 errors
- Must pass actual GCM hostname (not full URL) in MCP client headers
- Example: `"x-gcm-hostname": "gcm.example.com"` for URL `https://gcm.example.com:9443`

### MCP Client Configuration Gotchas
- `langchain-mcp-adapters` requires `streamable_http` transport for remote GCM server
- SSL verification enabled by default - custom `_client_factory()` needed to override
- Must pop `verify` kwarg before creating AsyncClient to avoid conflicts

### Tool Loading Pattern
- GCM MCP exposes 26 tools via `MultiServerMCPClient.get_tools()`
- Tools must be loaded during agent initialization, not runtime (performance)
- Multiple MCP servers (e.g., GCM + Slack) combine tools via list concatenation

### Discovery Mode (x-mcp-enable-discovery header)
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