#!/usr/bin/env python3
"""Example client for testing the WatsonX Orchestrate API.

Made with Bob
2026-06-10 02:49 UTC - Example client implementation
"""

import asyncio
import httpx
from typing import Optional


class OrchestrateClient:
    """Simple client for interacting with the WatsonX Orchestrate API."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        """
        Initialize client.
        
        Args:
            base_url: Base URL of the API server
        """
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=300.0)
    
    async def health_check(self) -> dict:
        """Check API health status."""
        response = await self.client.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()
    
    async def execute(
        self,
        query: str,
        context: Optional[dict] = None,
        session_id: Optional[str] = None
    ) -> dict:
        """
        Execute agent query.
        
        Args:
            query: Natural language query
            context: Optional context dictionary
            session_id: Optional session ID for conversation continuity
            
        Returns:
            Agent response dictionary
        """
        payload = {
            "query": query,
            "context": context or {},
            "session_id": session_id,
            "stream": False
        }
        
        response = await self.client.post(
            f"{self.base_url}/agent/execute",
            json=payload
        )
        response.raise_for_status()
        return response.json()
    
    async def stream_execute(
        self,
        query: str,
        context: Optional[dict] = None,
        session_id: Optional[str] = None
    ):
        """
        Execute agent query with streaming response.
        
        Args:
            query: Natural language query
            context: Optional context dictionary
            session_id: Optional session ID for conversation continuity
            
        Yields:
            Response chunks as they are generated
        """
        payload = {
            "query": query,
            "context": context or {},
            "session_id": session_id,
            "stream": True
        }
        
        async with self.client.stream(
            "POST",
            f"{self.base_url}/agent/execute",
            json=payload
        ) as response:
            response.raise_for_status()
            async for chunk in response.aiter_text():
                yield chunk
    
    async def get_status(self) -> dict:
        """Get agent status and configuration."""
        response = await self.client.get(f"{self.base_url}/agent/status")
        response.raise_for_status()
        return response.json()
    
    async def close(self):
        """Close client connection."""
        await self.client.aclose()


async def main():
    """Example usage of the orchestrate client."""
    client = OrchestrateClient()
    
    try:
        # Health check
        print("=== Health Check ===")
        health = await client.health_check()
        print(f"Status: {health['status']}")
        print(f"Components: {health['components']}")
        print()
        
        # Agent status
        print("=== Agent Status ===")
        status = await client.get_status()
        print(f"Status: {status['status']}")
        print(f"Config: {status['config']}")
        print(f"Tools loaded: {status['tools_loaded']}")
        print()
        
        # Execute query
        print("=== Execute Query ===")
        query = "List all cryptographic keys"
        print(f"Query: {query}")
        
        response = await client.execute(
            query=query,
            context={"user_id": "admin"}
        )
        
        print(f"\nResult: {response['result'][:200]}...")
        print(f"Tools used: {response['tools_used']}")
        print(f"Execution time: {response['execution_time']:.2f}s")
        print(f"Session ID: {response['session_id']}")
        print()
        
        # Streaming query
        print("=== Streaming Query ===")
        query = "Show me details of the first key"
        print(f"Query: {query}")
        print("\nStreaming response:")
        
        async for chunk in client.stream_execute(query=query):
            print(chunk, end="", flush=True)
        
        print("\n")
        
    except httpx.HTTPStatusError as e:
        print(f"HTTP Error: {e.response.status_code}")
        print(f"Response: {e.response.text}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())

# Made with Bob
