"""FastAPI REST API for WatsonX Orchestrate integration.

This module provides the REST API endpoints that make the GCM Agent
accessible to WatsonX Orchestrate platform.

Made with Bob
2026-06-10 02:47 UTC - Initial implementation of FastAPI REST API
"""

from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
import uvicorn

from gcm_agent.config import get_config_manager
from gcm_agent.config.config_manager import AgentSetupConfig, LLMProviderConfig
from gcm_agent.utils.logger import get_agent_logger

from watsonxorch.adapter import OrchestrateAdapter
from watsonxorch.models import AgentRequest, AgentResponse, HealthResponse, ErrorResponse
from watsonxorch.config import OrchestrateConfig


# Global adapter instance
adapter: Optional[OrchestrateAdapter] = None
logger = get_agent_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle (startup/shutdown)."""
    global adapter
    
    # Startup: Initialize adapter
    logger.info("Starting WatsonX Orchestrate API server")
    try:
        config_mgr = get_config_manager()
        
        # Determine LLM provider from environment
        llm_provider = config_mgr.get_llm_provider()
        
        if llm_provider == "watsonx":
            llm_config = LLMProviderConfig(
                provider="watsonx",
                watsonx_config=config_mgr.get_watsonx_config(),
                watsonx_api_key=config_mgr.get_watsonx_api_key()
            )
        elif llm_provider == "openai":
            llm_config = LLMProviderConfig(
                provider="openai",
                openai_config=config_mgr.get_openai_config(),
                openai_api_key=config_mgr.get_openai_api_key()
            )
        else:
            raise ValueError(f"Unsupported LLM provider: {llm_provider}")
        
        # Create agent setup config
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
        logger.info("Orchestrate adapter initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize adapter: {e}")
        raise
    
    yield
    
    # Shutdown: Cleanup adapter
    logger.info("Shutting down WatsonX Orchestrate API server")
    if adapter:
        await adapter.close()


# Create FastAPI app
app = FastAPI(
    title="GCM Agent API for WatsonX Orchestrate",
    description="REST API wrapper for GCM Agent compatible with WatsonX Orchestrate",
    version="1.0.0",
    lifespan=lifespan
)


# Configure CORS
orchestrate_config = OrchestrateConfig.from_env()
if orchestrate_config.cors_enabled:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=orchestrate_config.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for all unhandled exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error=type(exc).__name__,
            message=str(exc),
            details={"path": str(request.url)}
        ).dict()
    )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.
    
    Returns service health status and component availability.
    """
    components = {
        "adapter": "ready" if adapter else "not_initialized",
        "agent": "ready" if adapter and adapter.agent else "not_initialized",
    }
    
    # Check MCP client connection
    if adapter and adapter.agent and adapter.agent.mcp_client:
        components["mcp_client"] = "connected"
    else:
        components["mcp_client"] = "disconnected"
    
    # Check LLM availability
    if adapter and adapter.agent and adapter.agent.llm:
        components["llm"] = "available"
    else:
        components["llm"] = "unavailable"
    
    status = "healthy" if all(v in ["ready", "connected", "available"] for v in components.values()) else "degraded"
    
    return HealthResponse(
        status=status,
        version="1.0.0",
        components=components
    )


@app.post("/agent/execute", response_model=AgentResponse)
async def execute_agent(request: AgentRequest):
    """
    Execute agent request.
    
    Processes a natural language query using the GCM Agent and returns
    a structured response with results, tools used, and execution metadata.
    
    Args:
        request: Agent request with query and optional context
        
    Returns:
        Structured agent response
        
    Raises:
        HTTPException: If agent execution fails
    """
    if not adapter:
        raise HTTPException(
            status_code=503,
            detail="Agent adapter not initialized"
        )
    
    try:
        # Check if streaming is requested
        if request.stream:
            async def generate():
                async for chunk in adapter.stream_execute(request):
                    yield chunk
            
            return StreamingResponse(
                generate(),
                media_type="text/plain"
            )
        
        # Execute non-streaming request
        response = await adapter.execute(request)
        return response
        
    except Exception as e:
        logger.error(f"Agent execution failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error=type(e).__name__,
                message=str(e)
            ).dict()
        )


@app.get("/agent/status")
async def agent_status():
    """
    Get agent status and configuration.
    
    Returns current agent configuration and operational status.
    """
    if not adapter or not adapter.agent:
        raise HTTPException(
            status_code=503,
            detail="Agent not initialized"
        )
    
    return {
        "status": "operational",
        "config": {
            "discovery_mode": adapter.agent.agent_config.discovery_mode,
            "max_iterations": adapter.agent.agent_config.max_iterations,
            "llm_provider": adapter.agent.llm_config.provider,
        },
        "tools_loaded": len(adapter.agent.tools) if hasattr(adapter.agent, 'tools') else 0,
    }


def run_server(
    host: str = "0.0.0.0",
    port: int = 8000,
    reload: bool = False
):
    """
    Run the FastAPI server.
    
    Args:
        host: Server host address
        port: Server port
        reload: Enable auto-reload for development
    """
    uvicorn.run(
        "watsonxorch.api:app",
        host=host,
        port=port,
        reload=reload,
        log_level=orchestrate_config.log_level.lower()
    )


if __name__ == "__main__":
    run_server()

# Made with Bob
