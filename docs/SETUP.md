# GCM Agent Setup Guide

**Version:** 1.0  
**Last Updated:** 2026-06-05

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Verification](#verification)
5. [Deployment Options](#deployment-options)
6. [Troubleshooting Setup Issues](#troubleshooting-setup-issues)

---

## System Requirements

### Minimum Requirements

| Component | Requirement |
|-----------|-------------|
| **Python** | 3.10 or higher |
| **Operating System** | macOS 10.15+, Linux (Ubuntu 20.04+, RHEL 8+), Windows 10+ |
| **Memory** | 4 GB RAM (8 GB recommended) |
| **Disk Space** | 2 GB free space |
| **Network** | Internet connectivity for WatsonX and GCM access |

### Required System Packages

#### macOS

No additional system packages required. Python 3.10+ includes all necessary components.

```bash
# Verify Python version
python3 --version  # Should be 3.10 or higher
```

#### Linux (Ubuntu/Debian)

```bash
# Update package list
sudo apt update

# Install Python 3.10+ and required packages
sudo apt install python3.10 python3.10-venv python3-pip

# No additional packages required for Fernet encryption
```

#### Linux (RHEL/CentOS/Fedora)

```bash
# Install Python 3.10+ and required packages
sudo dnf install python3.10 python3-pip

# No additional packages required for Fernet encryption
```

#### Windows

1. **Install Python 3.10+**:
   - Download from [python.org](https://www.python.org/downloads/)
   - During installation, check "Add Python to PATH"
   - Verify installation: `python --version`

2. **No additional packages required** - Fernet encryption is included in the cryptography package

### Required Access

Before installation, ensure you have:

1. **Keycloak Server Access**:
   - Keycloak server URL and port
   - Keycloak realm information
   - Network connectivity to Keycloak server

2. **GCM Server Access**:
   - GCM server URL and hostname
   - Valid user account with appropriate permissions
   - Network connectivity to GCM server

3. **Authentication Credentials**:
   - OAuth2 client ID and client secret
   - GCM username and password

4. **WatsonX Credentials**:
   - WatsonX API key
   - WatsonX project ID
   - Active WatsonX subscription

---

## Installation

### Step 1: Clone the Repository

```bash
# Clone the repository
git clone <repository-url>
cd GCMMCPAgent

# Verify you're in the correct directory
ls -la
# You should see: app.py, requirements.txt, gcm_agent/, docs/, etc.
```

### Step 2: Create Virtual Environment

Creating a virtual environment isolates the agent's dependencies from your system Python.

#### macOS/Linux

```bash
# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate

# Verify activation (prompt should show (.venv))
which python
# Should show: /path/to/GCMMCPAgent/.venv/bin/python
```

#### Windows (Command Prompt)

```cmd
# Create virtual environment
python -m venv .venv

# Activate virtual environment
.venv\Scripts\activate.bat

# Verify activation
where python
REM Should show: C:\path\to\GCMMCPAgent\.venv\Scripts\python.exe
```

#### Windows (PowerShell)

```powershell
# Create virtual environment
python -m venv .venv

# Activate virtual environment
.venv\Scripts\Activate.ps1

# If you get an execution policy error, run:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Verify activation
Get-Command python
# Should show path in .venv\Scripts\
```

### Step 3: Install Dependencies

With your virtual environment activated:

```bash
# Upgrade pip to latest version
pip install --upgrade pip

# Install required packages
pip install -r requirements.txt

# Verify installation
pip list
# Should show langchain, langgraph, gradio, cryptography, etc.
```

### Step 4: Install Package in Development Mode

```bash
# Install the gcm_agent package
pip install -e .

# Verify installation
python -c "import gcm_agent; print('GCM Agent installed successfully')"
```

### Step 5: Verify Installation

Run a quick verification:

```bash
# Check Python version
python --version

# Verify key packages
python -c "import langchain; import langgraph; import gradio; print('All packages imported successfully')"

# Check cryptography package
python -c "from cryptography.fernet import Fernet; print('Fernet encryption available')"
```

Expected output:
```
Python 3.10.x (or higher)
All packages imported successfully
Fernet encryption available
```

---

## Configuration

### First-Time Setup Wizard

The GCM Agent uses a web-based configuration interface for secure credential management.

#### Step 1: Launch the Application

```bash
# Ensure virtual environment is activated
source .venv/bin/activate  # macOS/Linux
# or
.venv\Scripts\activate  # Windows

# Start the application
python app.py
```

You should see:
```
INFO: Starting GCM Agent application
INFO: Creating GCM Agent application
INFO: Configuration UI created successfully
INFO: Chat UI created successfully
INFO: GCM Agent application created successfully
Running on local URL:  http://0.0.0.0:7860
```

#### Step 2: Access the Web Interface

Open your web browser and navigate to:
```
http://localhost:7860
```

You'll see the GCM Agent interface with two tabs:
- ⚙️ Configuration
- 💬 Chat

#### Step 3: Configure GCM Server

In the **Configuration** tab, under **🖥️ GCM Server**:

1. **GCM URL**: Enter your GCM server URL
   ```
   Example: https://gcm.example.com
   ```

2. **GCM Hostname**: Enter the GCM server hostname (just the hostname, not the full URL)
   ```
   Example: gcm.example.com
   
   Note: The agent automatically extracts the hostname if you provide a full URL.
   - Input: https://gcm.apps.example.com:9443
   - Extracted: gcm.apps.example.com
   
   This hostname is used by the MCP server to construct internal API URLs.
   ```

3. **Keycloak Port**: Enter the Keycloak port (default: 443)
   ```
   Default: 443
   ```

4. **Realm**: Enter the Keycloak realm (default: master)
   ```
   Default: master
   ```

5. **Verify SSL Certificates**: Keep enabled for production
   ```
   ✅ Enabled (recommended)
   ```

#### Step 4: Configure Authentication

Under **🔐 Authentication**:

1. **Username**: Your GCM username
   ```
   Example: admin
   ```

2. **Password**: Your GCM password
   ```
   Enter your password (will be stored securely)
   ```

3. **Client ID**: OAuth2 client identifier
   ```
   Example: gcm-client
   ```

4. **Client Secret**: OAuth2 client secret
   ```
   Enter your client secret (will be stored securely)
   ```

#### Step 5: Configure WatsonX

Under **🤖 WatsonX**:

1. **Project ID**: Your WatsonX project identifier
   ```
   Example: 12345678-1234-1234-1234-123456789abc
   ```

2. **API Key**: Your WatsonX API key
   ```
   Enter your API key (will be stored securely)
   ```

3. **Model**: Select the LLM model
   ```
   Recommended: ibm/granite-13b-chat-v2
   ```

#### Step 6: Configure Agent Settings

Under **⚙️ Agent Settings**:

1. **Discovery Mode**: Enable for optimal performance
   ```
   ✅ Enabled (recommended)
   ```

2. **Max Iterations**: Set maximum reasoning steps
   ```
   Default: 10 (range: 1-50)
   ```

3. **Timeout**: Set operation timeout
   ```
   Default: 300 seconds (range: 60-600)
   ```

#### Step 7: Save Configuration

1. Click **💾 Save Configuration**
2. Wait for confirmation: "✅ Configuration saved successfully"

Your configuration is now securely encrypted and stored in `~/.gcm_agent/`.

### Testing Your Configuration

Before using the agent, verify your setup:

1. In the Configuration tab, click **🔌 Test Connection**
2. Wait for the result:
   - ✅ Success: "Connection successful! Credentials are valid."
   - ❌ Failure: See error message and troubleshooting section

### Loading Existing Configuration

If you've previously configured the agent:

1. Click **📥 Load Configuration**
2. All saved settings will populate the form
3. Passwords will show as `••••••••` for security

---

## Verification

### Verify Secure Storage

Check that credentials are properly encrypted and stored:

```bash
# Check that storage directory exists
ls -la ~/.gcm_agent/

# Should show:
# .key (encryption key, 0o600 permissions)
# .credentials.enc (encrypted credentials, 0o600 permissions)

# Verify file permissions (should be 0o600 - owner read/write only)
stat -c "%a %n" ~/.gcm_agent/.key ~/.gcm_agent/.credentials.enc  # Linux
stat -f "%Lp %N" ~/.gcm_agent/.key ~/.gcm_agent/.credentials.enc  # macOS
```

### Verify Agent Initialization

1. Navigate to the **💬 Chat** tab
2. Click **🚀 Initialize Agent**
3. Wait for initialization (10-30 seconds)
4. Status should change to: "✅ Agent Ready"

If initialization succeeds, your setup is complete!

### Run Test Scripts

The repository includes verification scripts:

```bash
# Test configuration system
python verify_config_system.py

# Test MCP integration
python verify_mcp_integration.py

# Test UI components
python test_ui.py
```

Expected output:
```
✅ Configuration system working
✅ MCP client connected
✅ UI components loaded
```

---

## Deployment Options

### Local Development Deployment

The default setup runs the agent locally on your machine.

**Advantages:**
- Full control over environment
- Easy debugging and development
- No external dependencies
- Secure credential storage

**Usage:**
```bash
# Start the agent
python app.py

# Access at http://localhost:7860
```

### Local Network Deployment

To make the agent accessible on your local network:

1. **Modify [`app.py`](../app.py)** (optional - already configured):
   ```python
   app.launch(
       server_name="0.0.0.0",  # Listen on all interfaces
       server_port=7860,
       share=False,
   )
   ```

2. **Start the application**:
   ```bash
   python app.py
   ```

3. **Access from other machines**:
   ```
   http://<your-ip-address>:7860
   ```

4. **Find your IP address**:
   ```bash
   # macOS/Linux
   ifconfig | grep "inet "
   
   # Windows
   ipconfig | findstr IPv4
   ```

**Security Considerations:**
- Only use on trusted networks
- Consider firewall rules
- Each user needs their own configuration
- Credentials are stored per-user, not shared

### Docker Deployment (Future)

Docker deployment is planned for future releases. This will provide:
- Containerized environment
- Easy distribution
- Consistent deployment across platforms
- Simplified dependency management

### Watsonx Orchestrate Integration (Future)

The agent is designed for future integration with Watsonx Orchestrate:

**Current Status:** Local deployment only

**Planned Features:**
- Seamless Orchestrate integration
- Shared agent instances
- Enterprise authentication
- Centralized management

**Compatibility Design:**
- Modular architecture supports portability
- Configuration abstraction layer
- Standardized API interfaces
- Minimal code changes required

For updates on Orchestrate integration, check the project repository.

---

## Troubleshooting Setup Issues

### Python Version Issues

**Problem:** Python version is too old

```bash
python --version
# Shows: Python 3.8.x or lower
```

**Solution:**
```bash
# macOS (using Homebrew)
brew install python@3.10

# Linux (Ubuntu)
sudo apt install python3.10

# Windows
# Download and install from python.org
```

### Virtual Environment Issues

**Problem:** Cannot activate virtual environment

**Solution (macOS/Linux):**
```bash
# Ensure you're in the project directory
cd /path/to/GCMMCPAgent

# Recreate virtual environment
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
```

**Solution (Windows PowerShell):**
```powershell
# Enable script execution
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Recreate virtual environment
Remove-Item -Recurse -Force .venv
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### Dependency Installation Issues

**Problem:** pip install fails

**Solution:**
```bash
# Upgrade pip
pip install --upgrade pip

# Clear pip cache
pip cache purge

# Retry installation
pip install -r requirements.txt

# If specific package fails, install individually
pip install langchain
pip install langgraph
# etc.
```

### Encryption Key Issues

**Problem:** Cannot create or access encryption key

**Solution:**
```bash
# Check storage directory permissions
ls -la ~/.gcm_agent/

# If directory doesn't exist or has wrong permissions
rm -rf ~/.gcm_agent/
mkdir -p ~/.gcm_agent/
chmod 700 ~/.gcm_agent/

# Restart the application to regenerate encryption key
python app.py
```

**Problem:** Corrupted encryption key or credentials file

**Solution:**
```bash
# Backup existing files (if needed)
cp ~/.gcm_agent/.key ~/.gcm_agent/.key.backup
cp ~/.gcm_agent/.credentials.enc ~/.gcm_agent/.credentials.enc.backup

# Remove corrupted files
rm ~/.gcm_agent/.key ~/.gcm_agent/.credentials.enc

# Restart application and reconfigure
python app.py
```

### Port Already in Use

**Problem:** Port 7860 is already in use

**Solution:**
```bash
# Find process using port 7860
# macOS/Linux
lsof -i :7860

# Windows
netstat -ano | findstr :7860

# Kill the process or use different port
# Modify app.py to use different port:
app.launch(server_port=7861)  # Use 7861 instead
```

### Network Connectivity Issues

**Problem:** Cannot connect to GCM server

**Solution:**
1. **Verify GCM server is accessible**:
   ```bash
   ping gcm.example.com
   curl -k https://gcm.example.com
   ```

2. **Check firewall rules**:
   - Ensure outbound HTTPS (443) is allowed
   - Check corporate proxy settings

3. **Test with curl**:
   ```bash
   curl -k https://gcm.example.com:443/ibm/mcp/mcp
   ```

4. **Verify DNS resolution**:
   ```bash
   nslookup gcm.example.com
   ```

### SSL Certificate Issues

**Problem:** SSL verification fails

**Temporary Solution (Testing Only):**
1. In Configuration tab, uncheck "Verify SSL Certificates"
2. Save configuration
3. Test connection

**Proper Solution:**
1. Install proper SSL certificates on GCM server
2. Add CA certificate to system trust store:
   ```bash
   # macOS
   sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain ca-cert.pem
   
   # Linux
   sudo cp ca-cert.pem /usr/local/share/ca-certificates/
   sudo update-ca-certificates
   
   # Windows
   # Import certificate via Certificate Manager (certmgr.msc)
   ```

### Permission Issues

**Problem:** Permission denied errors

**Solution:**
```bash
# Ensure you own the project directory
sudo chown -R $USER:$USER /path/to/GCMMCPAgent

# Fix permissions
chmod -R u+rw /path/to/GCMMCPAgent

# Recreate virtual environment
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Memory Issues

**Problem:** Out of memory errors

**Solution:**
1. **Close other applications**
2. **Use lighter model**:
   - Switch to `ibm/granite-13b-chat-v2` instead of Llama 70B
3. **Reduce max iterations**:
   - Set to 5 instead of 10
4. **Enable discovery mode**:
   - Reduces memory footprint

---

## Next Steps

After successful setup:

1. **Read the User Guide**: [`USER_GUIDE.md`](USER_GUIDE.md) for usage instructions
2. **Test Basic Operations**: Try listing keys, querying information
3. **Explore Features**: Test discovery mode, export conversations
4. **Review Security**: SSL verification is disabled by default; enable for production with valid certificates
5. **Monitor Performance**: Adjust settings based on your needs

For ongoing issues, see [`TROUBLESHOOTING.md`](TROUBLESHOOTING.md).

---

## Additional Resources

### Documentation

- **User Guide**: [`USER_GUIDE.md`](USER_GUIDE.md) - Complete usage documentation
- **Troubleshooting**: [`TROUBLESHOOTING.md`](TROUBLESHOOTING.md) - Common issues and solutions
- **Architecture**: [`docs/architecture/GCM-Agent-Architecture.md`](architecture/GCM-Agent-Architecture.md) - Technical details
- **AGENTS.md**: [`AGENTS.md`](../AGENTS.md) - Integration patterns and guidelines

### External Resources

- **Python Documentation**: https://docs.python.org/3/
- **LangChain Documentation**: https://python.langchain.com/
- **LangGraph Documentation**: https://langchain-ai.github.io/langgraph/
- **Gradio Documentation**: https://www.gradio.app/docs/
- **IBM GCM Documentation**: IBM internal documentation portal
- **WatsonX Documentation**: https://www.ibm.com/watsonx

---

**Document Version:** 1.0  
**Last Updated:** 2026-06-05  
**Maintained By:** GCM Agent Development Team