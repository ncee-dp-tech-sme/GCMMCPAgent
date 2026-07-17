# GCM Agent - IBM Guardium Cryptography Manager AI Assistant

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.9.6-blue.svg)](CHANGELOG.md)

An AI-powered assistant that provides natural language interaction with IBM Guardium Cryptography Manager (GCM) through its embedded Model Context Protocol (MCP) server.

Still work in progress and sometimes unreliable and unstable. Please install and test what tools do work for you.  Tools usually working are:
- fetch all assets
- fetch details of the asset with asset id xxx
- fetch all assets discovered in the last x days
- show details of certificate with crypto id x

## Overview

The GCM Agent enables you to manage cryptographic assets, query key information, and perform complex operations using conversational commands instead of navigating through traditional interfaces. Built with LangChain and LangGraph, it provides an intelligent, secure, and user-friendly way to interact with GCM.

### Key Features

- 🗣️ **Natural Language Interface** - Ask questions and give commands in plain English
- 🔒 **Secure Credential Storage** - All sensitive data encrypted with Fernet encryption and stored locally
- 🔐 **Flexible Authentication** - OAuth2 flow with Keycloak **or** direct API key mode (`token_type: api_key`)
- 🔍 **Dynamic Tool Discovery** - Automatically loads only the tools you need for optimal performance
- 💻 **Local Execution** - Runs entirely on your machine without cloud dependencies
- 📝 **Conversation History** - Maintains context across multiple interactions
- 💾 **Export Capabilities** - Save conversations for documentation or review
- 🎨 **User-Friendly UI** - Gradio-based web interface for configuration, chat, and debugging
- 🚀 **Handles Complex Queries** - Efficiently processes broad queries like "show me all keys" or "list all assets"
- 📊 **Tool Analytics** - Intelligent tool prioritization based on usage patterns (Phase 3)
- 🔍 **Observability** - Comprehensive logging for debugging and monitoring (Phase 4)
- 💰 **Token Tracking** - Monitor LLM costs with detailed token usage metrics (Phase 4)
- ⚡ **Performance Monitoring** - Real-time performance metrics and timing analysis (Phase 4)
- 📋 **Automatic Table Formatting** - Tabular data automatically rendered as styled HTML tables for improved readability

### Architecture Highlights

```
┌─────────────────────────────────────────────────────────────┐
│                      User Interface (Gradio)                 │
│          Configuration │ Chat │ Debug Dashboard              │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                   LangGraph Agent Core                       │
│         (IBM WatsonX or OpenAI LLM Backend)                  │
│         + Observability Logger (Phase 4)                     │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                  MCP Client Layer                            │
│         (Discovery Mode │ Standard Mode)                     │
│         + Tool Analytics (Phase 3)                           │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│              GCM MCP Server                                  │
│         (26 Tools │ 5 Discovery Tools)                       │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│         IBM Guardium Cryptography Manager                    │
│              (REST APIs)                                     │
└─────────────────────────────────────────────────────────────┘
```

For detailed architecture information, see [`docs/architecture/GCM-Agent-Architecture.md`](docs/architecture/GCM-Agent-Architecture.md).

## Quick Start

### Prerequisites

- **Python 3.10+** installed on your system
- **IBM Guardium Cryptography Manager** access with valid credentials
- **WatsonX/openai credentials** (API key and project ID)
- **Network connectivity** to GCM server and WatsonX services

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd GCMMCPAgent

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install package in development mode
pip install -e .
```

### Launch the Application

```bash
# Start the GCM Agent
python app.py
```

The application will start on `http://localhost:7860`

### Configure and Use

1. **Open your browser** to `http://localhost:7860`
2. **Navigate to the ⚙️ Configuration tab**
3. **Enter your settings**:
   - **Keycloak Server**: Authentication server URL, port, realm, and SSL verification
   - **GCM Server**: GCM MCP server URL, hostname, SSL verification, and optional tag filter
   - **Authentication**: Choose **Authentication Mode**:
     - **oauth2** (default): Username, password, client ID, and client secret (stored securely)
     - **api_key**: GCM API key only — Keycloak/password fields not required
   - **LLM Provider**: Choose between WatsonX or openai
     - **WatsonX**: API key, project ID, and model selection
     - **openai**: API key, model name, temperature, and max tokens
   - **Agent Settings**: Discovery mode, max iterations, and timeout
