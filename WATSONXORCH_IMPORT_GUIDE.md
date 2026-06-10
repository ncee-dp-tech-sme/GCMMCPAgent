# WatsonX Orchestrate Package Import Guide

Made with Bob
2026-06-10 02:56 UTC - Quick import guide for watsonxorch.zip

## Package Location

**File:** `watsonxorch.zip` (26KB)
**Location:** `/Users/erwin/Documents/Projecten/Github_repos/personal_dev/ncee-dp-tech-sme/gcmmcpagent/GCMMCPAgent/watsonxorch.zip`

## Quick Import Instructions

### Method 1: Extract and Install (Recommended)

```bash
# Extract the zip file
unzip watsonxorch.zip

# Navigate to the extracted directory
cd watsonxorch

# Install the package
pip install -e .

# Verify installation
python -c "import watsonxorch; print('Success! Version:', watsonxorch.__version__)"
```

### Method 2: Extract and Use Directly

```bash
# Extract the zip file
unzip watsonxorch.zip

# Add to Python path in your script
import sys
sys.path.insert(0, '/path/to/watsonxorch')

# Import the package
from watsonxorch import OrchestrateAdapter, AgentRequest, AgentResponse
```

### Method 3: Install Dependencies First

```bash
# Extract the zip file
unzip watsonxorch.zip
cd watsonxorch

# Install dependencies
pip install -r requirements.txt

# Install the package
pip install -e .
```

## What's Included in the Zip

The zip file contains the complete WatsonX Orchestrate integration package:

### Core Modules (5 files):
- `__init__.py` - Package initialization
- `models.py` - Pydantic models
- `adapter.py` - Orchestrate adapter
- `api.py` - FastAPI REST API
- `config.py` - Configuration management

### Configuration Files (5 files):
- `agent.yaml` - WatsonX Orchestrate skill definition
- `requirements.txt` - Python dependencies
- `setup.py` - Package installation
- `pyproject.toml` - Modern packaging
- `MANIFEST.in` - Distribution manifest

### Deployment Files (3 files):
- `Dockerfile` - Docker container
- `k8s-deployment.yaml` - Kubernetes manifests
- `.env.example` - Environment template

### Documentation & Examples (5 files):
- `README.md` - Full documentation
- `INSTALL.md` - Installation guide
- `run_server.py` - Server startup script
- `example_client.py` - Example usage
- `test_orchestrate.py` - Unit tests

## Usage After Import

### 1. Configure Environment

```bash
cd watsonxorch
cp .env.example .env
# Edit .env with your credentials
```

### 2. Start the API Server

```bash
# Using the installed CLI tool
watsonxorch-server

# Or using the script directly
python run_server.py

# With custom settings
python run_server.py --host 0.0.0.0 --port 9000 --reload
```

### 3. Test the Installation

```bash
# Run unit tests
pytest test_orchestrate.py -v

# Test with example client
python example_client.py

# Check health endpoint
curl http://localhost:8000/health
```

### 4. Use in Your Code

```python
import asyncio
from watsonxorch import OrchestrateAdapter, AgentRequest
from gcm_agent.config import get_config_manager
from gcm_agent.config.config_manager import AgentSetupConfig, LLMProviderConfig

async def main():
    # Load configuration
    config_mgr = get_config_manager()
    
    # Create LLM config
    llm_config = LLMProviderConfig(
        provider="watsonx",
        watsonx_config=config_mgr.get_watsonx_config(),
        watsonx_api_key=config_mgr.get_watsonx_api_key()
    )
    
    # Create setup config
    setup_config = AgentSetupConfig(
        keycloak_config=config_mgr.get_keycloak_config(),
        gcm_config=config_mgr.get_gcm_config(),
        auth_config=config_mgr.get_auth_config(),
        llm_config=llm_config,
        agent_config=config_mgr.get_agent_config(),
        password=config_mgr.get_password(),
        client_secret=config_mgr.get_client_secret()
    )
    
    # Create adapter
    adapter = await OrchestrateAdapter.create(setup_config)
    
    # Execute query
    request = AgentRequest(query="List all cryptographic keys")
    response = await adapter.execute(request)
    
    print(f"Result: {response.result}")
    print(f"Tools used: {response.tools_used}")
    
    await adapter.close()

if __name__ == "__main__":
    asyncio.run(main())
```

## Register with WatsonX Orchestrate

1. Deploy the API server (see above)
2. Update `agent.yaml` with your API endpoint URL
3. Register with WatsonX Orchestrate:
   ```bash
   orchestrate skill register --file watsonxorch/agent.yaml
   ```

## Troubleshooting

### Import Errors

```bash
# Ensure package is in Python path
python -c "import sys; print('\n'.join(sys.path))"

# Reinstall if needed
pip install -e . --force-reinstall
```

### Missing Dependencies

```bash
# Install all dependencies
pip install -r requirements.txt

# Or install specific missing packages
pip install fastapi uvicorn[standard]
```

### Permission Errors

```bash
# Use --user flag if needed
pip install -e . --user
```

## Next Steps

1. Read `README.md` for comprehensive documentation
2. Review `INSTALL.md` for detailed installation instructions
3. Check `example_client.py` for usage examples
4. Test with `test_orchestrate.py`
5. Deploy using `Dockerfile` or `k8s-deployment.yaml`

## Support

For issues or questions:
- Check the README.md in the package
- Review test_orchestrate.py for examples
- Consult INSTALL.md for troubleshooting