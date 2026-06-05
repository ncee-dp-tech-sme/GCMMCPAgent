# GCM Agent User Guide

**Version:** 1.0  
**Last Updated:** 2026-06-05

## Table of Contents

1. [Introduction](#introduction)
2. [Getting Started](#getting-started)
3. [Configuration Guide](#configuration-guide)
4. [Using the Agent](#using-the-agent)
5. [Advanced Features](#advanced-features)
6. [Best Practices](#best-practices)
7. [FAQ](#faq)

---

## Introduction

### What is the GCM Agent?

The GCM Agent is an AI-powered assistant that provides natural language interaction with IBM Guardium Cryptography Manager (GCM). It enables you to manage cryptographic assets, query key information, and perform complex operations using conversational commands instead of navigating through traditional interfaces.

### Key Features

- **Natural Language Interface**: Ask questions and give commands in plain English
- **Secure Credential Storage**: All sensitive data encrypted with Fernet encryption and stored locally
- **Two-Step Authentication**: OAuth2 flow with Keycloak and GCM user management
- **Dynamic Tool Discovery**: Automatically loads only the tools you need for optimal performance
- **Local Execution**: Runs entirely on your machine without cloud dependencies
- **Conversation History**: Maintains context across multiple interactions
- **Export Capabilities**: Save conversations for documentation or review

### Architecture Overview

The GCM Agent consists of several integrated components:

- **LangGraph Agent Core**: Orchestrates AI reasoning and tool execution
- **MCP Client Layer**: Connects to GCM's Model Context Protocol server
- **Configuration Manager**: Handles secure storage and retrieval of settings
- **Authentication Manager**: Manages OAuth2 tokens and GCM authorization
- **Gradio UI**: Provides user-friendly web interface for configuration and chat

For detailed architecture information, see [`docs/architecture/GCM-Agent-Architecture.md`](architecture/GCM-Agent-Architecture.md).

---

## Getting Started

### Prerequisites

Before using the GCM Agent, ensure you have:

1. **Python 3.10 or higher** installed on your system
2. **Access to IBM Guardium Cryptography Manager** with valid credentials
3. **WatsonX credentials** (API key and project ID)
4. **Network connectivity** to your GCM server and WatsonX services

### Quick Start

1. **Install the GCM Agent** (see [`SETUP.md`](SETUP.md) for detailed instructions):
   ```bash
   pip install -r requirements.txt
   ```

2. **Launch the application**:
   ```bash
   python app.py
   ```

3. **Access the web interface**:
   Open your browser to `http://localhost:7860`

4. **Configure your connection** in the Configuration tab

5. **Start chatting** in the Chat tab after initialization

---

## Configuration Guide

### Accessing Configuration

The Configuration interface is available in the **⚙️ Configuration** tab when you launch the application. It provides a secure way to set up your GCM Agent without exposing sensitive credentials.

### Configuration Sections

#### 🔑 Keycloak Server Settings

Configure your connection to the Keycloak authentication server:

| Field | Description | Example |
|-------|-------------|---------|
| **Keycloak URL** | Full URL to your Keycloak server | `https://keycloak.example.com` |
| **Keycloak Port** | Port for Keycloak server | `443` (default) |
| **Realm** | Keycloak realm name | `master` (default) |
| **Verify SSL** | Enable SSL certificate verification for Keycloak | ✅ Enabled (recommended) |

> **Note:** The Keycloak URL is used for OAuth2 token authentication.

#### 🖥️ GCM Server Settings

Configure your connection to the GCM MCP server:

| Field | Description | Example |
|-------|-------------|---------|
| **GCM URL** | Full URL to your GCM server | `https://gcm.example.com` |
| **Hostname** | GCM server hostname | `gcm-server` |
| **Verify SSL** | Enable SSL certificate verification for GCM | ✅ Enabled (recommended) |

> **Note:** The GCM URL is used for both MCP operations and user management authorization. The `/ibm/mcp/mcp` path is added automatically.

#### 🔐 Authentication Settings

Provide your GCM authentication credentials:

| Field | Description | Security |
|-------|-------------|----------|
| **Username** | Your GCM username | Encrypted locally |
| **Password** | Your GCM password | Encrypted with Fernet |
| **Client ID** | OAuth2 client identifier | Encrypted locally |
| **Client Secret** | OAuth2 client secret | Encrypted with Fernet |

> **Security Note:** All passwords and secrets are encrypted using Fernet encryption and stored in `~/.gcm_agent/.credentials.enc` with restrictive file permissions (0o600). They are never stored in plain text files.

#### 🤖 WatsonX Configuration

Configure the AI model backend:

| Field | Description | Example |
|-------|-------------|---------|
| **Project ID** | WatsonX project identifier | `12345678-1234-1234-1234-123456789abc` |
| **API Key** | WatsonX API key | Encrypted with Fernet |
| **Model** | LLM model to use | `ibm/granite-13b-chat-v2` |

**Available Models:**
- `ibm/granite-13b-chat-v2` - Recommended for most use cases
- `ibm/granite-20b-multilingual` - For multilingual support
- `meta-llama/llama-3-70b-instruct` - High-performance option
- `meta-llama/llama-3-1-70b-instruct` - Latest Llama model

#### ⚙️ Agent Settings

Fine-tune agent behavior:

| Setting | Description | Default | Range |
|---------|-------------|---------|-------|
| **Discovery Mode** | Enable dynamic tool loading | ✅ Enabled | On/Off |
| **Max Iterations** | Maximum reasoning steps | 10 | 1-50 |
| **Timeout** | Operation timeout in seconds | 300 | 60-600 |

**Discovery Mode Explained:**
- **Enabled (Recommended)**: Agent dynamically searches and loads only the tools it needs, improving performance
- **Disabled**: All 26 GCM tools are loaded upfront, which may be slower but ensures all capabilities are available

### Saving Configuration

1. Fill in all required fields in each section
2. Click **💾 Save Configuration**
3. Wait for the success message: "✅ Configuration saved successfully"

Your configuration is now securely stored and will persist across application restarts.

### Testing Your Connection

Before using the agent, verify your GCM connection:

1. Complete the GCM Server and Authentication sections
2. Click **🔌 Test Connection**
3. Wait for the result:
   - ✅ Success: "Connection successful! Credentials are valid."
   - ❌ Failure: Error message with details

### Loading Existing Configuration

If you've previously configured the agent:

1. Click **📥 Load Configuration**
2. Your saved settings will populate all fields
3. Passwords and secrets will show as `••••••••` for security

### Clearing Configuration

To remove all stored configuration:

1. Click **🗑️ Clear All**
2. Confirm the action
3. All settings and credentials will be deleted from secure storage

> **Warning:** This action cannot be undone. You'll need to reconfigure the agent.

---

## Using the Agent

### Initializing the Agent

Before you can chat with the agent, it must be initialized:

1. Navigate to the **💬 Chat** tab
2. Ensure your configuration is complete (check Configuration tab)
3. Click **🚀 Initialize Agent**
4. Wait for initialization (typically 10-30 seconds)
5. Status will change to "✅ Agent Ready"

**What happens during initialization:**
- Loads your configuration from secure storage
- Establishes connection to GCM MCP server
- Authenticates with Keycloak and GCM
- Loads available tools (discovery mode) or all tools (standard mode)
- Initializes the WatsonX LLM
- Prepares the conversation context

### Chat Interface Overview

The chat interface provides an intuitive way to interact with GCM:

```
┌─────────────────────────────────────────┐
│ Agent Status: ✅ Agent Ready            │
│ [🚀 Initialize Agent]                   │
├─────────────────────────────────────────┤
│                                         │
│  Conversation Area                      │
│  (Your messages and agent responses)    │
│                                         │
├─────────────────────────────────────────┤
│ Message: [Type your message here...]   │
├─────────────────────────────────────────┤
│ [📤 Send] [🗑️ Clear] [💾 Export]       │
└─────────────────────────────────────────┘
```

### Sending Messages

1. Type your question or command in the message box
2. Press **Enter** or click **📤 Send**
3. Watch as the agent processes your request
4. Responses stream in real-time

### Example Conversations

#### Listing Keys

**You:** List all cryptographic keys

**Agent:** I'll retrieve the list of keys from GCM for you.

*[Agent uses the appropriate tool to query GCM]*

Here are the cryptographic keys in your GCM instance:

1. **AES-256-Key-001**
   - Type: AES
   - Size: 256 bits
   - Status: Active
   - Created: 2026-05-15

2. **RSA-2048-Key-002**
   - Type: RSA
   - Size: 2048 bits
   - Status: Active
   - Created: 2026-05-20

*[Additional keys listed...]*

#### Getting Key Details

**You:** Show me details for AES-256-Key-001

**Agent:** Let me fetch the detailed information for that key.

*[Agent retrieves specific key information]*

**Key Details: AES-256-Key-001**

- **Key ID:** 550e8400-e29b-41d4-a716-446655440000
- **Algorithm:** AES
- **Key Size:** 256 bits
- **State:** Active
- **Usage:** Encryption/Decryption
- **Created:** 2026-05-15 14:30:22 UTC
- **Last Modified:** 2026-05-15 14:30:22 UTC
- **Key Group:** Production-Keys
- **Permissions:** Read, Use

#### Complex Operations

**You:** Create a new AES-256 key named "Database-Encryption-Key" in the Production-Keys group

**Agent:** I'll create a new AES-256 key with the specified name and assign it to the Production-Keys group.

*[Agent executes multi-step workflow]*

✅ Successfully created key:
- **Name:** Database-Encryption-Key
- **Type:** AES-256
- **Key Group:** Production-Keys
- **Key ID:** 660e8400-e29b-41d4-a716-446655440001
- **Status:** Active

The key is now ready for use in your database encryption operations.

### Understanding Agent Responses

The agent provides structured, informative responses:

- **Status Indicators**: ✅ Success, ❌ Error, ⚠️ Warning, ℹ️ Information
- **Formatted Data**: Tables, lists, and structured output for clarity
- **Context**: Explanations of what actions were taken
- **Next Steps**: Suggestions for related operations when appropriate

### Managing Conversation History

#### Clearing History

To start a fresh conversation:

1. Click **🗑️ Clear History**
2. All previous messages are removed
3. Agent context is reset
4. Status confirms: "✅ History cleared"

> **Note:** Clearing history doesn't affect your configuration or agent initialization.

#### Exporting Conversations

To save your conversation for documentation or review:

1. Click **💾 Export**
2. Conversation is exported as JSON
3. Export appears in a text box below
4. Copy the JSON for your records

**Export Format:**
```json
{
  "exported_at": "2026-06-05T20:30:00.000Z",
  "message_count": 12,
  "messages": [
    {
      "role": "user",
      "content": "List all keys"
    },
    {
      "role": "assistant",
      "content": "Here are the keys..."
    }
  ]
}
```

---

## Advanced Features

### Discovery Mode

Discovery mode enables intelligent, on-demand tool loading for optimal performance.

#### How It Works

1. **Initial State**: Agent starts with 5 discovery tools:
   - `search` - Find relevant tools by description
   - `get_schema` - Get detailed tool specifications
   - `list_tools` - List all available tools
   - `tags` - Browse tools by category
   - `execute` - Run workflows in sandboxed environment

2. **Dynamic Loading**: When you ask a question:
   - Agent analyzes your request
   - Searches for relevant tools
   - Loads only what's needed
   - Executes the operation

3. **Performance Benefits**:
   - Faster initialization (5 tools vs 26 tools)
   - Reduced memory footprint
   - More focused AI reasoning
   - Better token efficiency

#### When to Use Discovery Mode

**Enable Discovery Mode (Recommended) when:**
- You perform varied operations
- You want optimal performance
- You have limited system resources
- You're exploring GCM capabilities

**Disable Discovery Mode when:**
- You need all tools immediately available
- You perform repetitive operations
- You want predictable tool availability
- You're debugging tool-related issues

### Tool Execution

The agent can execute complex, multi-step workflows:

#### Single Tool Execution

Simple operations use one tool:
```
User: "List all key groups"
→ Agent uses list_key_groups tool
→ Returns formatted results
```

#### Multi-Tool Workflows

Complex operations chain multiple tools:
```
User: "Create a key and add it to the Production group"
→ Agent uses create_key tool
→ Agent uses add_key_to_group tool
→ Returns confirmation of both operations
```

#### Sandboxed Execution

In discovery mode, the `execute` tool runs workflows safely:
- Operations are validated before execution
- RBAC policies are enforced
- Errors are caught and reported
- Rollback is possible for failed operations

### Conversation Context

The agent maintains context across your conversation:

#### Context Retention

**You:** List all keys in the Production group

**Agent:** *[Lists keys]*

**You:** Show me details for the first one

**Agent:** *[Knows you mean the first key from the previous list]*

#### Context Limits

- Maximum iterations: Configurable (default: 10)
- Timeout: Configurable (default: 300 seconds)
- History: Maintained until cleared or agent restarted

### Error Handling

The agent gracefully handles various error scenarios:

#### Authentication Errors

```
❌ Authentication failed: Invalid credentials
Please check your username and password in the Configuration tab.
```

#### Tool Execution Errors

```
❌ Failed to create key: Key name already exists
Suggestion: Try a different key name or check existing keys first.
```

#### Timeout Errors

```
⚠️ Operation timed out after 300 seconds
The operation may still be processing on the server.
You can increase the timeout in Agent Settings if needed.
```

---

## Best Practices

### Security Recommendations

1. **Use Strong Credentials**
   - Choose complex passwords for GCM accounts
   - Rotate credentials regularly
   - Never share your WatsonX API key

2. **Enable SSL Verification**
   - Always keep "Verify SSL Certificates" enabled in production
   - Only disable for testing in controlled environments

3. **Protect Your Configuration**
   - Don't export or share configuration files
   - Use the built-in secure storage
   - Clear configuration when decommissioning systems

4. **Monitor Access**
   - Review GCM audit logs regularly
   - Track agent operations
   - Report suspicious activity

### Performance Optimization

1. **Use Discovery Mode**
   - Enables faster initialization
   - Reduces memory usage
   - Improves response times

2. **Adjust Timeout Settings**
   - Increase for complex operations
   - Decrease for simple queries
   - Monitor actual operation times

3. **Manage Conversation Length**
   - Clear history periodically
   - Export long conversations
   - Start fresh for unrelated tasks

4. **Choose Appropriate Models**
   - Use Granite 13B for most tasks
   - Use Llama 70B for complex reasoning
   - Consider response time vs. capability tradeoffs

### Effective Communication

1. **Be Specific**
   - ✅ "List all AES-256 keys in the Production group"
   - ❌ "Show me some keys"

2. **Use Clear Commands**
   - ✅ "Create a new RSA-2048 key named 'API-Key-001'"
   - ❌ "Make a key"

3. **Provide Context**
   - ✅ "Show details for the key I just created"
   - ❌ "Show details" (without prior context)

4. **Ask Follow-up Questions**
   - Agent maintains context
   - Build on previous responses
   - Clarify when needed

### Troubleshooting Tips

1. **Agent Not Responding**
   - Check initialization status
   - Verify network connectivity
   - Review timeout settings
   - Check logs for errors

2. **Unexpected Results**
   - Rephrase your question
   - Be more specific
   - Clear history and try again
   - Check GCM permissions

3. **Performance Issues**
   - Enable discovery mode
   - Reduce max iterations
   - Clear conversation history
   - Check system resources

For detailed troubleshooting, see [`TROUBLESHOOTING.md`](TROUBLESHOOTING.md).

---

## FAQ

### General Questions

**Q: Do I need an internet connection?**  
A: Yes, the agent requires connectivity to:
- Your GCM server (may be on local network)
- WatsonX services (cloud-based)
- Keycloak authentication server

**Q: Can multiple users share one configuration?**
A: No, configuration is stored per-user in `~/.gcm_agent/` directory. Each user must configure their own credentials.

**Q: Is my data sent to the cloud?**  
A: Only your prompts and GCM responses are sent to WatsonX for AI processing. Your credentials and configuration remain local.

### Configuration Questions

**Q: Where are my credentials stored?**
A: In the `~/.gcm_agent/` directory in your home folder:
- Encryption key: `~/.gcm_agent/.key` (0o600 permissions)
- Encrypted credentials: `~/.gcm_agent/.credentials.enc` (0o600 permissions)
- Both files are protected with restrictive permissions (owner read/write only)

**Q: Can I use environment variables instead?**  
A: The agent is designed to use secure storage, not environment variables. This is a security best practice to prevent credential exposure.

**Q: How do I change my password?**  
A: Update it in the Configuration tab and click Save. The new password will be securely stored.

### Usage Questions

**Q: What can I ask the agent?**  
A: Anything related to GCM operations:
- List, create, update, delete keys
- Manage key groups
- Query key details and metadata
- Perform cryptographic operations
- Manage policies and permissions

**Q: How long does initialization take?**  
A: Typically 10-30 seconds, depending on:
- Network latency
- Discovery mode setting
- Number of available tools

**Q: Can I use the agent offline?**  
A: No, the agent requires connectivity to GCM and WatsonX services.

### Troubleshooting Questions

**Q: Why does initialization fail?**  
A: Common causes:
- Incomplete configuration
- Invalid credentials
- Network connectivity issues
- GCM server unavailable
- WatsonX API issues

**Q: Why are responses slow?**  
A: Possible reasons:
- Complex operations requiring multiple tools
- Network latency
- Large result sets
- Model processing time
- Consider enabling discovery mode

**Q: What if I get an authentication error?**  
A: Try these steps:
1. Verify credentials in Configuration tab
2. Test connection
3. Check GCM server accessibility
4. Verify Keycloak is running
5. Review GCM user permissions

---

## Getting Help

### Documentation Resources

- **Setup Guide**: [`SETUP.md`](SETUP.md) - Installation and configuration
- **Troubleshooting**: [`TROUBLESHOOTING.md`](TROUBLESHOOTING.md) - Common issues and solutions
- **Architecture**: [`docs/architecture/GCM-Agent-Architecture.md`](architecture/GCM-Agent-Architecture.md) - Technical details

### Log Files

The agent maintains detailed logs for troubleshooting:

- **Location**: Application directory
- **Files**: 
  - `gcm_agent.log` - General application logs
  - `gcm_agent_ui.log` - UI-specific logs
  - `gcm_agent_config.log` - Configuration operations

### Reporting Issues

When reporting issues, include:

1. **Error Message**: Exact text of any error
2. **Steps to Reproduce**: What you did before the error
3. **Configuration**: GCM version, Python version, OS
4. **Logs**: Relevant log excerpts (redact sensitive data)
5. **Screenshots**: If UI-related

### Community Resources

- **IBM Documentation**: Official GCM and WatsonX documentation
- **GitHub Issues**: Report bugs and request features
- **Internal Support**: Contact your IBM support team

---

## Appendix

### Glossary

- **GCM**: IBM Guardium Cryptography Manager
- **MCP**: Model Context Protocol - Interface for AI tool integration
- **LangGraph**: Framework for building stateful AI agents
- **WatsonX**: IBM's AI and data platform
- **Keycloak**: Open-source identity and access management
- **OAuth2**: Industry-standard authorization protocol
- **RBAC**: Role-Based Access Control
- **Discovery Mode**: Dynamic tool loading mechanism

### Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-06-05 | Initial release |

---

**Document Version:** 1.0  
**Last Updated:** 2026-06-05  
**Maintained By:** GCM Agent Development Team