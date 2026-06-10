# WatsonX Orchestrate Integration for GCM Agent

This package provides a REST API adapter that makes the GCM Agent compatible with WatsonX Orchestrate platform. It follows the portability design principles outlined in the GCM Agent Architecture documentation.

## Overview

The WatsonX Orchestrate integration provides:
- **REST API Wrapper**: FastAPI-based endpoints for agent execution
- **Stateless Operations**: No local state dependencies for cloud deployment
- **Standard Interfaces**: OpenAPI/REST for external communication
- **Configuration Injection**: Accept configuration from external sources
- **Streaming Support**: Real-time response streaming for long-running queries
- **Agent Configuration**: `agent.yaml` for WatsonX Orchestrate skill registration

## Architecture

```
WatsonX Orchestrate → REST API → Orchestrate Adapter → GCM Agent → MCP Client → GCM Server
```

## Installation

### Option 1: Install from watsonxorch directory

```bash
# Navigate to watsonxorch directory
cd watsonxorch

# Install in development mode
pip install -e .

# Or install with dev dependencies
pip install -e ".[dev]"
```

### Option 2: Install from parent project

```bash
# From GCM Agent project root
pip install -e .

# The watsonxorch package will be available for import
```

### Option 3: Install from requirements.txt

```bash
# Navigate to watsonxorch directory
cd watsonxorch

# Install dependencies
pip install -r requirements.txt
```

### Verify Installation

```python
# Test import
import watsonxorch
from watsonxorch import OrchestrateAdapter, AgentRequest, AgentResponse

print(f"WatsonX Orchestrate version: {watsonxorch.__version__}")
```

## Configuration

### Environment Variables

Create a `.env` file or set environment variables:

```bash
# GCM Configuration (required)
GCM_URL=https://gcm.example.com:9443
GCM_HOSTNAME=gcm.example.com
USERNAME=admin
PASSWORD=your_password
CLIENT_ID=your_client_id
CLIENT_SECRET=your_client_secret

# Keycloak Configuration (required)
KEYCLOAK_PORT=443
REALM=master

# LLM Configuration (required - choose one)
# WatsonX
LLM_PROVIDER=watsonx
LLM_WATSONX_API_KEY=your_api_key
LLM_WATSONX_PROJECT_ID=your_project_id
WATSONX_MODEL=ibm/granite-13b-chat-v2

# OR OpenAI
LLM_PROVIDER=openai
OPENAI_API_KEY=your_api_key
OPENAI_MODEL=gpt-4
OPENAI_TEMPERATURE=0.1
OPENAI_MAX_TOKENS=4096

# Orchestrate API Configuration (optional)
ORCHESTRATE_HOST=0.0.0.0
ORCHESTRATE_PORT=8000
ORCHESTRATE_CORS_ENABLED=true
ORCHESTRATE_CORS_ORIGINS=*
ORCHESTRATE_SESSION_TIMEOUT=3600
ORCHESTRATE_MAX_SESSIONS=100
ORCHESTRATE_MAX_WORKERS=4
ORCHESTRATE_REQUEST_TIMEOUT=300
ORCHESTRATE_LOG_LEVEL=INFO
ORCHESTRATE_LOG_FORMAT=json
```

## WatsonX Orchestrate Registration

### Agent Configuration File

The `agent.yaml` file defines the agent's capabilities and skills for WatsonX Orchestrate. It includes:

- **Agent metadata**: Name, version, description
- **Skills definition**: Available operations (execute_query, health_check, agent_status)
- **Input/output schemas**: Request and response formats
- **Examples**: Common use cases and queries
- **Security settings**: Authentication and compliance requirements
- **Deployment configuration**: Scaling and monitoring settings

### Registering with WatsonX Orchestrate

1. **Deploy the API Server** (see Usage section below)

2. **Configure the endpoint** in `agent.yaml`:
   ```yaml
   endpoint:
     baseUrl: https://your-gcm-agent-api.example.com
   ```

3. **Register the agent** with WatsonX Orchestrate:
   - Upload `agent.yaml` to WatsonX Orchestrate skill registry
   - Or use the Orchestrate CLI:
     ```bash
     orchestrate skill register --file watsonxorch/agent.yaml
     ```

4. **Test the integration**:
   - Use WatsonX Orchestrate UI to invoke the agent
   - Try example queries from `agent.yaml`

### Available Skills

The agent exposes three skills to WatsonX Orchestrate:

1. **execute_query**: Execute natural language queries against GCM
   - Input: `query` (string), optional `context` and `session_id`
   - Output: Structured response with results and metadata

2. **health_check**: Check agent health and availability
   - No input required
   - Output: Health status and component availability

3. **agent_status**: Get agent configuration and operational status
   - No input required
   - Output: Configuration details and tools loaded

## Usage

### Starting the API Server

#### Method 1: Direct Python Execution

```bash
# From project root
python -m watsonxorch.api
```

#### Method 2: Using the Run Script

```bash
# From project root
python watsonxorch/run_server.py
```

#### Method 3: Programmatic

```python
from watsonxorch.api import run_server

run_server(
    host="0.0.0.0",
    port=8000,
    reload=False  # Set True for development
)
```