4. **Click 💾 Save Configuration**
5. **Test your connection** with 🔌 Test Connection
6. **Switch to the 💬 Chat tab**
7. **Click 🚀 Initialize Agent**
8. **Start chatting!**
9. **Monitor performance** in the 🔍 Debug tab (optional)

Example conversation:
```
You: List all cryptographic keys
Agent: I'll retrieve the list of keys from GCM for you.
      [Lists all keys with details]

You: Show me details for AES-256-Key-001
Agent: [Displays comprehensive key information]

You: Create a new RSA-2048 key named "API-Key-001"
Agent: [Creates key and confirms success]
```

## Documentation

### User Documentation

- **[User Guide](docs/USER_GUIDE.md)** - Complete usage documentation
  - Introduction and features
  - Configuration guide
  - Using the agent
  - Advanced features
  - Best practices
  - FAQ

- **[Setup Guide](docs/SETUP.md)** - Installation and configuration
  - System requirements
  - Step-by-step installation
  - Configuration wizard
  - Verification steps
  - Deployment options

- **[Troubleshooting Guide](docs/TROUBLESHOOTING.md)** - Common issues and solutions
  - Authentication issues
  - Configuration problems
  - MCP connection issues
  - Agent execution errors
  - Performance optimization
  - Logging and diagnostics

### Technical Documentation

- **[Architecture Documentation](docs/architecture/GCM-Agent-Architecture.md)** - Technical design
  - Component architecture
  - Authentication flow
  - Tool discovery mechanism
  - Security considerations
  - Implementation guidelines

- **[AGENTS.md](AGENTS.md)** - Integration patterns and guidelines
  - GCM MCP server authentication
  - MCP client configuration
  - Tool loading patterns
  - Discovery mode details
  - LangGraph agent structure

## Project Structure

