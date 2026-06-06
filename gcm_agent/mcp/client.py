"""MCP client wrapper for GCM server integration."""

# Made with Bob
# 2026-06-06 04:38 UTC - Fixed async/await error in execute_tool by checking if result is a coroutine and awaiting it (fixes 'execute' tool TypeError)
# 2026-06-06 04:10 UTC - Enhanced error logging in get_tools() to capture TaskGroup exception details with full traceback
# 2026-06-06 02:59 UTC - Fixed x-gcm-hostname header propagation by passing gcm_hostname to _client_factory during token refresh
# 2026-06-06 01:59 UTC - Added parameter unwrapping to fix Pydantic validation errors from LangChain MCP adapter nested params structure
# 2026-06-06 01:08 UTC - Removed module-level SSL bypass (now handled at app.py startup)
# 2026-06-06 00:55 UTC - Implemented module-level SSL bypass before MCP imports to fix SSL verification errors
# 2026-06-06 00:28 UTC - Added token refresh mechanism and reconnection support to fix intermittent SSL/500 errors
# 2026-06-05 23:51 UTC - Enhanced SSL workaround to patch both AsyncClient and sync Client, auto-extract hostname from URL
# 2026-06-05 23:44 UTC - Added x-gcm-hostname header to fix 500 errors on asset inventory API calls
# 2026-06-05 22:48 UTC - Added environment variable SSL workaround
# 2026-06-05 22:43 UTC - Added SSL verification workaround for self-signed certificates
# 2026-06-05 22:01 UTC - Initial implementation of GCMMCPClient with streamable_http transport
# 2026-06-05 21:47 UTC - Fixed MCP endpoint URL to /ibm/mcp/mcp and removed deprecated context manager usage
# 2026-06-05 21:59 UTC - Fixed parameter name: client_factory -> httpx_client_factory

from typing import Callable, Optional, List, Dict, Any
import asyncio
import traceback
import sys

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_core.tools import Tool

from gcm_agent.utils.logger import get_mcp_logger