### API Endpoints

#### Health Check

```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2026-06-10T02:47:00Z",
  "components": {
    "adapter": "ready",
    "agent": "ready",
    "mcp_client": "connected",
    "llm": "available"
  }
}
```

#### Execute Agent Request

```bash
curl -X POST http://localhost:8000/agent/execute \
  -H "Content-Type: application/json" \
  -d '{
    "query": "List all cryptographic keys",
    "context": {"user_id": "admin"},
    "session_id": "sess_abc123"
  }'
```

Response:
```json
{
  "result": "Found 42 cryptographic keys in the system...",
  "tools_used": ["gcm_AssetInventoryService_FetchAllCryptoObjects"],
  "execution_time": 2.34,
  "session_id": "sess_abc123",
  "timestamp": "2026-06-10T02:47:00Z",
  "metadata": {
    "query_length": 30,
    "context_keys": ["user_id"],
    "agent_config": {
      "discovery_mode": false,
      "max_iterations": 20
    }
  }
}
```

#### Streaming Response

```bash
curl -X POST http://localhost:8000/agent/execute \
  -H "Content-Type: application/json" \
  -d '{
    "query": "List all cryptographic keys",
    "stream": true
  }'
```

#### Agent Status

```bash
curl http://localhost:8000/agent/status
```

Response:
```json
{
  "status": "operational",
  "config": {
    "discovery_mode": false,
    "max_iterations": 20,
    "llm_provider": "watsonx"
  },
  "tools_loaded": 26
}
```

### Interactive API Documentation

FastAPI provides automatic interactive documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/openapi.json

## Programmatic Usage

### Using the Adapter Directly

```python
import asyncio
from gcm_agent.config import get_config_manager
from gcm_agent.config.config_manager import AgentSetupConfig, LLMProviderConfig
from watsonxorch.adapter import OrchestrateAdapter
from watsonxorch.models import AgentRequest

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
    
    try:
        # Execute request
        request = AgentRequest(
            query="List all cryptographic keys",
            context={"user_id": "admin"}
        )
        
        response = await adapter.execute(request)
        print(f"Result: {response.result}")
        print(f"Tools used: {response.tools_used}")
        print(f"Execution time: {response.execution_time}s")
        
    finally:
        await adapter.close()

if __name__ == "__main__":
    asyncio.run(main())
```

### Streaming Responses

```python
async def stream_example():
    adapter = await OrchestrateAdapter.create(setup_config)
    
    try:
        request = AgentRequest(
            query="List all cryptographic keys",
            stream=True
        )
        
        async for chunk in adapter.stream_execute(request):
            print(chunk, end="", flush=True)
        
    finally:
        await adapter.close()
```

## Deployment

### Docker Deployment

Create a `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Copy project files
COPY . .

# Install dependencies
RUN pip install -e .

# Expose API port
EXPOSE 8000

# Run server
CMD ["python", "-m", "watsonxorch.api"]
```

Build and run:

```bash
docker build -t gcm-agent-orchestrate .
docker run -p 8000:8000 --env-file .env gcm-agent-orchestrate
```

### Kubernetes Deployment

See `watsonxorch/k8s-deployment.yaml` for example Kubernetes manifests.

### Production Considerations

1. **Security**:
   - Use HTTPS/TLS for production deployments
   - Implement authentication/authorization middleware
   - Secure credential storage (Kubernetes secrets, vault, etc.)

2. **Performance**:
   - Adjust `ORCHESTRATE_MAX_WORKERS` based on load
   - Configure `ORCHESTRATE_REQUEST_TIMEOUT` for long-running queries
   - Use connection pooling for database/API connections

3. **Monitoring**:
   - Enable structured logging (`ORCHESTRATE_LOG_FORMAT=json`)
   - Integrate with monitoring tools (Prometheus, Grafana)
   - Set up health check endpoints for load balancers

4. **Scaling**:
   - Deploy multiple replicas behind load balancer
   - Use session affinity if maintaining conversation state
   - Consider Redis for distributed session storage

## Troubleshooting

### Common Issues

1. **"Agent adapter not initialized"**
   - Check that all required environment variables are set
   - Verify GCM server connectivity
   - Check logs for initialization errors

2. **SSL Certificate Errors**
   - Ensure SSL bypass is configured in `.env` if using self-signed certificates
   - Verify `GCM_URL` and `GCM_HOSTNAME` are correct

3. **Token Expiration**
   - Token refresh is automatic - check Keycloak configuration
   - Verify `CLIENT_ID` and `CLIENT_SECRET` are correct

4. **Tool Execution Failures**
   - Check MCP server connectivity
   - Verify RBAC permissions for the user
   - Review agent logs for detailed error messages

### Debug Mode

Enable debug logging:

```bash
export ORCHESTRATE_LOG_LEVEL=DEBUG
python -m watsonxorch.api
```

## API Reference

See the auto-generated OpenAPI documentation at `/docs` when the server is running.

## License

See the main project LICENSE file.

## Support

For issues and questions, refer to the main GCM Agent documentation or create an issue in the project repository.