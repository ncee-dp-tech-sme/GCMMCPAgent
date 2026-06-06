# Changelog

All notable changes to the GCM Agent project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
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

[Unreleased]: https://github.com/your-org/gcm-agent/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/your-org/gcm-agent/releases/tag/v1.0.0