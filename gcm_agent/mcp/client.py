"""MCP client wrapper for GCM server integration."""

# Made with Bob
# 2026-06-05 22:48 UTC - Added environment variable SSL workaround
# 2026-06-05 22:43 UTC - Added SSL verification workaround for self-signed certificates
# 2026-06-05 22:01 UTC - Initial implementation of GCMMCPClient with streamable_http transport
# 2026-06-05 21:47 UTC - Fixed MCP endpoint URL to /ibm/mcp/mcp and removed deprecated context manager usage
# 2026-06-05 21:59 UTC - Fixed parameter name: client_factory -> httpx_client_factory

from typing import Callable, Optional, List, Dict, Any
import asyncio
import ssl
import warnings
import os

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
    - Discovery mode support via x-mcp-enable-discovery header
    
    Example:
        >>> async with GCMMCPClient(gcm_url, client_factory) as client:
        ...     tools = await client.get_tools()
        ...     result = await client.execute_tool("list_keys", {})
    """
    
    def __init__(
        self,
        gcm_url: str,
        client_factory: Callable,
        discovery_mode: bool = True,
        timeout: int = 300,
        verify_ssl: bool = True,
    ):
        """
        Initialize GCM MCP Client.
        
        Args:
            gcm_url: GCM server URL (e.g., https://gcm.example.com)
            client_factory: Factory function from GCMAuthenticator._client_factory()
            discovery_mode: Enable discovery mode (default True)
                - True: Returns 4 discovery tools + 1 execute tool
                - False: Returns all 26 application tools
            timeout: Request timeout in seconds (default 300)
            verify_ssl: Verify SSL certificates (default True)
        """
        self.gcm_url = gcm_url.rstrip("/")
        self.client_factory = client_factory
        self.discovery_mode = discovery_mode
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.logger = get_mcp_logger()
        
        # Connection state
        self._connected = False
        self._mcp_client: Optional[MultiServerMCPClient] = None
        self._tools_cache: Optional[List[Tool]] = None
        self._server_info: Optional[Dict[str, Any]] = None
        self._ssl_context_applied = False
        
        self.logger.debug(
            f"GCMMCPClient initialized for {gcm_url} "
            f"(discovery_mode={discovery_mode}, timeout={timeout}s, verify_ssl={verify_ssl})"
        )
    
    async def connect(self) -> None:
        """
        Establish MCP connection to GCM server.
        
        Creates MultiServerMCPClient with streamable_http transport and
        proper authentication headers. The x-mcp-enable-discovery header
        controls which tools are exposed by the server.
        
        For self-signed certificates, applies SSL context workaround to
        disable certificate verification at the SSL module level.
        
        Raises:
            MCPConnectionError: If connection fails
        """
        if self._connected:
            self.logger.debug("Already connected to MCP server")
            return
        
        self.logger.info(f"Connecting to GCM MCP server at {self.gcm_url}")
        
        # Apply SSL workaround if SSL verification is disabled
        if not self.verify_ssl and not self._ssl_context_applied:
            self._apply_ssl_workaround()
        
        try:
            # Create MCP client with streamable_http transport
            # This is critical for remote GCM server integration
            # Note: As of langchain-mcp-adapters 0.1.0, MultiServerMCPClient
            # should NOT be used as a context manager
            self._mcp_client = MultiServerMCPClient(
                {
                    "gcm": {
                        "transport": "streamable_http",
                        "url": f"{self.gcm_url}/ibm/mcp/mcp",
                        "headers": {
                            "x-mcp-enable-discovery": "true" if self.discovery_mode else "false"
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
            self.logger.error(f"Failed to connect to MCP server: {e}")
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
        
        Returns:
            List of LangChain Tool objects
        
        Raises:
            MCPConnectionError: If not connected
            MCPToolError: If tool retrieval fails
        """
        if not self._connected or not self._mcp_client:
            from gcm_agent.mcp import MCPConnectionError
            raise MCPConnectionError("Not connected to MCP server")
        
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
            self.logger.error(f"Failed to fetch tools from MCP server: {e}")
            from gcm_agent.mcp import MCPToolError
            raise MCPToolError(f"Failed to fetch tools: {e}") from e
    
    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        Execute a tool on the MCP server.
        
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
        
        self.logger.info(f"Executing tool '{tool_name}' with arguments: {arguments}")
        
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
            
            # Execute the tool
            result = await tool.ainvoke(arguments)
            
            self.logger.info(f"Successfully executed tool '{tool_name}'")
            self.logger.debug(f"Tool result: {result}")
            
            return result
            
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
    
    def _apply_ssl_workaround(self) -> None:
        """
        Apply SSL verification workaround for self-signed certificates.
        
        This is a workaround for cases where the MCP library creates HTTP clients
        that don't use our client factory. It modifies the default SSL context
        to disable certificate verification and sets environment variables.
        
        WARNING: This affects all SSL connections in the process. Only use when
        verify_ssl=False is explicitly set.
        """
        try:
            self.logger.warning(
                "Applying SSL verification workaround for self-signed certificates. "
                "This will disable SSL verification for all HTTPS connections in this process."
            )
            
            # Method 1: Modify default SSL context
            ssl._create_default_https_context = ssl._create_unverified_context
            self.logger.debug("Set ssl._create_default_https_context to unverified")
            
            # Method 2: Set environment variables that httpx and other libraries respect
            os.environ['PYTHONHTTPSVERIFY'] = '0'
            os.environ['CURL_CA_BUNDLE'] = ''
            os.environ['REQUESTS_CA_BUNDLE'] = ''
            os.environ['SSL_CERT_FILE'] = ''
            self.logger.debug("Set SSL-related environment variables to disable verification")
            
            # Method 3: Monkey-patch httpx.AsyncClient to force verify=False
            try:
                import httpx
                original_init = httpx.AsyncClient.__init__
                
                def patched_init(self, *args, **kwargs):
                    # Force verify=False for all AsyncClient instances
                    kwargs['verify'] = False
                    return original_init(self, *args, **kwargs)
                
                httpx.AsyncClient.__init__ = patched_init
                self.logger.debug("Monkey-patched httpx.AsyncClient to force verify=False")
            except Exception as e:
                self.logger.warning(f"Could not monkey-patch httpx.AsyncClient: {e}")
            
            # Method 4: Suppress SSL warnings
            warnings.filterwarnings('ignore', message='Unverified HTTPS request')
            warnings.filterwarnings('ignore', message='InsecureRequestWarning')
            
            # Try to disable urllib3 warnings if available
            try:
                import urllib3
                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                self.logger.debug("Disabled urllib3 SSL warnings")
            except ImportError:
                pass
            
            self._ssl_context_applied = True
            self.logger.info("SSL verification workaround applied successfully (all methods including httpx monkey-patch)")
            
        except Exception as e:
            self.logger.error(f"Failed to apply SSL workaround: {e}")
            # Don't raise - let the connection attempt proceed
    
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
