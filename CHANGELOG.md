# Changelog

All notable changes to the GCM Agent project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.1] - 2026-06-06

### Fixed
- **Critical**: Fixed "need more steps" error for broad queries
  - Increased `max_iterations` from 10 to 20 in `AgentConfig` default configuration
  - Changed `discovery_mode` default from True to False for better performance on common queries
  - Agent now handles broad queries like "show me all keys" or "list all assets" without hitting iteration limits
  - Discovery mode workflows typically need 15-20 iterations for complex queries with multiple tool calls
  - Standard mode (discovery_mode=False) loads all 26 tools upfront, providing faster responses for typical operations
  - Discovery mode now opt-in for complex scenarios requiring dynamic tool loading and sandboxed execution
  - Modified file: `gcm_agent/config/config_manager.py` (lines 197, 203)
  - Created test script: `test_max_iterations_fix.py` to validate the fix

### Changed
- **Agent Configuration Defaults**: Updated default behavior for better user experience
  - `max_iterations`: 10 → 20 (allows complex multi-step operations to complete)
  - `discovery_mode`: True → False (faster initialization and response times for common queries)
  - Users can still enable discovery mode via Configuration UI for advanced use cases

### Documentation
- Updated `README.md` with information about handling broad queries
- Updated `docs/USER_GUIDE.md` with:
  - New example conversation showing broad query handling
  - Updated Agent Settings section with new defaults and explanations
  - Enhanced Discovery Mode section with configuration change details
  - Guidance on when to use discovery mode vs standard mode
- Updated `docs/TROUBLESHOOTING.md` with comprehensive "Need More Steps" error section
  - Documented the fix and version where it was resolved
  - Provided manual configuration steps for extreme edge cases
  - Added guidance on when to increase max_iterations further
- Updated `AGENTS.md` with technical details about the fix

## [Unreleased]

### Added
- **Comprehensive Header Logging**: Added detailed logging for Authorization Bearer token verification
  - Added token masking in logs (shows first 8 and last 4 characters only)
  - Logs all headers at client factory creation with masked Authorization header
  - Added httpx event hooks to log every outgoing HTTP request with headers
  - Added httpx event hooks to log every HTTP response with status and timing
  - Enhanced `authorize()` method to log authorization requests with masked token
  - Created `test_auth_header_logging.py` to verify logging functionality
  - Helps debug connection issues and verify token is being sent correctly
  - Security: Token never fully exposed in logs, only partial masking for verification

- **OpenAI LLM Support**: Added OpenAI as an alternative LLM provider alongside WatsonX
  - New configuration models: `OpenAIConfig`, `LLMConfig` in `config_manager.py`
  - Agent now supports both providers via `llm_provider` parameter
  - Environment variables: `LLM_PROVIDER`, `OPENAI_API_KEY`, `OPENAI_MODEL`, `OPENAI_TEMPERATURE`, `OPENAI_MAX_TOKENS`
  - Easy switching between providers via Configuration UI or environment variables
  - Added `langchain-openai>=0.1.0` dependency to requirements.txt

### Fixed
- **Critical**: Fixed x-gcm-hostname header propagation through token refresh cycles
  - Header now injected at factory level in `_client_factory()` method
  - Factory passes `gcm_hostname` parameter to ensure header persists
  - Updated `reconnect_with_new_factory()` to pass hostname during token refresh
  - Ensures header survives token lifecycle management
  - Prevents 500 errors caused by missing hostname in MCP requests
  - Modified files: `gcm_agent/auth/gcm_auth.py`, `gcm_agent/auth/__init__.py`, `gcm_agent/mcp/client.py`

- **Critical**: Fixed discovery mode header name
  - Changed from incorrect `x-mcp-enable-discovery` to correct `x-mcp-code-mode`
  - Header values: `"true"` for discovery mode, `"false"` for standard mode
  - Aligns with GCM MCP server API specification
  - Modified file: `gcm_agent/mcp/client.py`

- **Critical**: Fixed syntax error in config_manager.py
  - Corrected malformed dictionary in `OpenAIConfig` model
  - Fixed `Field(default={)` to proper `Field(default={})`
  - Prevents import errors when using OpenAI configuration

- **Critical**: Fixed token refresh to properly update expiration info after refresh
  - `GCMAuthenticator.refresh_token()` now calls `set_token_info()` to update token expiration
  - Retrieves new expiration time from Keycloak authenticator after token refresh
  - Adds 30-second buffer to new expiration time for proactive refresh
  - Includes fallback to 4-minute default if expiration time unavailable
  - Prevents SSL/500 errors that occurred when refreshed token info wasn't updated
  - Completes the token lifecycle management pattern documented in AGENTS.md

