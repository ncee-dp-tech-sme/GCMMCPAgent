# GCM Agent Troubleshooting Guide

**Version:** 1.0  
**Last Updated:** 2026-06-05

## Table of Contents

1. [Authentication Issues](#authentication-issues)
2. [Configuration Problems](#configuration-problems)
3. [MCP Connection Issues](#mcp-connection-issues)
4. [Agent Execution Errors](#agent-execution-errors)
5. [Performance Issues](#performance-issues)
6. [UI and Display Issues](#ui-and-display-issues)
7. [Logging and Diagnostics](#logging-and-diagnostics)
8. [Getting Help](#getting-help)

---

## Authentication Issues

### Keycloak Connection Errors

#### Symptom
```
❌ Connection failed: Unable to connect to Keycloak server
```

#### Possible Causes
1. Incorrect Keycloak URL or port
2. Network connectivity issues
3. Keycloak server is down
4. Firewall blocking connection

#### Solutions

**1. Verify Keycloak URL**
```bash
# Test connectivity
curl -k https://gcm.example.com:443/auth/realms/master

# Expected: JSON response with realm information
```

**2. Check Network Connectivity**
```bash
# Test basic connectivity
ping gcm.example.com

# Test HTTPS port
telnet gcm.example.com 443
# or
nc -zv gcm.example.com 443
```

**3. Verify Configuration**
- In Configuration tab, check:
  - GCM URL format: `https://gcm.example.com` (no trailing slash)
  - Keycloak Port: Usually `443` or `8443`
  - Realm: Usually `master` (case-sensitive)

**4. Check Firewall Rules**
```bash
# macOS - check if port is blocked
sudo pfctl -s rules | grep 443

# Linux - check iptables
sudo iptables -L -n | grep 443

# Windows - check firewall
netsh advfirewall firewall show rule name=all | findstr 443
```

**5. Test with Disabled SSL Verification (Testing Only)**
- Temporarily disable "Verify SSL Certificates" in Configuration
- If this works, the issue is SSL certificate-related
- See [SSL Certificate Issues](#ssl-certificate-issues) below

---

### Invalid Credentials

#### Symptom
```
❌ Authentication failed: Invalid username or password
```

#### Solutions

**1. Verify Credentials**
- Double-check username (case-sensitive)
- Re-enter password carefully
- Ensure no extra spaces

**2. Test Credentials Directly**
```bash
# Test with curl
curl -k -X POST "https://gcm.example.com:443/auth/realms/master/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=YOUR_USERNAME" \
  -d "password=YOUR_PASSWORD" \
  -d "grant_type=password" \
  -d "client_id=YOUR_CLIENT_ID" \
  -d "client_secret=YOUR_CLIENT_SECRET"

# Expected: JSON with access_token
```

**3. Check Account Status**
- Verify account is not locked
- Check password hasn't expired
- Confirm account has necessary permissions

**4. Reset Credentials**
- Clear existing configuration: Click **🗑️ Clear All**
- Re-enter credentials carefully
- Save and test connection

---

### Token Expiration

#### Symptom
```
❌ Token expired: Please reinitialize the agent
```

#### Solutions

**1. Reinitialize Agent**
- Go to Chat tab
- Click **🚀 Initialize Agent**
- Wait for "✅ Agent Ready"

**2. Adjust Token Lifetime (GCM Admin)**
- Increase token lifetime in Keycloak settings
- Typical values: 300-3600 seconds

**3. Implement Auto-Refresh (Future Enhancement)**
- Currently, manual reinitialization is required
- Auto-refresh is planned for future releases

---

### SSL Certificate Issues

#### Symptoms

**Self-Signed Certificate Error:**
```
❌ Agent error: Agent streaming failed: Error calling tool 'gcm_getCertificateDashboard':
Request error (ConnectError): [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed:
self-signed certificate (_ssl.c:1004)
```

**General SSL Verification Error:**
```
❌ SSL verification failed: certificate verify failed
```

#### Quick Solution (Development/Testing)

For development and testing environments with self-signed certificates:

1. **Open Configuration Tab** in the GCM Agent UI
2. **Uncheck "Verify SSL"** for the affected server:
   - Uncheck for **Keycloak** if Keycloak uses self-signed certificates
   - Uncheck for **GCM Server** if GCM uses self-signed certificates
   - You can disable SSL verification independently for each server
3. **Click "💾 Save Configuration"**
4. **Return to Chat Tab** and click **"🚀 Initialize Agent"**
5. **Verify** the agent initializes without SSL errors

**What Happens When SSL Verification is Disabled:**
- The agent applies a process-wide SSL context workaround
- A warning message is logged: `"Applying SSL verification workaround for self-signed certificates"`
- All HTTPS connections in the process will bypass certificate verification
- This is safe for development/testing but should not be used in production

> **Security Warning:** Disabling SSL verification affects all HTTPS connections in the process. Only use this for development/testing environments with self-signed certificates. Never disable SSL verification in production.

#### Production Solutions

For production environments, properly install the CA certificate:

**1. Install CA Certificate (macOS)**
```bash
# Download CA certificate from GCM admin
# Install to system keychain
sudo security add-trusted-cert -d -r trustRoot \
  -k /Library/Keychains/System.keychain \
  /path/to/ca-cert.pem

# Verify installation
security find-certificate -c "Your CA Name" -a
```

**2. Install CA Certificate (Linux)**
```bash
# Copy certificate to CA directory
sudo cp /path/to/ca-cert.pem /usr/local/share/ca-certificates/gcm-ca.crt

# Update CA certificates
sudo update-ca-certificates

# Verify
openssl verify -CAfile /etc/ssl/certs/ca-certificates.crt /path/to/server-cert.pem
```

**3. Install CA Certificate (Windows)**
```powershell
# Open Certificate Manager
certmgr.msc

# Import certificate:
# 1. Right-click "Trusted Root Certification Authorities"
# 2. Select "All Tasks" > "Import"
# 3. Follow wizard to import CA certificate
```

**4. Export Self-Signed Certificate from Server**
```bash
# Export certificate from server
openssl s_client -connect gcm.example.com:443 -showcerts

# Save the certificate section (between BEGIN and END CERTIFICATE)
# Then install using one of the methods above
```

#### Verification

After installing the CA certificate or disabling SSL verification:

1. **Test Connection** in the Configuration tab
2. **Initialize Agent** in the Chat tab
3. **Check Logs** for SSL-related messages:
   ```bash
   tail -f logs/auth_*.log logs/mcp_*.log
   ```
4. **Verify** no SSL errors appear when executing tools

#### Troubleshooting SSL Issues

**Issue: SSL errors persist after disabling verification**
- **Solution**: Restart the application to apply the SSL workaround
- The SSL context is set during MCP client initialization

**Issue: Different SSL settings needed for Keycloak vs GCM**
- **Solution**: The agent supports independent SSL verification settings
- Uncheck SSL verification only for the server with self-signed certificates
- Keep SSL verification enabled for servers with valid certificates

**Issue: Warning about unverified HTTPS requests**
- **Expected**: This warning appears when SSL verification is disabled
- **Solution**: This is informational and can be ignored in development/testing
- For production, install proper CA certificates to eliminate the warning

---

## Configuration Problems

### Encryption Storage Errors

#### Symptom
```
❌ Storage error: Failed to create encryption key
❌ Storage error: Failed to load credentials
❌ EncryptionError: Invalid token or corrupted file
```

#### Solutions

**Cannot Create Storage Directory**
```bash
# Check if directory exists and has correct permissions
ls -la ~/.gcm_agent/

# Create directory with correct permissions
mkdir -p ~/.gcm_agent/
chmod 700 ~/.gcm_agent/

# Verify
ls -ld ~/.gcm_agent/
# Should show: drwx------ (700 permissions)
```

**Corrupted Encryption Key**
```bash
# Backup existing key (if needed)
cp ~/.gcm_agent/.key ~/.gcm_agent/.key.backup

# Remove corrupted key
rm ~/.gcm_agent/.key

# Restart application to regenerate
python app.py
# New key will be created automatically
```

**Corrupted Credentials File**
```bash
# Backup existing credentials (if needed)
cp ~/.gcm_agent/.credentials.enc ~/.gcm_agent/.credentials.enc.backup

# Remove corrupted file
rm ~/.gcm_agent/.credentials.enc

# Reconfigure in the UI
# Navigate to Configuration tab and re-enter credentials
```

**Permission Denied Errors**
```bash
# Fix ownership
sudo chown -R $USER:$USER ~/.gcm_agent/

# Fix permissions
chmod 700 ~/.gcm_agent/
chmod 600 ~/.gcm_agent/.key
chmod 600 ~/.gcm_agent/.credentials.enc

# Verify
ls -la ~/.gcm_agent/
# .key and .credentials.enc should show: -rw------- (600 permissions)
```

**Verify Encryption is Working**
```bash
# Test Fernet encryption
python -c "from cryptography.fernet import Fernet; key = Fernet.generate_key(); f = Fernet(key); encrypted = f.encrypt(b'test'); decrypted = f.decrypt(encrypted); print('Encryption working:', decrypted == b'test')"
# Should print: Encryption working: True
```

---

### Missing Configuration

#### Symptom
```
❌ Configuration incomplete. Please configure the agent first.
```

#### Solutions

**1. Check Configuration Status**
```python
# Run in Python console
from gcm_agent.config import get_config_manager

config_mgr = get_config_manager()
print(f"Configured: {config_mgr.is_configured()}")

# Check what's missing
try:
    config_mgr.get_gcm_config()
    print("✅ GCM config OK")
except Exception as e:
    print(f"❌ GCM config: {e}")

try:
    config_mgr.get_auth_config()
    print("✅ Auth config OK")
except Exception as e:
    print(f"❌ Auth config: {e}")

try:
    config_mgr.get_watsonx_config()
    print("✅ WatsonX config OK")
except Exception as e:
    print(f"❌ WatsonX config: {e}")
```

**2. Reconfigure**
- Go to Configuration tab
- Click **📥 Load Configuration** to see what's saved
- Fill in missing fields
- Click **💾 Save Configuration**

**3. Start Fresh**
- Click **🗑️ Clear All**
- Enter all configuration from scratch
- Save and test

---

### Invalid Configuration Values

#### Symptom
```
❌ Invalid configuration: URL must start with http:// or https://
```

#### Solutions

**1. Validate URL Format**
```
✅ Correct: https://gcm.example.com
❌ Wrong: gcm.example.com
❌ Wrong: https://gcm.example.com/
❌ Wrong: http://gcm.example.com:443
```

**2. Validate Port Numbers**
```
✅ Correct: 443, 8443, 8080
❌ Wrong: -1, 0, 70000
```

**3. Validate Required Fields**
- All fields must be non-empty
- No leading/trailing spaces
- Case-sensitive where applicable

**4. Check Field Constraints**
```python
# Max iterations: 1-50
# Timeout: 60-600 seconds
# Port: 1-65535
```

---

## MCP Connection Issues

### Connection Timeout

#### Symptom
```
❌ MCP connection timeout: Failed to connect to GCM MCP server
```

#### Solutions

**1. Verify MCP Endpoint**
```bash
# Test MCP endpoint
curl -k https://gcm.example.com/ibm/mcp/mcp

# Expected: MCP server response or error message
```

**2. Check GCM MCP Server Status**
- Verify GCM MCP server is running
- Check GCM server logs for errors
- Confirm MCP feature is enabled in GCM

**3. Increase Timeout**
- In Agent Settings, increase timeout to 600 seconds
- Save configuration
- Reinitialize agent

**4. Check Network Path**
```bash
# Trace route to server
traceroute gcm.example.com

# Check for network delays or blocks
```

---

### Tool Loading Failures

#### Symptom
```
❌ Failed to load tools: No tools available
```

#### Solutions

**1. Check Discovery Mode**
- If discovery mode is enabled, ensure GCM MCP server supports it
- Try disabling discovery mode in Agent Settings
- Save and reinitialize

**2. Verify MCP Server Version**
- Ensure GCM MCP server is up to date
- Check compatibility with `langchain-mcp-adapters`

**3. Check RBAC Configuration**
- Verify your user has permissions to access tools
- Check GCM RBAC settings
- Confirm tool visibility in GCM admin interface

**4. Test Tool Loading Manually**
```python
# Run in Python console
import asyncio
from gcm_agent.mcp import GCMMCPClient

async def test_tools():
    client = GCMMCPClient(
        gcm_url="https://gcm.example.com",
        gcm_hostname="gcm.example.com",
        # ... other params
    )
    await client.connect()
    tools = await client.get_tools()
    print(f"Loaded {len(tools)} tools")
    for tool in tools:
        print(f"  - {tool.name}")

asyncio.run(test_tools())
```

---

### Discovery Mode Problems

#### Symptom
```
❌ Discovery tools not available
```

#### Solutions

**1. Verify Discovery Mode Support**
- Check if GCM MCP server supports discovery mode
- Look for `x-mcp-enable-discovery` header support

**2. Disable Discovery Mode**
- In Agent Settings, uncheck "Discovery Mode"
- Save configuration
- Reinitialize agent
- All 26 tools will load upfront

**3. Check Discovery Tools**
Expected discovery tools:
- `search` - Find tools by description
- `get_schema` - Get tool specifications
- `list_tools` - List available tools
- `tags` - Browse by category
- `execute` - Run workflows

**4. Test Discovery Manually**
```python
# Test discovery endpoint
import httpx

async def test_discovery():
    async with httpx.AsyncClient(verify=False) as client:
        response = await client.get(
            "https://gcm.example.com/ibm/mcp/mcp",
            headers={"x-mcp-enable-discovery": "true"}
        )
        print(response.json())

import asyncio
asyncio.run(test_discovery())
```

---

## Agent Execution Errors

### LLM Initialization Failures

#### Symptom
```
❌ Agent initialization failed: Failed to initialize WatsonX LLM
```

#### Solutions

**1. Verify WatsonX Credentials**
```bash
# Test API key
curl -X POST "https://us-south.ml.cloud.ibm.com/ml/v1/text/generation?version=2023-05-29" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"input": "test", "model_id": "ibm/granite-13b-chat-v2", "project_id": "YOUR_PROJECT_ID"}'

# Expected: JSON response with generated text
```

**2. Check Project ID**
- Verify project ID is correct (UUID format)
- Confirm project exists in WatsonX
- Check project has model access

**3. Verify Model Availability**
- Confirm selected model is available in your project
- Try different model (e.g., `ibm/granite-13b-chat-v2`)

**4. Check Network Connectivity**
```bash
# Test WatsonX endpoint
ping us-south.ml.cloud.ibm.com

# Test HTTPS
curl -I https://us-south.ml.cloud.ibm.com
```

---

### Tool Execution Errors

#### Symptom
```
❌ Tool execution failed: Error calling GCM API
```

#### Solutions

**1. Check Tool Permissions**
- Verify your GCM user has permissions for the operation
- Check RBAC policies in GCM
- Confirm tool is enabled in GCM configuration

**2. Verify Input Parameters**
- Ensure required parameters are provided
- Check parameter format and types
- Review tool schema for requirements

**3. Check GCM Server Logs**
- Review GCM server logs for errors
- Look for API call failures
- Check for resource constraints

**4. Test Tool Directly**
```python
# Test tool execution
import asyncio
from gcm_agent.agent import GCMAgent

async def test_tool():
    # Initialize agent (see setup)
    agent = GCMAgent(...)
    await agent.initialize()
    
    # Test specific tool
    result = await agent.execute_tool("list_keys", {})
    print(result)

asyncio.run(test_tool())
```

---

### Streaming Issues

#### Symptom
```
❌ Streaming failed: Connection lost during response
```

#### Solutions

**1. Check Network Stability**
- Verify stable internet connection
- Test with ping for packet loss
- Check for network interruptions

**2. Increase Timeout**
- In Agent Settings, increase timeout
- Save and reinitialize

**3. Disable Streaming (Fallback)**
```python
# Modify agent to use non-streaming mode
# In gcm_agent/agent/gcm_agent.py
# Use invoke() instead of stream()
```

**4. Check Proxy Settings**
- If behind proxy, configure proxy settings
- Test direct connection if possible

---

## Performance Issues

### Slow Initialization

#### Symptom
Agent takes >60 seconds to initialize

#### Solutions

**1. Enable Discovery Mode**
- In Agent Settings, enable "Discovery Mode"
- Reduces initial tool loading time
- Save and reinitialize

**2. Check Network Latency**
```bash
# Test latency to GCM server
ping -c 10 gcm.example.com

# Test latency to WatsonX
ping -c 10 us-south.ml.cloud.ibm.com
```

**3. Reduce Max Iterations**
- In Agent Settings, reduce to 5
- Faster initialization
- May limit complex operations

**4. Check System Resources**
```bash
# Check CPU usage
top  # macOS/Linux
# or
taskmgr  # Windows

# Check memory
free -h  # Linux
vm_stat  # macOS
```

---

### Slow Response Times

#### Symptom
Agent responses take >30 seconds

#### Solutions

**1. Use Faster Model**
- Switch to `ibm/granite-13b-chat-v2`
- Faster than Llama 70B models
- Good balance of speed and quality

**2. Enable Discovery Mode**
- Reduces tool loading overhead
- Faster tool selection

**3. Clear Conversation History**
- Long histories slow processing
- Click **🗑️ Clear History**
- Start fresh conversation

**4. Optimize Queries**
- Be specific in requests
- Avoid overly complex questions
- Break complex tasks into steps

---

### High Memory Usage

#### Symptom
Application uses >4GB RAM

#### Solutions

**1. Use Lighter Model**
- Switch to `ibm/granite-13b-chat-v2`
- Smaller model, less memory

**2. Enable Discovery Mode**
- Loads fewer tools
- Reduces memory footprint

**3. Restart Application**
```bash
# Stop application (Ctrl+C)
# Restart
python app.py
```

**4. Clear System Cache**
```bash
# macOS
sudo purge

# Linux
sudo sync && sudo sysctl -w vm.drop_caches=3
```

---

## UI and Display Issues

### UI Not Loading

#### Symptom
Browser shows "Unable to connect" or blank page

#### Solutions

**1. Verify Application is Running**
```bash
# Check if process is running
ps aux | grep "python app.py"

# Check if port is listening
lsof -i :7860  # macOS/Linux
netstat -ano | findstr :7860  # Windows
```

**2. Check Correct URL**
```
✅ Correct: http://localhost:7860
❌ Wrong: https://localhost:7860
❌ Wrong: http://127.0.0.1:7860 (may work, but use localhost)
```

**3. Try Different Browser**
- Test in Chrome, Firefox, Safari
- Clear browser cache
- Try incognito/private mode

**4. Check Firewall**
```bash
# Temporarily disable firewall (testing only)
# macOS
sudo pfctl -d

# Linux
sudo ufw disable

# Windows
netsh advfirewall set allprofiles state off
```

---

### Configuration Not Saving

#### Symptom
Configuration disappears after restart

#### Solutions

**1. Check Keyring Permissions**
```bash
# macOS - unlock keychain
security unlock-keychain ~/Library/Keychains/login.keychain-db

# Linux - check keyring daemon
ps aux | grep gnome-keyring-daemon
```

**2. Verify Write Permissions**
```bash
# Check if keyring is writable
python -c "import keyring; keyring.set_password('test', 'test', 'test'); print('OK')"
```

**3. Check Disk Space**
```bash
# Ensure sufficient disk space
df -h  # macOS/Linux
```

**4. Use Alternative Backend**
```bash
# If system keyring fails, use file backend
export PYTHON_KEYRING_BACKEND=keyrings.alt.file.EncryptedKeyring
```

---

### Chat History Not Displaying

#### Symptom
Previous messages don't show in chat

#### Solutions

**1. Refresh Page**
- Press F5 or Cmd+R
- Reload browser page

**2. Check Browser Console**
- Open Developer Tools (F12)
- Check Console tab for errors
- Look for JavaScript errors

**3. Clear Browser Cache**
```
Chrome: Settings > Privacy > Clear browsing data
Firefox: Settings > Privacy > Clear Data
Safari: Develop > Empty Caches
```

**4. Reinitialize Agent**
- Click **🚀 Initialize Agent**
- Start new conversation

---

## Logging and Diagnostics

### Log File Locations

The agent creates several log files:

```
GCMMCPAgent/
├── gcm_agent.log          # Main application log
├── gcm_agent_ui.log       # UI-specific log
├── gcm_agent_config.log   # Configuration operations
└── gcm_agent_auth.log     # Authentication log
```

### Viewing Logs

```bash
# View main log
tail -f gcm_agent.log

# View last 100 lines
tail -n 100 gcm_agent.log

# Search for errors
grep "ERROR" gcm_agent.log

# Search for specific issue
grep -i "authentication" gcm_agent.log
```

### Log Levels

Logs use standard Python logging levels:

- **DEBUG**: Detailed diagnostic information
- **INFO**: General informational messages
- **WARNING**: Warning messages (non-critical)
- **ERROR**: Error messages (operation failed)
- **CRITICAL**: Critical errors (system failure)

### Enabling Debug Logging

```python
# Modify gcm_agent/utils/logger.py
# Change log level to DEBUG

import logging

def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)  # Change from INFO to DEBUG
    # ... rest of configuration
```

### Common Log Messages

#### Successful Operations
```
INFO: Configuration loaded successfully
INFO: GCM Agent initialized successfully
INFO: Tool execution completed
```

#### Warnings
```
WARNING: Token will expire in 60 seconds
WARNING: Configuration incomplete or invalid
WARNING: Retrying connection (attempt 2/3)
```

#### Errors
```
ERROR: Failed to connect to GCM server
ERROR: Authentication failed: Invalid credentials
ERROR: Tool execution failed: Permission denied
```

### Diagnostic Commands

```bash
# Check Python environment
python --version
pip list | grep langchain

# Check network connectivity
ping gcm.example.com
curl -k https://gcm.example.com

# Check encryption
python -c "from cryptography.fernet import Fernet; print('Fernet available')"

# Check storage
ls -la ~/.gcm_agent/

# Check configuration
python -c "from gcm_agent.config import get_config_manager; print(get_config_manager().is_configured())"

# Test imports
python -c "import langchain; import langgraph; import gradio; print('OK')"
```

---

## Getting Help

### Before Requesting Help

Gather the following information:

1. **System Information**
   ```bash
   python --version
   uname -a  # macOS/Linux
   systeminfo  # Windows
   ```

2. **Error Messages**
   - Exact error text
   - Screenshots if UI-related
   - Relevant log excerpts

3. **Configuration** (redact sensitive data)
   - GCM server version
   - Python version
   - Operating system
   - Network environment (proxy, firewall, etc.)

4. **Steps to Reproduce**
   - What you were trying to do
   - Steps taken before error
   - Whether error is consistent

5. **Logs**
   ```bash
   # Collect last 200 lines of each log
   tail -n 200 gcm_agent.log > logs_main.txt
   tail -n 200 gcm_agent_ui.log > logs_ui.txt
   tail -n 200 gcm_agent_config.log > logs_config.txt
   ```

### Support Channels

1. **Documentation**
   - [`USER_GUIDE.md`](USER_GUIDE.md) - Usage documentation
   - [`SETUP.md`](SETUP.md) - Installation guide
   - [`docs/architecture/GCM-Agent-Architecture.md`](architecture/GCM-Agent-Architecture.md) - Technical details

2. **GitHub Issues**
   - Search existing issues
   - Create new issue with template
   - Include diagnostic information

3. **Internal Support**
   - Contact IBM support team
   - Provide collected diagnostic data
   - Include GCM server details

### Creating Effective Bug Reports

Use this template:

```markdown
## Bug Description
[Clear description of the issue]

## Environment
- OS: [macOS 13.0 / Ubuntu 22.04 / Windows 11]
- Python: [3.10.5]
- GCM Agent Version: [1.0]
- GCM Server Version: [x.x.x]

## Steps to Reproduce
1. [First step]
2. [Second step]
3. [Third step]

## Expected Behavior
[What should happen]

## Actual Behavior
[What actually happens]

## Error Messages
```
[Paste error messages here]
```

## Logs
[Attach relevant log excerpts]

## Screenshots
[If applicable]

## Additional Context
[Any other relevant information]
```

---

## Quick Reference

### Common Issues Quick Fix

| Issue | Quick Fix |
|-------|-----------|
| Can't connect to GCM | Check URL, test with curl, verify network |
| Invalid credentials | Re-enter carefully, test with curl |
| SSL errors | Install CA cert or disable SSL (testing only) |
| Encryption errors | Check ~/.gcm_agent/ permissions, regenerate key |
| Slow initialization | Enable discovery mode, check network |
| Agent not responding | Reinitialize agent, check logs |
| Configuration not saving | Check storage permissions, verify ~/.gcm_agent/ |
| UI not loading | Verify app running, check port, try different browser |

### Emergency Recovery

If nothing works:

```bash
# 1. Stop application
# Press Ctrl+C

# 2. Clear all configuration
python -c "from gcm_agent.config import get_config_manager; get_config_manager().reset_config()"

# 3. Remove virtual environment
rm -rf .venv

# 4. Recreate environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 5. Restart application
python app.py

# 6. Reconfigure from scratch
```

---

**Document Version:** 1.0  
**Last Updated:** 2026-06-05  
**Maintained By:** GCM Agent Development Team