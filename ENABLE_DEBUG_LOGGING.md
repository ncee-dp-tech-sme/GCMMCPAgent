# How to Enable Debug Logging for GCM Agent

There are two ways to enable DEBUG logging to see detailed parameter injection logs:

## Option 1: Environment Variable (Recommended)

Add to your `.env` file:

```bash
# Enable DEBUG logging for all modules
LOG_LEVEL=DEBUG

# Optional: Enable file logging
LOG_TO_FILE=true
LOG_DIR=logs
```

Then restart the application:
```bash
python app.py
```

**Benefits:**
- Affects all loggers (auth, mcp, agent, ui, config)
- Persists across restarts
- No code changes needed

## Option 2: Programmatic (For Testing)

Add this code at the start of `app.py` (after imports, before `create_app()`):

```python
# Add after line 40 (after logger = get_ui_logger())
import logging
from gcm_agent.utils.logger import StructuredLogger

# Enable DEBUG logging for MCP module only
StructuredLogger.set_level('gcm_agent.mcp', logging.DEBUG)

# Or enable DEBUG for all modules
StructuredLogger.set_level('gcm_agent.auth', logging.DEBUG)
StructuredLogger.set_level('gcm_agent.mcp', logging.DEBUG)
StructuredLogger.set_level('gcm_agent.agent', logging.DEBUG)
StructuredLogger.set_level('gcm_agent.config', logging.DEBUG)
StructuredLogger.set_level('gcm_agent.ui', logging.DEBUG)
```

**Benefits:**
- Fine-grained control per module
- Temporary debugging without changing .env
- Can be toggled at runtime

## What You'll See with DEBUG Logging

### Parameter Injection Logs:
```
[INFO] Added default page_number=1 to tool 'fetch_asset_list' body
[INFO] Added default page_size=50 to tool 'fetch_asset_list' body
```

### Tool Execution Details:
```
[DEBUG] Tool 'fetch_asset_list' result type: <class 'tuple'>
[DEBUG] Tool returned tuple: content type=<class 'str'>, artifact type=<class 'dict'>
```

### MCP Connection Details:
```
[DEBUG] Extracted hostname 'gcm.example.com' from URL 'https://gcm.example.com:9443'
[DEBUG] MCP client connected successfully
```

## Current Log Levels

The logger system (`gcm_agent/utils/logger.py`) supports:
- `DEBUG` - Detailed diagnostic information
- `INFO` - General informational messages (default)
- `WARNING` - Warning messages
- `ERROR` - Error messages
- `CRITICAL` - Critical errors

## File Logging

If you enable `LOG_TO_FILE=true`, logs will be written to:
```
logs/mcp_20260608.log
logs/auth_20260608.log
logs/agent_20260608.log
logs/config_20260608.log
logs/ui_20260608.log
```

Each module gets its own log file with date suffix.

## Recommended Setup for Debugging Parameter Issues

Add to `.env`:
```bash
# Enable DEBUG logging
LOG_LEVEL=DEBUG

# Enable file logging for easier analysis
LOG_TO_FILE=true
LOG_DIR=logs

# Your existing GCM configuration
GCM_URL=https://your-gcm-server:9443
GCM_HOSTNAME=your-gcm-server
# ... rest of your config
```

Then run:
```bash
python app.py
```

You'll see detailed logs in both console and `logs/mcp_YYYYMMDD.log` file showing exactly when and how parameters are being added to tool calls.