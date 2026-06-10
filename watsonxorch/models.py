"""Pydantic models for WatsonX Orchestrate API requests and responses.

Made with Bob
2026-06-10 02:47 UTC - Initial implementation of request/response models
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class AgentRequest(BaseModel):
    """Standard agent request format for WatsonX Orchestrate."""
    
    query: str = Field(
        ...,
        description="Natural language query for the GCM agent",
        example="List all cryptographic keys"
    )
    context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context for the query (optional)",
        example={"user_id": "admin", "department": "security"}
    )
    session_id: Optional[str] = Field(
        None,
        description="Session ID for conversation continuity (optional)",
        example="sess_abc123"
    )
    stream: bool = Field(
        False,
        description="Enable streaming response (optional)",
        example=False
    )


class AgentResponse(BaseModel):
    """Standard agent response format for WatsonX Orchestrate."""
    
    result: str = Field(
        ...,
        description="Agent's response to the query",
        example="Found 42 cryptographic keys in the system..."
    )
    tools_used: List[str] = Field(
        default_factory=list,
        description="List of tools executed during query processing",
        example=["gcm_AssetInventoryService_FetchAllCryptoObjects"]
    )
    execution_time: float = Field(
        ...,
        description="Total execution time in seconds",
        example=2.34
    )
    session_id: str = Field(
        ...,
        description="Session ID for this interaction",
        example="sess_abc123"
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="Response timestamp in ISO 8601 format",
        example="2026-06-10T02:47:00Z"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata about the execution",
        example={"token_count": 1234, "model": "ibm/granite-13b-chat-v2"}
    )


class HealthResponse(BaseModel):
    """Health check response format."""
    
    status: str = Field(
        ...,
        description="Service health status",
        example="healthy"
    )
    version: str = Field(
        ...,
        description="API version",
        example="1.0.0"
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="Health check timestamp",
        example="2026-06-10T02:47:00Z"
    )
    components: Dict[str, str] = Field(
        default_factory=dict,
        description="Status of individual components",
        example={"agent": "ready", "mcp_client": "connected", "llm": "available"}
    )


class ErrorResponse(BaseModel):
    """Error response format."""
    
    error: str = Field(
        ...,
        description="Error type or category",
        example="AgentExecutionError"
    )
    message: str = Field(
        ...,
        description="Detailed error message",
        example="Failed to execute tool: Connection timeout"
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="Error timestamp",
        example="2026-06-10T02:47:00Z"
    )
    details: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional error details (optional)",
        example={"tool_name": "list_keys", "retry_count": 3}
    )

# Made with Bob