```
GCMMCPAgent/
├── gcm_agent/              # Main package
│   ├── __init__.py
│   ├── config/             # Configuration management
│   │   ├── config_manager.py    # Secure config with Pydantic models
│   │   └── storage.py           # Fernet encryption storage
│   ├── auth/               # Authentication
│   │   ├── keycloak_auth.py     # OAuth2 token retrieval
│   │   └── gcm_auth.py          # GCM authorization
│   ├── mcp/                # MCP client integration
│   │   ├── client.py            # MCP client with auth injection
│   │   └── tool_loader.py       # Dynamic tool loading
│   ├── agent/              # LangGraph agent
│   │   ├── gcm_agent.py         # Agent orchestration
│   │   └── prompts.py           # System prompts
│   ├── ui/                 # Gradio interfaces
│   │   ├── config_ui.py         # Configuration interface
│   │   └── chat_ui.py           # Chat interface
│   └── utils/              # Utilities
│       └── logger.py            # Logging configuration
├── docs/                   # Documentation
│   ├── USER_GUIDE.md            # User documentation
│   ├── SETUP.md                 # Installation guide
│   ├── TROUBLESHOOTING.md       # Troubleshooting guide
│   └── architecture/            # Technical documentation
│       └── GCM-Agent-Architecture.md
├── tests/                  # Test suite
│   ├── test_config.py           # Configuration tests
│   ├── test_auth.py             # Authentication tests
│   ├── test_mcp.py              # MCP client tests

## Recent Updates

### Phase 4: Observability & Debugging (2026-06-08)

**Comprehensive observability features for better debugging and monitoring:**

- **Structured Logging** - JSON-formatted logs for tool selection, execution, tokens, and performance
- **Tool Selection Reasoning** - Captures LLM decision-making process during tool selection
- **Token Usage Tracking** - Monitor prompt/completion/total tokens per query and cumulatively
- **Performance Monitoring** - Automatic timing of operations with `@timed_operation` decorator
- **Debug Dashboard** - New 🔍 Debug tab with real-time metrics visualization
- **Session Tracking** - Unique session IDs for correlating logs across operations

**Key Benefits:**
- <1ms logging overhead per operation
- Zero configuration required - works automatically
- Structured JSON logs for easy parsing
- Real-time monitoring via Debug Dashboard

See [`docs/PHASE4_COMPLETION_SUMMARY.md`](docs/PHASE4_COMPLETION_SUMMARY.md) for complete details.

### Phase 3: Tool Management & Analytics (2026-06-08)

**Intelligent tool prioritization and usage analytics:**

- **Tool Usage Analytics** - Tracks execution frequency, success rates, and duration
- **Intelligent Prioritization** - Most-used tools presented first to LLM for faster selection
- **Force Refresh** - Manual cache invalidation for dynamic tool updates
- **Analytics Integration** - Automatic tracking with <1ms overhead
- **Persistent Storage** - Analytics saved in `~/.gcm_agent/tool_analytics.json`

**Expected Impact:**
- 20-30% faster tool selection with analytics data
- Data-driven insights for optimization
- Better cache control and flexibility

See [`docs/PHASE3_COMPLETION_SUMMARY.md`](docs/PHASE3_COMPLETION_SUMMARY.md) for complete details.

│   └── test_agent.py            # Agent tests
├── app.py                  # Main entry point
├── requirements.txt        # Python dependencies
├── setup.py                # Package setup
  ├── ui/                 # Gradio interfaces
  │   ├── config_ui.py         # Configuration interface
  │   ├── chat_ui.py           # Chat interface
  │   └── debug_ui.py          # Debug dashboard (Phase 4)
  ├── mcp/                # MCP client integration
  │   ├── client.py            # MCP client with auth injection
  │   ├── tool_loader.py       # Dynamic tool loading + analytics (Phase 3)
  │   └── tool_analytics.py    # Tool usage analytics (Phase 3)
├── .env.example            # Configuration reference
├── AGENTS.md               # Integration guidelines
└── README.md               # This file
```

## Features in Detail

### Secure Configuration Management

- **Fernet Encryption Storage**: Credentials encrypted with Fernet and stored in `~/.gcm_agent/` with restrictive permissions
- **No Environment Variables**: Security-first approach prevents credential exposure
- **Pydantic Validation**: Type-safe configuration with automatic validation
- **Thread-Safe Singleton**: Consistent configuration access across components

### Authentication Modes

The agent supports two authentication modes, selectable per connection:

**OAuth2 mode (default)** — two-step flow:
1. **Keycloak OAuth2**: Obtain access token from Keycloak server
2. **GCM Authorization**: Authorize with GCM user management endpoint
3. **Token Injection**: Custom `_client_factory()` injects token into MCP client headers
4. **Automatic Refresh**: Token management handled transparently

**API Key mode** — single-step:
1. Set **Authentication Mode** to `api_key` in the Configuration UI (or `AUTH_MODE=api_key` in `.env`)
2. Enter your **GCM API Key** — stored securely in the same Fernet-encrypted store
3. The key is placed directly in `Authorization: Bearer <api_key>` and the additional header `token_type: api_key` is sent to the MCP server
4. Keycloak, password, and client secret fields are not required and can be left empty

**Tag Filtering (both modes)**:
- Set **Filtered Tags** in the GCM Server tab to restrict which tool groups the MCP server exposes
- Sent as the `X-MCP-Filtered-Tags` header (e.g. `Transformation,Ansible`)
- Leave empty to expose all tools (default)

### Dynamic Tool Discovery

**Discovery Mode**:
- Starts with 5 discovery tools (search, get_schema, list_tools, tags, execute)
- Dynamically loads only needed tools based on user queries
- Faster initialization and reduced memory footprint
- Optimal for complex scenarios requiring dynamic tool selection
- **Note:** Discovery mode is now disabled by default for better performance on common queries

