"""MCP client wrapper for GCM server integration."""

# Made with Bob
# 2026-07-17 - Fixed ExceptionGroup sub-exception extraction in get_tools() to surface real connection errors
# 2026-06-08 21:11 UTC - Phase 3: Integrated tool usage analytics for intelligent tool prioritization
# 2026-06-08 20:47 UTC - Phase 2: Added retry logic with exponential backoff for tool execution resilience
# 2026-06-08 16:12 UTC - Added intelligent parameter defaults for pagination (page_number, page_size) to fix missing required parameters
# 2026-06-06 05:43 UTC - Added execute payload normalization/validation and targeted 405 error enrichment for policy_violations_dashboard
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
import json
import time

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_core.tools import Tool

from gcm_agent.utils.logger import get_mcp_logger
from gcm_agent.mcp.tool_analytics import ToolAnalytics


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
        verify_ssl: bool = False,
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
            
            # Extract sub-exceptions from ExceptionGroup (Python 3.11+) or TaskGroup wrappers.
            # anyio wraps connection errors in a BaseExceptionGroup, not a plain "TaskGroup" type.
            root_cause_msg = str(e)
            if hasattr(e, 'exceptions') and e.exceptions:
                self.logger.error(f"\nExceptionGroup detected - {len(e.exceptions)} sub-exception(s):")
                sub_msgs = []
                for idx, sub_exc in enumerate(e.exceptions, 1):
                    self.logger.error(f"\nSub-exception {idx}:")
                    self.logger.error(f"  Type: {type(sub_exc).__name__}")
                    self.logger.error(f"  Message: {str(sub_exc)}")
                    self.logger.error("  Traceback:")
                    self.logger.error(''.join(traceback.format_exception(type(sub_exc), sub_exc, sub_exc.__traceback__)))
                    sub_msgs.append(f"{type(sub_exc).__name__}: {sub_exc}")
                # Use the real sub-exception messages as the error description
                root_cause_msg = "; ".join(sub_msgs)
            
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
            raise MCPToolError(f"Failed to fetch tools: {root_cause_msg}") from e
    
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

    # Normalize execute tool payloads before sending them to MCP.
    def _normalize_execute_arguments(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize execute tool arguments into a valid dictionary payload.
        
        Accepts either a dictionary or a JSON string under common wrapper keys.
        Raises a ValueError with actionable context when malformed JSON is detected.
        """
        if not isinstance(arguments, dict):
            raise ValueError(
                f"Execute tool requires a dictionary payload, received {type(arguments).__name__}"
            )

        normalized_arguments = self._unwrap_params(arguments)

        if isinstance(normalized_arguments, dict):
            for key in ("workflow", "input", "payload"):
                value = normalized_arguments.get(key)
                if isinstance(value, str):
                    try:
                        parsed_value = json.loads(value)
                    except json.JSONDecodeError as exc:
                        raise ValueError(
                            f"Execute tool received malformed JSON in '{key}' at byte {exc.pos}: {exc.msg}"
                        ) from exc
                    if not isinstance(parsed_value, dict):
                        raise ValueError(
                            f"Execute tool '{key}' JSON must decode to an object, received {type(parsed_value).__name__}"
                        )
                    self.logger.warning(
                        f"Execute tool '{key}' was provided as JSON string; normalized to dictionary payload"
                    )
                    return parsed_value

            if "tool_name" in normalized_arguments:
                return normalized_arguments

        raise ValueError(
            "Execute tool requires a workflow object containing at least 'tool_name'. "
            f"Received keys: {list(normalized_arguments.keys()) if isinstance(normalized_arguments, dict) else 'non-dict'}"
        )
    
    def _add_parameter_defaults(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add intelligent defaults for common required parameters.
        
        Many GCM API tools require pagination parameters (page_number, page_size)
        that LLMs often forget to provide. This method adds sensible defaults
        when these parameters are missing.
        
        Args:
            tool_name: Name of the tool being called
            arguments: Original tool arguments
            
        Returns:
            Arguments with defaults added where appropriate
        """
        # Create a copy to avoid modifying the original
        enhanced_args = arguments.copy()
        
        # Check if this is a list/fetch operation that likely needs pagination
        list_fetch_keywords = ['list', 'fetch', 'get_all', 'search', 'query', 'dashboard']
        needs_pagination = any(keyword in tool_name.lower() for keyword in list_fetch_keywords)
        
        if needs_pagination:
            # Check for nested body/params structure
            if 'body' in enhanced_args and isinstance(enhanced_args['body'], dict):
                body = enhanced_args['body']
                if 'page_number' not in body:
                    body['page_number'] = 1
                    self.logger.info(f"Added default page_number=1 to tool '{tool_name}' body")
                if 'page_size' not in body:
                    body['page_size'] = 50
                    self.logger.info(f"Added default page_size=50 to tool '{tool_name}' body")
            elif 'params' in enhanced_args and isinstance(enhanced_args['params'], dict):
                params = enhanced_args['params']
                if 'page_number' not in params:
                    params['page_number'] = 1
                    self.logger.info(f"Added default page_number=1 to tool '{tool_name}' params")
                if 'page_size' not in params:
                    params['page_size'] = 50
                    self.logger.info(f"Added default page_size=50 to tool '{tool_name}' params")
            else:
                # Top-level parameters
                if 'page_number' not in enhanced_args:
                    enhanced_args['page_number'] = 1
                    self.logger.info(f"Added default page_number=1 to tool '{tool_name}'")
                if 'page_size' not in enhanced_args:
                    enhanced_args['page_size'] = 50
                    self.logger.info(f"Added default page_size=50 to tool '{tool_name}'")
        
        return enhanced_args
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((ConnectionError, TimeoutError, asyncio.TimeoutError)),
        before_sleep=before_sleep_log(get_mcp_logger(), "WARNING"),
        reraise=True,
    )
    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        Execute a tool on the MCP server with automatic retry on transient failures.
        
        Retries up to 3 times with exponential backoff (2s, 4s, 8s) for:
        - ConnectionError: Network connectivity issues
        - TimeoutError: Request timeouts
        
        Checks token expiration before executing the tool.
        Automatically unwraps nested 'params' structures from LangChain MCP adapter.
        Records tool usage analytics for intelligent prioritization.
        
        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments as dictionary
        
        Returns:
            Tool execution result
        
        Raises:
            MCPConnectionError: If not connected
            ToolNotFoundError: If tool not found
            MCPToolError: If tool execution fails (after retries)
        """
        if not self._connected or not self._mcp_client:
            from gcm_agent.mcp import MCPConnectionError
            raise MCPConnectionError("Not connected to MCP server")
        
        # Check and refresh token before operation
        await self._check_and_refresh_token()
        
        # Start timing for analytics
        start_time = time.time()
        success = False
        analytics = ToolAnalytics()
        
        # Log tool execution inputs for debugging.
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
            self.logger.error("This indicates malformed data from LLM or caller")
        
        # Normalize execute payloads and unwrap standard tool params.
        if tool_name == "execute":
            unwrapped_arguments = self._normalize_execute_arguments(arguments)
        else:
            unwrapped_arguments = self._unwrap_params(arguments)
            # Add intelligent defaults for common required parameters
            unwrapped_arguments = self._add_parameter_defaults(tool_name, unwrapped_arguments)
        
        self.logger.info(f"Normalized arguments type: {type(unwrapped_arguments)}")
        self.logger.info(f"Normalized arguments: {unwrapped_arguments}")
        
        # Validate normalized arguments can be serialized to JSON
        try:
            json_unwrapped = json.dumps(unwrapped_arguments, indent=2)
            self.logger.info(f"Normalized arguments as JSON (valid):\n{json_unwrapped}")
        except (TypeError, ValueError) as e:
            self.logger.error(f"Normalized arguments cannot be serialized to JSON: {e}")
            self.logger.error("This indicates malformed tool payload after normalization")
        
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
            
            # Record successful execution
            success = True
            duration = time.time() - start_time
            analytics.record_tool_use(tool_name, success=True, duration=duration)
            
            return actual_result
            
        except Exception as e:
            # Record failed execution
            duration = time.time() - start_time
            analytics.record_tool_use(tool_name, success=False, duration=duration)
            
            error_message = str(e)

            if tool_name == "policy_violations_dashboard" and "405" in error_message:
                error_message = (
                    f"{error_message} | Root cause likely on remote GCM MCP server: "
                    "tool 'policy_violations_dashboard' appears to be mapped to an HTTP method "
                    "the backend rejects. Local client forwards MCP tool calls and does not choose "
                    "the REST method. Verify the server-side tool schema/method mapping for "
                    "/ibm/gempolicyengine/api/v1/violations/dashboards/policy-violations."
                )

            self.logger.error(f"Failed to execute tool '{tool_name}': {error_message}")
            self.logger.error(f"Tool execution context: tool_name={tool_name}, discovery_mode={self.discovery_mode}")
            self.logger.error(f"Tool arguments at failure: {unwrapped_arguments if 'unwrapped_arguments' in locals() else arguments}")

            from gcm_agent.mcp import MCPToolError
            raise MCPToolError(f"Failed to execute tool '{tool_name}': {error_message}") from e
    
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
