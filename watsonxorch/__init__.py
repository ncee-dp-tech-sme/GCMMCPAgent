"""WatsonX Orchestrate integration package for GCM Agent.

This package provides a REST API adapter that makes the GCM Agent compatible
with WatsonX Orchestrate platform. It follows the portability design principles
outlined in the GCM Agent Architecture documentation.

Made with Bob
2026-06-10 02:47 UTC - Initial implementation of WatsonX Orchestrate integration
"""

from watsonxorch.adapter import OrchestrateAdapter
from watsonxorch.models import (
    AgentRequest,
    AgentResponse,
    HealthResponse,
    ErrorResponse,
)
from watsonxorch.config import OrchestrateConfig

__version__ = "1.0.0"

__all__ = [
    "OrchestrateAdapter",
    "AgentRequest",
    "AgentResponse",
    "HealthResponse",
    "ErrorResponse",
    "OrchestrateConfig",
]

# Made with Bob