- **Critical**: Implemented token refresh mechanism to fix intermittent SSL/500 errors
  - Added token expiration tracking to `GCMAuthenticator` with 60-second buffer
  - Implemented automatic token refresh via Keycloak when token expires
  - Modified `_client_factory()` to use current token from authenticator instance
  - Added `_check_and_refresh_token()` method called before all MCP operations
  - Added `reconnect_with_new_factory()` to recreate MCP client with refreshed token
  - `get_client_factory()` now returns both factory and authenticator for refresh capability
  - `GCMMCPClient` stores authenticator reference and checks token before operations
  - Resolves intermittent authentication failures after 5-15 minutes of operation
  - Token refresh is transparent to the user and maintains connection state

- **Critical**: Fixed SSL certificate verification error in `_client_factory()`
  - Ensured 'verify' kwarg is properly popped before creating AsyncClient (per AGENTS.md pattern)
  - Prevents conflicts when MCP library passes verify parameter
  - Factory now correctly respects verify_ssl setting for self-signed certificates
  - Resolves `[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: self-signed certificate` errors

- **Critical**: Fixed AttributeError in GCMMCPClient initialization
  - Moved logger initialization before hostname extraction logic
  - Prevents "'GCMMCPClient' object has no attribute 'logger'" error
  - Logger now available for all initialization steps

- **Critical**: Fixed 500 Internal Server Error on certificate listing and asset inventory tools
  - Added `x-gcm-hostname` header to MCP client configuration
  - GCM MCP server now receives actual hostname instead of using placeholder (`asset`)
  - Hostname automatically extracted from full URLs if provided
  - Prevents internal API calls from failing with incorrect hostnames

- **Critical**: Moved SSL bypass to application startup for global effect
  - Relocated SSL bypass patch to `app.py` at the very top before ANY imports
  - Patches `httpx.AsyncClient.__init__` before any MCP or httpx usage in the application
  - Removed ineffective module-level patch from `gcm_agent/mcp/client.py`
  - Ensures ALL httpx clients (including MCP internal clients) have SSL bypass applied
  - Resolves persistent SSL verification errors with self-signed certificates
  - Previous module-level patch ran too late - other code imported httpx before patch was applied
  - By patching at application startup, httpx.AsyncClient class is modified before any code uses it

### Changed
- Updated `GCMMCPClient.__init__()` to accept and auto-extract hostname from URLs
- Enhanced SSL workaround to patch both async and sync httpx clients
- Improved logging to show extracted hostname for debugging

### Documentation
- **Connection Stability Analysis**: Added comprehensive analysis to `AGENTS.md`
  - Documented token lifecycle management architecture
  - Confirmed no bugs in connection handling - architecture is correct
  - Identified potential server-side or network issues if errors persist
  - Recommendation to test with both WatsonX and OpenAI to isolate issues
- **OpenAI LLM Support**: Updated `README.md` with new LLM provider section
  - Added LLM Provider Configuration section with detailed setup instructions
  - Updated architecture diagram to show both WatsonX and OpenAI support
  - Updated configuration steps to include LLM provider selection
  - Updated dependencies list to include langchain-openai
  - Updated access requirements to list both LLM providers
- Updated `AGENTS.md` with GCM Hostname Header Requirement section
- Added troubleshooting sections for 500 errors and SSL verification failures
- Updated `SETUP.md` with hostname configuration details and auto-extraction notes
- Enhanced `README.md` with SSL workaround details and hostname configuration
- Created `CHANGELOG.md` to track project changes

## [1.0.0] - 2026-06-05

### Added
- Initial release of GCM Agent
- Natural language interface for IBM Guardium Cryptography Manager
- Secure credential storage with Fernet encryption
- Two-step authentication (Keycloak OAuth2 + GCM authorization)
- Dynamic tool discovery mode
- LangGraph-based agent architecture
- Gradio web UI for configuration and chat
- Comprehensive documentation suite
- Test suite for core components

### Security
- Fernet encryption for credential storage
- SSL/TLS verification enabled by default
- Secure token injection via custom client factory
- Per-user isolated credential storage

[Unreleased]: https://github.com/your-org/gcm-agent/compare/v1.0.1...HEAD
[1.0.1]: https://github.com/your-org/gcm-agent/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/your-org/gcm-agent/releases/tag/v1.0.0