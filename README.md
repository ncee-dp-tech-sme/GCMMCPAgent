# GCM Agent - IBM Guardium Cryptography Manager AI Assistant

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)

An AI-powered assistant that provides natural language interaction with IBM Guardium Cryptography Manager (GCM) through its embedded Model Context Protocol (MCP) server.

## Overview

The GCM Agent enables you to manage cryptographic assets, query key information, and perform complex operations using conversational commands instead of navigating through traditional interfaces. Built with LangChain and LangGraph, it provides an intelligent, secure, and user-friendly way to interact with GCM.

### Key Features

- 🗣️ **Natural Language Interface** - Ask questions and give commands in plain English
- 🔒 **Secure Credential Storage** - All sensitive data encrypted with Fernet encryption and stored locally
- 🔐 **Two-Step Authentication** - OAuth2 flow with Keycloak and GCM user management
- 🔍 **Dynamic Tool Discovery** - Automatically loads only the tools you need for optimal performance
- 💻 **Local Execution** - Runs entirely on your machine without cloud dependencies
- 📝 **Conversation History** - Maintains context across multiple interactions
- 💾 **Export Capabilities** - Save conversations for documentation or review
- 🎨 **User-Friendly UI** - Gradio-based web interface for configuration and chat

### Architecture Highlights

```
┌─────────────────────────────────────────────────────────────┐
│                      User Interface (Gradio)                 │
│                  Configuration │ Chat Interface              │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                   LangGraph Agent Core                       │
│              (IBM WatsonX LLM Backend)                       │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                  MCP Client Layer                            │
│         (Discovery Mode │ Standard Mode)                     │
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
- **WatsonX credentials** (API key and project ID)
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
   - GCM server connection details
   - Authentication credentials (stored securely)
   - WatsonX configuration
   - Agent behavior settings
4. **Click 💾 Save Configuration**
5. **Test your connection** with 🔌 Test Connection
6. **Switch to the 💬 Chat tab**
7. **Click 🚀 Initialize Agent**
8. **Start chatting!**

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
│   └── test_agent.py            # Agent tests
├── app.py                  # Main entry point
├── requirements.txt        # Python dependencies
├── setup.py                # Package setup
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

### Two-Step Authentication

1. **Keycloak OAuth2**: Obtain access token from Keycloak server
2. **GCM Authorization**: Authorize with GCM user management endpoint
3. **Token Injection**: Custom `_client_factory()` injects token into MCP client headers
4. **Automatic Refresh**: Token management handled transparently

### Dynamic Tool Discovery

**Discovery Mode (Recommended)**:
- Starts with 5 discovery tools (search, get_schema, list_tools, tags, execute)
- Dynamically loads only needed tools based on user queries
- Faster initialization and reduced memory footprint
- Optimal for varied operations

**Standard Mode**:
- Loads all 26 GCM tools upfront
- Immediate access to all capabilities
- Better for repetitive operations
- Predictable tool availability

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
langchain-mcp-adapters     # MCP protocol support
httpx>=0.25.0              # Async HTTP client
pydantic>=2.0.0            # Data validation
cryptography>=41.0.0       # Fernet encryption for credentials
gradio>=4.0.0              # Web UI framework
pytest>=7.4.0              # Testing framework
```

### Access Requirements

- **GCM Server**: URL, hostname, valid user credentials
- **Keycloak**: OAuth2 client ID and secret, realm information
- **WatsonX**: API key, project ID, active subscription

## Security Considerations

### Credential Storage

- ✅ **Secure**: Fernet encryption with restrictive file permissions (0o600)
- ✅ **Encrypted**: Credentials encrypted at rest in `~/.gcm_agent/`
- ✅ **Per-User**: Each user has isolated credential storage in their home directory
- ❌ **No Plain Text**: Never stored in plain text files or environment variables

### SSL/TLS

- ✅ **Enabled by Default**: SSL verification enabled for all connections
- ✅ **Certificate Validation**: Validates server certificates
- ⚠️ **Disable for Testing Only**: Can be disabled for development environments

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
| SSL errors | Install CA certificate or disable SSL (testing only) |
| Encryption errors | Check ~/.gcm_agent/ permissions, regenerate key |
| Slow initialization | Enable discovery mode |
| Agent not responding | Reinitialize agent, check logs |

For detailed troubleshooting, see [`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md).

### Log Files

The agent maintains detailed logs:

```
gcm_agent.log          # Main application log
gcm_agent_ui.log       # UI-specific log
gcm_agent_config.log   # Configuration operations
gcm_agent_auth.log     # Authentication log
```

View logs:
```bash
tail -f gcm_agent.log
```

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
| 1.0 | 2026-06-05 | Initial release with core functionality |

---

**Maintained By:** GCM Agent Development Team  
**Last Updated:** 2026-06-05  
**Version:** 1.0