**Standard Mode (Default)**:
- Loads all 26 GCM tools upfront
- Immediate access to all capabilities
- Better for repetitive operations and broad queries
- Predictable tool availability
- **Recommended for most use cases** - handles queries like "show me all keys" efficiently
- Agent configured with 20 max iterations to handle complex multi-step operations

### LangGraph Agent Architecture

- **State Management**: [`MessagesState`](https://langchain-ai.github.io/langgraph/reference/graphs/#langgraph.graph.MessagesState) for conversation history
- **Agent Wrapper**: [`create_agent()`](https://python.langchain.com/docs/modules/agents/) from LangChain
- **Graph Structure**: Simple linear flow (START → agent → END)
- **Async Execution**: Full async/await support for performance
- **Streaming Responses**: Real-time response streaming to UI

## Requirements

### System Requirements

- **Python**: 3.10 or higher
- **Operating System**: macOS 10.15+, Linux (Ubuntu 20.04+, RHEL 8+), Windows 10+
- **Memory**: 4 GB RAM minimum (8 GB recommended)
- **Disk Space**: 2 GB free space
- **Network**: Internet connectivity for WatsonX and GCM access

### Python Dependencies

Core dependencies (see [`requirements.txt`](requirements.txt) for complete list):

```
langchain>=0.1.0           # LangChain framework
langgraph>=0.0.40          # Agent orchestration
langchain-ibm>=0.1.0       # IBM WatsonX integration
langchain-openai>=0.1.0    # openai integration
langchain-mcp-adapters     # MCP protocol support
httpx>=0.25.0              # Async HTTP client
pydantic>=2.0.0            # Data validation
cryptography>=41.0.0       # Fernet encryption for credentials
gradio>=4.0.0              # Web UI framework
pytest>=7.4.0              # Testing framework
```

### Access Requirements

- **GCM Server**: URL, hostname, and either:
  - **OAuth2 mode**: valid GCM username, password, Keycloak client ID and secret
  - **API key mode**: GCM API key only
- **Keycloak** *(OAuth2 mode only)*: client ID and secret, realm information

## LLM Provider Configuration

The GCM Agent supports two LLM providers: **IBM WatsonX** and **openai**. You can easily switch between them via the Configuration UI or environment variables.

### Choosing a Provider

**IBM WatsonX** (Default):
- Enterprise-grade AI platform
- Requires WatsonX API key and project ID
- Supports multiple IBM foundation models
- Best for IBM ecosystem integration

**openai**:
- Industry-leading language models (GPT-4, GPT-3.5-turbo, etc.)
- Requires openai API key
- Configurable temperature and token limits
- Best for general-purpose AI tasks

### Configuration via UI

1. Navigate to the **⚙️ Configuration** tab
2. In the **LLM Configuration** section:
   - Select your preferred provider from the dropdown
   - **For WatsonX**: Enter API key, project ID, and select model
   - **For openai**: Enter API key, model name (e.g., `gpt-4`), temperature (0.0-1.0), and max tokens
3. Click **💾 Save Configuration**
4. Re-initialize the agent to apply changes

### Configuration via Environment Variables

Add to your `.env` file:

**For WatsonX:**
```bash
LLM_PROVIDER=watsonx
LLM_WATSONX_API_KEY=your_watsonx_api_key
LLM_WATSONX_PROJECT_ID=your_project_id
WATSONX_MODEL=ibm/granite-13b-chat-v2
```

**For openai:**
```bash
LLM_PROVIDER=openai
openai_API_KEY=your_openai_api_key
openai_MODEL=gpt-4
openai_TEMPERATURE=0.7
openai_MAX_TOKENS=4096
```

### Switching Providers

To switch between providers:
1. Update the configuration (UI or `.env` file)
2. Restart the application: `python app.py`
3. Re-initialize the agent in the Chat tab

The agent will automatically use the selected provider for all LLM operations.

- **LLM Provider** (choose one):
  - **WatsonX**: API key, project ID, active subscription
  - **openai**: API key, active subscription

## Security Considerations

### Credential Storage

- ✅ **Secure**: Fernet encryption with restrictive file permissions (0o600)
- ✅ **Encrypted**: Credentials encrypted at rest in `~/.gcm_agent/`
- ✅ **Per-User**: Each user has isolated credential storage in their home directory
- ❌ **No Plain Text**: Never stored in plain text files or environment variables

### SSL/TLS

- ✅ **Enabled by Default**: SSL verification enabled for all connections
- ✅ **Certificate Validation**: Validates server certificates against trusted CAs
- ✅ **Independent Settings**: Separate SSL verification for Keycloak and GCM servers
- ⚠️ **Self-Signed Certificates**: Can be disabled for development/testing environments
- ⚠️ **Security Warning**: Disabling SSL verification affects all HTTPS connections in the process

**For Self-Signed Certificates:**

If your GCM or Keycloak servers use self-signed certificates, you can disable SSL verification in the Configuration UI:

1. Navigate to the **⚙️ Configuration** tab
2. Uncheck **"Verify SSL"** for the affected server (Keycloak or GCM)
3. Save the configuration
4. Re-initialize the agent

**Note:** When SSL verification is disabled, the agent applies comprehensive SSL workarounds:
- Modifies default SSL context to disable certificate verification
- Monkey-patches both `httpx.AsyncClient` and `httpx.Client` to force `verify=False`
- Sets environment variables to disable SSL verification
- This affects all HTTPS connections in the process and is logged with a warning

### GCM Hostname Configuration

The GCM MCP server requires the actual hostname to construct internal API URLs. The agent handles this automatically:

- **Automatic Extraction**: If you provide a full URL (e.g., `https://gcm.example.com:9443`), the agent extracts just the hostname (`gcm.example.com`)
- **Direct Input**: You can also provide just the hostname directly
- **Critical Header**: The hostname is passed via the `x-gcm-hostname` header to the MCP server
- **Error Prevention**: Without this header, internal API calls fail with 500 errors using placeholder hostnames like `asset`

**Example Configuration:**
```
GCM URL: https://gcm.apps.example.com:9443
GCM Hostname: gcm.apps.example.com (or full URL - will be extracted automatically)
```

### API Key Authentication

When `auth_mode = api_key` is configured:

- ✅ **Simplified**: No Keycloak server required — single credential to manage
- ✅ **Secure**: API key stored with Fernet encryption alongside other credentials
- ✅ **Headers sent**: `Authorization: Bearer <api_key>` and `token_type: api_key`
- ✅ **No expiry**: API keys are treated as non-expiring — no token refresh cycles
- ⚠️ **Key rotation**: Rotate API keys manually via the Configuration UI when required

### MCP Tag Filtering

The `X-MCP-Filtered-Tags` header controls which tool groups the MCP server exposes:

- **Configure**: Enter comma-separated tag names in the **Filtered Tags** field of the GCM Server tab
- **Example**: `Transformation,Ansible` exposes only tools tagged with those groups
- **Empty (default)**: All tools are exposed — no filter applied
- **Works in both modes**: Tag filtering is independent of the authentication mode used
- **Environment variable**: `MCP_FILTERED_TAGS=Transformation,Ansible`

### RBAC Enforcement

- ✅ **GCM RBAC**: Respects GCM role-based access control
- ✅ **Tool-Level**: Permissions enforced at tool execution time
- ✅ **Audit Trail**: All operations logged in GCM audit logs

### Network Security

- ✅ **Local Execution**: No data sent to third parties (except WatsonX for LLM)
- ✅ **HTTPS Only**: All connections use encrypted HTTPS
- ✅ **Token Management**: Automatic token refresh and expiration handling

## Development

### Running Tests

```bash
# Activate virtual environment
source .venv/bin/activate

# Run all tests
pytest

# Run specific test file
pytest tests/test_config.py

# Run with coverage
pytest --cov=gcm_agent tests/
```

### Verification Scripts

```bash
# Verify configuration system
python verify_config_system.py

# Verify MCP integration
python verify_mcp_integration.py

# Test UI components
python test_ui.py
```

### Code Style

The project follows Python best practices:
- PEP 8 style guide
- Type hints for function signatures
- Docstrings for all public functions
- Pydantic models for data validation

## Deployment

### Local Deployment

Default deployment runs locally on your machine:

```bash
python app.py
# Access at http://localhost:7860
```

### Local Network Deployment

To make accessible on your local network:

```bash
# Already configured in app.py
# Access from other machines at http://<your-ip>:7860
```

### Future: Watsonx Orchestrate Integration

The agent is designed for future integration with Watsonx Orchestrate:
- Modular architecture supports portability
- Configuration abstraction layer
- Standardized API interfaces
- Minimal code changes required for migration

## Troubleshooting

### Quick Fixes

| Issue | Solution |
|-------|----------|
| Can't connect to GCM | Verify URL, test with curl, check network |
| Invalid credentials | Re-enter carefully, test connection |
| SSL certificate errors | Uncheck "Verify SSL" in Configuration for self-signed certs |
| Tool limit exceeded | Enable discovery mode (limits tools to 128 for WatsonX) |
| Encryption errors | Check ~/.gcm_agent/ permissions, regenerate key |
| Slow initialization | Enable discovery mode |
| Agent not responding | Reinitialize agent, check logs |
| Gradio message format error | Update to latest version (fixed in v1.0) |
| "Recursion limit" / "Need more steps" error | Fixed in latest version (unit mismatch between `max_iterations` and LangGraph's `recursion_limit` corrected). Default `max_iterations=30` now yields `recursion_limit=90`. Increase `max_iterations` in config if still needed. |
| AttributeError: 'coroutine' object | Fixed in v2026-06-06 - update to latest version |
| Discovery mode execute tool errors | Fixed in v2026-06-06 - LLM now calls tools directly for simple queries |
| 405 Method Not Allowed errors | Server-side schema mismatch - check GCM MCP server tool mappings |

### Common Error Messages

#### SSL Certificate Verification Failed

**Error:**
```
[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: self-signed certificate
```

**Solution:**
1. Navigate to **⚙️ Configuration** tab
2. Uncheck **"Verify SSL"** for the affected server (Keycloak or GCM)
3. Click **💾 Save Configuration**
4. Return to **💬 Chat** tab and click **🚀 Initialize Agent**

**Technical Details:** The agent applies comprehensive SSL bypass at module level when verification is disabled. See [`SSL_BYPASS_FIX.md`](SSL_BYPASS_FIX.md) for implementation details.

#### Agent Streaming Errors (Fixed in v2026-06-06)

**Error:**
```
AttributeError: 'coroutine' object has no attribute 'value'
TypeError: 'coroutine' object is not subscriptable
```

**Solution:** These errors were fixed in version 2026-06-06. Update to the latest version:
```bash
git pull origin main
pip install -r requirements.txt
```

**Technical Details:** The fix properly handles tuple unpacking from `langchain-mcp-adapters` tools. See [`JSON_PARSING_ERROR_FIX.md`](JSON_PARSING_ERROR_FIX.md) for details.

#### Discovery Mode Execute Tool Misuse (Fixed in v2026-06-06)

**Error:**
```
Unknown tool: list_tools
NameError: name 'params' is not defined
```

**Solution:** This was fixed in version 2026-06-06 by updating the discovery mode prompt. The LLM now correctly calls tools directly for simple queries instead of misusing the execute tool.

**Recommendation:** Keep discovery mode disabled (default) for most use cases. Enable only for complex workflows requiring dynamic tool selection.

For detailed troubleshooting, see [`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md).

### Logging Configuration

The agent supports configurable logging with environment variables:

**Enable Detailed Logging:**

1. Add to your `.env` file (or set environment variables):
```bash
LOG_LEVEL=DEBUG          # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_TO_FILE=true         # Enable file logging
LOG_DIR=logs             # Directory for log files (default: logs)
```

2. Restart the application:
```bash
python app.py
```

**Log Files:**

When file logging is enabled, logs are stored in the `logs/` directory with daily rotation:

```
logs/
├── config_20260605.log    # Configuration operations
├── auth_20260605.log      # Authentication log
├── mcp_20260605.log       # MCP client operations
├── agent_20260605.log     # Agent execution log
└── ui_20260605.log        # UI-specific log
```

**View Logs:**
```bash
# View all logs
tail -f logs/*.log

# View specific module
tail -f logs/auth_20260605.log

# Search for errors
grep -i error logs/*.log
```

**Log Levels:**
- `DEBUG`: Detailed diagnostic information (verbose)
- `INFO`: General informational messages (default)
- `WARNING`: Warning messages for potential issues
- `ERROR`: Error messages for failures
- `CRITICAL`: Critical errors requiring immediate attention

**Note:** The `logs/` directory is automatically added to `.gitignore` to prevent committing sensitive log data.

## Contributing

Contributions are welcome! Please follow these guidelines:

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/your-feature`
3. **Make your changes** with clear commit messages
4. **Add tests** for new functionality
5. **Update documentation** as needed
6. **Submit a pull request**

### Code Standards

- Follow PEP 8 style guide
- Add type hints to function signatures
- Write docstrings for public functions
- Include unit tests for new features
- Update documentation for user-facing changes

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## Support

### Documentation

- **User Guide**: [`docs/USER_GUIDE.md`](docs/USER_GUIDE.md)
- **Setup Guide**: [`docs/SETUP.md`](docs/SETUP.md)
- **Troubleshooting**: [`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md)
- **Architecture**: [`docs/architecture/GCM-Agent-Architecture.md`](docs/architecture/GCM-Agent-Architecture.md)

### Getting Help

1. **Check Documentation**: Review user guide and troubleshooting guide
2. **Search Issues**: Look for similar issues on GitHub
3. **Create Issue**: Submit detailed bug report or feature request
4. **Contact Support**: Reach out to IBM support team

When reporting issues, include:
- Error messages and logs
- System information (OS, Python version)
- Steps to reproduce
- Configuration details (redact sensitive data)

## Acknowledgments

Built with:
- [LangChain](https://python.langchain.com/) - LLM application framework
- [LangGraph](https://langchain-ai.github.io/langgraph/) - Agent orchestration
- [Gradio](https://www.gradio.app/) - Web UI framework
- [IBM WatsonX](https://www.ibm.com/watsonx) - AI and data platform
- [IBM Guardium Cryptography Manager](https://www.ibm.com/products/guardium-cryptography-manager) - Cryptographic asset management

## Roadmap

### Current Version (1.0)
- ✅ Local deployment with Gradio UI
- ✅ Secure Fernet encryption-based configuration
- ✅ Two-step OAuth2 authentication
- ✅ Dynamic tool discovery
- ✅ LangGraph agent with WatsonX
- ✅ Conversation history and export

### Planned Features
- 🔄 Automatic token refresh
- 🔄 Docker deployment support
- 🔄 Watsonx Orchestrate integration
- 🔄 Multi-user support
- 🔄 Advanced RBAC configuration
- 🔄 Batch operations
- 🔄 Scheduled tasks
- 🔄 Enhanced error recovery

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 0.9.7 | 2026-07-17 | Added API key authentication mode (`token_type: api_key`) and `X-MCP-Filtered-Tags` header support |
| 0.9.6 | 2026-06-09 | Phase 4: Observability & Debugging - Structured logging, token tracking, performance monitoring |
| 0.9.5 | 2026-06-08 | Phase 3: Tool Management & Analytics - Intelligent tool prioritization |
| 0.9.4 | 2026-06-08 | Phase 2: Configuration & Resilience - Configurable LLM parameters, retry logic |
| 1.0.1 | 2026-06-06 | Fixed SSL certificate verification, tuple unpacking, and discovery mode prompt issues |
| 1.0.0 | 2026-06-05 | Initial release with core functionality |

For detailed changelog, see [`docs/CHANGELOG.md`](docs/CHANGELOG.md).

---

**Maintained By:** Erwin Friethoff - Senior Security Architect
**Last Updated:** 2026-07-17
**Version:** 0.9.7