class GCMMCPClient:
    """
    MCP client wrapper for GCM server integration.
    
    Manages connection to GCM MCP server using streamable_http transport
    with proper authentication via client_factory. Supports both discovery
    mode (dynamic tool loading) and standard mode (all tools loaded).
    
    Key Features:
    - Async context manager support
    - Connection state management
    - Tool caching for performance
    - Automatic reconnection on connection loss
    - Discovery mode support via x-mcp-code-mode header
    
    Example:
        >>> async with GCMMCPClient(gcm_url, client_factory) as client:
        ...     tools = await client.get_tools()
        ...     result = await client.execute_tool("list_keys", {})
    """
    
    def __init__(
        self,
        gcm_url: str,
        gcm_hostname: str,
        client_factory: Callable,
        discovery_mode: bool = True,
        timeout: int = 300,
        verify_ssl: bool = True,
        gcm_authenticator: Optional[Any] = None,
    ):
        """
        Initialize GCM MCP Client.
        
        Args:
            gcm_url: GCM server URL (e.g., https://gcm.example.com)
            gcm_hostname: GCM server hostname (used for internal API calls)
                Can be full URL or just hostname - will extract hostname automatically
            client_factory: Factory function from GCMAuthenticator._client_factory()
            discovery_mode: Enable discovery mode (default True)
                - True: Returns 4 discovery tools + 1 execute tool
                - False: Returns all 26 application tools
            timeout: Request timeout in seconds (default 300)
            verify_ssl: Verify SSL certificates (default True)
            gcm_authenticator: Optional GCMAuthenticator instance for token refresh
        """
        self.gcm_url = gcm_url.rstrip("/")
        self.logger = get_mcp_logger()
        
        # Extract hostname from URL if full URL was provided
        # e.g., "https://gcm.example.com:9443" -> "gcm.example.com"
        if gcm_hostname.startswith(("http://", "https://")):
            from urllib.parse import urlparse
            parsed = urlparse(gcm_hostname)
            self.gcm_hostname = parsed.hostname or gcm_hostname
            self.logger.debug(f"Extracted hostname '{self.gcm_hostname}' from URL '{gcm_hostname}'")
        else:
            self.gcm_hostname = gcm_hostname
        
        self.client_factory = client_factory
        self.discovery_mode = discovery_mode
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.gcm_authenticator = gcm_authenticator
        
        # Log SSL verification status (bypass is handled at app.py startup)
        if not verify_ssl:
            self.logger.warning(
                "SSL verification disabled - global bypass applied at application startup"
            )
        
        # Connection state
        self._connected = False
        self._mcp_client: Optional[MultiServerMCPClient] = None
        self._tools_cache: Optional[List[Tool]] = None
        self._server_info: Optional[Dict[str, Any]] = None
        
        self.logger.debug(
            f"GCMMCPClient initialized for {gcm_url} (hostname={gcm_hostname}) "
            f"(discovery_mode={discovery_mode}, timeout={timeout}s, verify_ssl={verify_ssl})"
        )
    
    async def _check_and_refresh_token(self) -> None:
        """
        Check if token is expired and refresh if needed.
        
        This method should be called before any MCP operation to ensure
        the token is valid. If the token is expired, it will refresh it
        and recreate the client factory.
        """
        if not self.gcm_authenticator:
            # No authenticator available, cannot refresh
            return
        
        if self.gcm_authenticator.is_token_expired():
            self.logger.warning("Token expired, refreshing...")
            
            try:
                # Refresh the token
                new_token = await self.gcm_authenticator.refresh_token()
                
                # Create new client factory with refreshed token
                self.client_factory = self.gcm_authenticator._client_factory(
                    new_token, self.timeout, self.gcm_hostname
                )
                
                # Reconnect with new factory
                await self.reconnect_with_new_factory()
                
                self.logger.info("Token refreshed and client reconnected successfully")
                
            except Exception as e:
                self.logger.error(f"Failed to refresh token: {e}")
                # Don't raise - let the operation proceed and fail naturally
                # This allows for better error messages from the actual operation
    
    async def connect(self) -> None:
        """
        Establish MCP connection to GCM server.
        
        Creates MultiServerMCPClient with streamable_http transport and
        proper authentication headers. The x-mcp-code-mode header
        controls which tools are exposed by the server.
        
        SSL verification is controlled by the module-level patch applied
        during initialization when verify_ssl=False.
        
        Raises:
            MCPConnectionError: If connection fails
        """
        if self._connected:
            self.logger.debug("Already connected to MCP server")
            return
        
        self.logger.info(f"Connecting to GCM MCP server at {self.gcm_url}")
        
        # Check and refresh token before connecting
        await self._check_and_refresh_token()
        
        try:
            # Log connection parameters for debugging
            mcp_url = f"{self.gcm_url}/ibm/mcp/mcp"
            self.logger.debug(f"MCP Endpoint URL: {mcp_url}")
            self.logger.debug(f"Headers: x-mcp-code-mode={'true' if self.discovery_mode else 'false'}, x-gcm-hostname={self.gcm_hostname}")
            self.logger.debug(f"Timeout: {self.timeout}s")
            
            # Create MCP client with streamable_http transport
            # This is critical for remote GCM server integration
            # Note: As of langchain-mcp-adapters 0.1.0, MultiServerMCPClient
            # should NOT be used as a context manager
            self._mcp_client = MultiServerMCPClient(
                {
                    "gcm": {
                        "transport": "streamable_http",
                        "url": mcp_url,
                        "headers": {
                            "x-mcp-code-mode": "true" if self.discovery_mode else "false",
                            "x-gcm-hostname": self.gcm_hostname
                        },
                        "httpx_client_factory": self.client_factory,
                        "timeout": self.timeout,
                    }
                }
            )
            
            # Client is ready to use immediately (no context manager needed)
            self._connected = True
            self.logger.info(
                f"Successfully connected to GCM MCP server "
                f"(discovery_mode={self.discovery_mode})"
            )
            
            # Get server info
            await self._fetch_server_info()
            
        except Exception as e:
            # Enhanced error logging for connection failures
            self.logger.error("=" * 80)
            self.logger.error("DETAILED ERROR INFORMATION FOR MCP CONNECTION FAILURE")
            self.logger.error("=" * 80)
            self.logger.error(f"Exception Type: {type(e).__name__}")
            self.logger.error(f"Exception Message: {str(e)}")
            self.logger.error("\nFull Traceback:")
            self.logger.error(traceback.format_exc())
            
            # Log connection parameters
            self.logger.error("\nConnection Parameters:")
            self.logger.error(f"  GCM URL: {self.gcm_url}")
            self.logger.error(f"  MCP Endpoint: {self.gcm_url}/ibm/mcp/mcp")
            self.logger.error(f"  GCM Hostname: {self.gcm_hostname}")
            self.logger.error(f"  Discovery Mode: {self.discovery_mode}")
            self.logger.error(f"  Timeout: {self.timeout}s")
            self.logger.error(f"  Verify SSL: {self.verify_ssl}")
            self.logger.error("=" * 80)
            
            from gcm_agent.mcp import MCPConnectionError
            raise MCPConnectionError(f"Failed to connect to MCP server: {e}") from e
    
    async def disconnect(self) -> None:
        """
        Close MCP connection and cleanup resources.
        
        Properly closes the MCP client connection and clears cached data.
        Safe to call multiple times.
        """
        if not self._connected:
            self.logger.debug("Not connected to MCP server")
            return
        
        self.logger.info("Disconnecting from GCM MCP server")
        
        try:
            # Note: As of langchain-mcp-adapters 0.1.0, no explicit cleanup needed
            # Just clear the reference
            self._mcp_client = None
            
            self._connected = False
            self._tools_cache = None
            self._server_info = None
            
            self.logger.info("Successfully disconnected from GCM MCP server")
            
        except Exception as e:
            self.logger.error(f"Error during disconnect: {e}")
            # Still mark as disconnected even if cleanup fails
            self._connected = False
            self._mcp_client = None
    
    async def get_tools(self) -> List[Tool]:
        """
        Get available tools from MCP server.
        
        Returns cached tools if available, otherwise fetches from server.
        In discovery mode, returns 5 tools (search, get_schema, list_tools,
        get_tags, execute). In standard mode, returns all 26 application tools.
        
        Checks token expiration before fetching tools.
        
        Returns:
            List of LangChain Tool objects
        
        Raises:
            MCPConnectionError: If not connected
            MCPToolError: If tool retrieval fails
        """
        if not self._connected or not self._mcp_client:
            from gcm_agent.mcp import MCPConnectionError
            raise MCPConnectionError("Not connected to MCP server")
        
        # Check and refresh token before operation
        await self._check_and_refresh_token()
        
        # Return cached tools if available
        if self._tools_cache is not None:
            self.logger.debug(f"Returning {len(self._tools_cache)} cached tools")
            return self._tools_cache
        
        self.logger.info("Fetching tools from MCP server")
        
        try:
            # Get tools from MCP client
            tools = await self._mcp_client.get_tools()
            
            # Cache tools
            self._tools_cache = tools
            
            self.logger.info(
                f"Successfully fetched {len(tools)} tools from MCP server "
                f"(discovery_mode={self.discovery_mode})"
            )
            
            # Log tool names for debugging
            tool_names = [tool.name for tool in tools]
            self.logger.debug(f"Available tools: {', '.join(tool_names)}")
            
            return tools
            
        except Exception as e:
            # Enhanced error logging for TaskGroup and other exceptions
            self.logger.error("=" * 80)
            self.logger.error("DETAILED ERROR INFORMATION FOR TOOL LOADING FAILURE")
            self.logger.error("=" * 80)
            
            # Log exception type and message
            exc_type = type(e).__name__
            self.logger.error(f"Exception Type: {exc_type}")
            self.logger.error(f"Exception Message: {str(e)}")
            
            # Log full traceback
            self.logger.error("\nFull Traceback:")
            self.logger.error(traceback.format_exc())
            
            # For TaskGroup exceptions, try to extract sub-exceptions
            if "TaskGroup" in exc_type or "TaskGroup" in str(e):
                self.logger.error("\nTaskGroup Exception Detected - Attempting to extract sub-exceptions:")
                
                # Try to access __cause__ and __context__ for nested exceptions
                if hasattr(e, '__cause__') and e.__cause__:
                    self.logger.error(f"\n__cause__: {type(e.__cause__).__name__}: {e.__cause__}")
                    self.logger.error("Cause Traceback:")
                    self.logger.error(''.join(traceback.format_exception(type(e.__cause__), e.__cause__, e.__cause__.__traceback__)))
                
                if hasattr(e, '__context__') and e.__context__:
                    self.logger.error(f"\n__context__: {type(e.__context__).__name__}: {e.__context__}")
                    self.logger.error("Context Traceback:")
                    self.logger.error(''.join(traceback.format_exception(type(e.__context__), e.__context__, e.__context__.__traceback__)))
                
                # Try to access exceptions attribute if it's an ExceptionGroup
                if hasattr(e, 'exceptions'):
                    self.logger.error(f"\nFound {len(e.exceptions)} sub-exception(s):")
                    for idx, sub_exc in enumerate(e.exceptions, 1):
                        self.logger.error(f"\nSub-exception {idx}:")
                        self.logger.error(f"  Type: {type(sub_exc).__name__}")
                        self.logger.error(f"  Message: {str(sub_exc)}")
                        self.logger.error("  Traceback:")
                        self.logger.error(''.join(traceback.format_exception(type(sub_exc), sub_exc, sub_exc.__traceback__)))
            
            # Log MCP client state
            self.logger.error("\nMCP Client State:")
            self.logger.error(f"  Connected: {self._connected}")
            self.logger.error(f"  MCP Client: {self._mcp_client is not None}")
            self.logger.error(f"  GCM URL: {self.gcm_url}")
            self.logger.error(f"  GCM Hostname: {self.gcm_hostname}")
            self.logger.error(f"  Discovery Mode: {self.discovery_mode}")
            self.logger.error(f"  Timeout: {self.timeout}s")
            self.logger.error(f"  Verify SSL: {self.verify_ssl}")
            
            # Log Python and system info
            self.logger.error("\nSystem Information:")
            self.logger.error(f"  Python Version: {sys.version}")
            self.logger.error(f"  Platform: {sys.platform}")
            
            self.logger.error("=" * 80)
            
            from gcm_agent.mcp import MCPToolError
            raise MCPToolError(f"Failed to fetch tools: {e}") from e
    
    def _unwrap_params(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Unwrap nested params structure from LangChain MCP adapter.
        
        The LangChain MCP adapter wraps tool parameters in a nested 'params'
        structure: {"params": {"arg1": val1, "arg2": val2}}
        But the GCM MCP server expects flat parameters: {"arg1": val1, "arg2": val2}
        
        This method detects and unwraps the nested structure while preserving
        flat structures that don't need unwrapping.
        
        Args:
            arguments: Tool arguments (may be wrapped or flat)
        
        Returns:
            Unwrapped arguments dictionary
        """
        # Check if arguments contain a nested 'params' dict
        if isinstance(arguments, dict) and "params" in arguments and len(arguments) == 1:
            # Extract the contents of 'params'
            unwrapped = arguments["params"]
            if isinstance(unwrapped, dict):
                self.logger.debug(f"Unwrapped nested params structure: {list(unwrapped.keys())}")
                return unwrapped
        
        # Return original structure if no unwrapping needed
        return arguments
    
    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        Execute a tool on the MCP server.
        
        Checks token expiration before executing the tool.
        Automatically unwraps nested 'params' structures from LangChain MCP adapter.
        
        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments as dictionary
        
        Returns:
            Tool execution result
        
        Raises:
            MCPConnectionError: If not connected
            ToolNotFoundError: If tool not found
            MCPToolError: If tool execution fails
        """
        if not self._connected or not self._mcp_client:
            from gcm_agent.mcp import MCPConnectionError
            raise MCPConnectionError("Not connected to MCP server")
        
        # Check and refresh token before operation
        await self._check_and_refresh_token()
        
        # === JSON DEBUGGING: Log raw arguments ===
        import json
        self.logger.info("=" * 80)
        self.logger.info(f"EXECUTE TOOL DEBUG: '{tool_name}'")
        self.logger.info("=" * 80)
        self.logger.info(f"Raw arguments type: {type(arguments)}")
        self.logger.info(f"Raw arguments: {arguments}")
        
        # Try to serialize arguments to JSON to check for malformed data
        try:
            json_args = json.dumps(arguments, indent=2)
            self.logger.info(f"Arguments as JSON (valid):\n{json_args}")
        except (TypeError, ValueError) as e:
            self.logger.error(f"Arguments cannot be serialized to JSON: {e}")
            self.logger.error(f"This indicates malformed data from LLM")
        
        # Unwrap nested params structure if present (handles LangChain MCP adapter wrapping)
        unwrapped_arguments = self._unwrap_params(arguments)
        
        self.logger.info(f"Unwrapped arguments type: {type(unwrapped_arguments)}")
        self.logger.info(f"Unwrapped arguments: {unwrapped_arguments}")
        
        # Validate unwrapped arguments can be serialized to JSON
        try:
            json_unwrapped = json.dumps(unwrapped_arguments, indent=2)
            self.logger.info(f"Unwrapped arguments as JSON (valid):\n{json_unwrapped}")
        except (TypeError, ValueError) as e:
            self.logger.error(f"Unwrapped arguments cannot be serialized to JSON: {e}")
            self.logger.error(f"This indicates parameter unwrapping introduced malformed data")
        
        try:
            # Get tools to find the requested tool
            tools = await self.get_tools()
            
            # Find the tool
            tool = None
            for t in tools:
                if t.name == tool_name:
                    tool = t
                    break
            
            if tool is None:
                from gcm_agent.mcp import ToolNotFoundError
                raise ToolNotFoundError(f"Tool '{tool_name}' not found")
            
            # Execute the tool with unwrapped arguments
            # LangChain MCP adapter tools return a tuple: (content, artifact)
            # when response_format="content_and_artifact" is set
            result = await tool.ainvoke(unwrapped_arguments)
            
            # Add detailed logging to understand result structure
            import inspect
            self.logger.debug(f"Tool '{tool_name}' result type: {type(result)}")
            self.logger.debug(f"Tool '{tool_name}' result is coroutine: {inspect.iscoroutine(result)}")
            
            # Check if result is a coroutine (some tools may return coroutines)
            # This can happen with the 'execute' tool in discovery mode
            if inspect.iscoroutine(result):
                self.logger.debug(f"Tool '{tool_name}' returned a coroutine, awaiting it")
                result = await result
                self.logger.debug(f"After await - result type: {type(result)}")
            
            # LangChain MCP adapter returns (content, artifact) tuple
            # Extract just the content part for the agent
            if isinstance(result, tuple) and len(result) == 2:
                content, artifact = result
                self.logger.debug(f"Tool returned tuple: content type={type(content)}, artifact type={type(artifact)}")
                actual_result = content
            else:
                self.logger.debug(f"Tool returned non-tuple result: {type(result)}")
                actual_result = result
            
            # === JSON DEBUGGING: Log tool result ===
            self.logger.info(f"Tool result type: {type(actual_result)}")
            self.logger.info(f"Tool result: {actual_result}")
            
            # Try to serialize result to JSON to check for malformed response
            try:
                if isinstance(actual_result, str):
                    # If result is a string, try to parse it as JSON
                    try:
                        parsed_result = json.loads(actual_result)
                        self.logger.info(f"Result is valid JSON string, parsed to: {type(parsed_result)}")
                        json_result = json.dumps(parsed_result, indent=2)
                        self.logger.info(f"Parsed result as JSON:\n{json_result}")
                    except json.JSONDecodeError as je:
                        self.logger.error(f"Result is a string but NOT valid JSON: {je}")
                        self.logger.error(f"Malformed JSON at position {je.pos}: {actual_result[max(0, je.pos-50):je.pos+50]}")
                        self.logger.error(f"This indicates the execute tool returned malformed JSON")
                else:
                    # Result is not a string, try to serialize it
                    json_result = json.dumps(actual_result, indent=2)
                    self.logger.info(f"Result as JSON (valid):\n{json_result}")
            except (TypeError, ValueError) as e:
                self.logger.error(f"Result cannot be serialized to JSON: {e}")
                self.logger.error(f"This indicates the tool returned non-serializable data")
            
            self.logger.info("=" * 80)
            self.logger.info(f"Successfully executed tool '{tool_name}'")
            
            return actual_result
            
        except Exception as e:
            self.logger.error(f"Failed to execute tool '{tool_name}': {e}")
            from gcm_agent.mcp import MCPToolError
            raise MCPToolError(f"Failed to execute tool '{tool_name}': {e}") from e
    
    def is_connected(self) -> bool:
        """
        Check if client is connected to MCP server.
        
        Returns:
            True if connected, False otherwise
        """
        return self._connected
    
    def get_server_info(self) -> Dict[str, Any]:
        """
        Get MCP server information.
        
        Returns:
            Dictionary containing server information
        
        Raises:
            MCPConnectionError: If not connected
        """
        if not self._connected:
            from gcm_agent.mcp import MCPConnectionError
            raise MCPConnectionError("Not connected to MCP server")
        
        return self._server_info or {}
    
    async def _fetch_server_info(self) -> None:
        """
        Fetch server information from MCP server.
        
        Internal method to retrieve and cache server metadata.
        """
        try:
            # Get basic server info
            self._server_info = {
                "url": self.gcm_url,
                "discovery_mode": self.discovery_mode,
                "timeout": self.timeout,
                "connected": self._connected,
            }
            
            self.logger.debug(f"Server info: {self._server_info}")
            
        except Exception as e:
            self.logger.warning(f"Failed to fetch server info: {e}")
            self._server_info = {}
    
    async def reconnect_with_new_factory(self) -> None:
        """
        Reconnect to MCP server with a new client factory.
        
        This is used after token refresh to recreate the MCP client
        with the new authentication token. Preserves connection state
        and clears tool cache to force refetch with new credentials.
        
        Raises:
            MCPConnectionError: If reconnection fails
        """
        self.logger.info("Reconnecting to MCP server with refreshed token")
        
        # Disconnect current client
        await self.disconnect()
        
        # Brief delay before reconnecting
        await asyncio.sleep(0.5)
        
        # Reconnect with new factory (which has the refreshed token)
        await self.connect()
        
        self.logger.info("Successfully reconnected with refreshed token")
    
    async def reconnect(self) -> None:
        """
        Reconnect to MCP server.
        
        Disconnects and reconnects to the MCP server. Useful for
        recovering from connection errors.
        
        Raises:
            MCPConnectionError: If reconnection fails
        """
        self.logger.info("Reconnecting to MCP server")
        
        await self.disconnect()
        await asyncio.sleep(1)  # Brief delay before reconnecting
        await self.connect()
        
        self.logger.info("Successfully reconnected to MCP server")
    
    def clear_cache(self) -> None:
        """
        Clear cached tools.
        
        Forces tools to be refetched on next get_tools() call.
        """
        self._tools_cache = None
        self.logger.debug("Cleared tools cache")
    
    # Async context manager support
    async def __aenter__(self):
        """Enter async context manager."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context manager."""
        await self.disconnect()
        return False
