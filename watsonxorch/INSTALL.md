# Installation Guide for WatsonX Orchestrate Integration

Made with Bob
2026-06-10 02:54 UTC - Installation instructions

## Prerequisites

- Python 3.9 or higher
- pip package manager
- Access to GCM server
- WatsonX or OpenAI API credentials

## Installation Methods

### Method 1: Install as Standalone Package (Recommended)

```bash
# Navigate to watsonxorch directory
cd watsonxorch

# Install the package
pip install -e .

# Verify installation
python -c "import watsonxorch; print(watsonxorch.__version__)"
```

### Method 2: Install from Parent Project

```bash
# From GCM Agent project root
pip install -e .

# The watsonxorch package will be available
python -c "from watsonxorch import OrchestrateAdapter"
```

### Method 3: Install Dependencies Only

```bash
# Navigate to watsonxorch directory
cd watsonxorch

# Install dependencies from requirements.txt
pip install -r requirements.txt
```

## Post-Installation Setup

### 1. Configure Environment Variables

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your credentials
nano .env
```

Required variables:
- `GCM_URL` - GCM server URL
- `GCM_HOSTNAME` - GCM hostname
- `USERNAME` - GCM username
- `PASSWORD` - GCM password
- `CLIENT_ID` - OAuth2 client ID
- `CLIENT_SECRET` - OAuth2 client secret
- `LLM_PROVIDER` - "watsonx" or "openai"
- LLM-specific credentials (see `.env.example`)

### 2. Test Installation

```bash
# Test API server startup
python run_server.py

# In another terminal, test health endpoint
curl http://localhost:8000/health
```

### 3. Run Tests

```bash
# Install test dependencies
pip install -e ".[dev]"

# Run tests
pytest test_orchestrate.py -v
```

## Package Structure

After installation, the package provides:

```python
from watsonxorch import (
    OrchestrateAdapter,      # Main adapter class
    AgentRequest,            # Request model
    AgentResponse,           # Response model
    HealthResponse,          # Health check model
    ErrorResponse,           # Error model
    OrchestrateConfig,       # Configuration class
)
```

## Command-Line Tools

The package installs a command-line tool:

```bash
# Start the API server
watsonxorch-server

# With custom host/port
watsonxorch-server --host 0.0.0.0 --port 9000

# With auto-reload for development
watsonxorch-server --reload
```

## Troubleshooting

### Import Errors

If you get import errors:

```bash
# Ensure package is installed
pip list | grep watsonxorch

# Reinstall if needed
pip install -e . --force-reinstall
```

### Dependency Conflicts

If you have dependency conflicts:

```bash
# Create a fresh virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install package
pip install -e .
```

### Missing Dependencies

If FastAPI or uvicorn are missing:

```bash
# Install web server dependencies explicitly
pip install fastapi uvicorn[standard]
```

## Uninstallation

```bash
# Uninstall the package
pip uninstall watsonxorch

# Remove virtual environment (if used)
deactivate
rm -rf venv
```

## Next Steps

1. Configure your environment variables in `.env`
2. Start the API server: `python run_server.py`
3. Test with example client: `python example_client.py`
4. Register with WatsonX Orchestrate using `agent.yaml`
5. Read the full documentation in `README.md`

## Support

For issues or questions:
- Check `README.md` for detailed documentation
- Review `test_orchestrate.py` for usage examples
- Check logs in the console output