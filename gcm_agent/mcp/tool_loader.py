"""Tool loader for dynamic tool loading from GCM MCP server."""

# Made with Bob
# 2026-06-08 21:12 UTC - Phase 3: Added force refresh, analytics integration, and intelligent tool prioritization
# 2026-06-05 22:02 UTC - Initial implementation of GCMToolLoader with caching and discovery mode support

from typing import List, Dict, Optional, Any
import time

from langchain_core.tools import Tool

from gcm_agent.utils.logger import get_mcp_logger
from gcm_agent.mcp.tool_analytics import ToolAnalytics


class ToolCache:
    """
    Cache for MCP tools with TTL (Time To Live) support.
    
    Caches tools to avoid repeated fetches from the MCP server,
    improving performance. Each cache entry has a timestamp and
    is considered expired after the TTL period.
    """
    
    def __init__(self, ttl: int = 3600):
        """
        Initialize tool cache.
        
        Args:
            ttl: Time to live in seconds (default: 3600 = 1 hour)
        """
        self._cache: Dict[str, List[Tool]] = {}
        self._timestamps: Dict[str, float] = {}
        self._ttl = ttl
        self.logger = get_mcp_logger()
        
        self.logger.debug(f"ToolCache initialized with TTL={ttl}s")
    
    def get(self, key: str) -> Optional[List[Tool]]:
        """
        Get cached tools if not expired.
        
        Args:
            key: Cache key
        
        Returns:
            List of tools if found and not expired, None otherwise
        """
        if key not in self._cache:
            return None
        
        if self.is_expired(key):
            self.logger.debug(f"Cache entry '{key}' expired")
            self._cache.pop(key, None)
            self._timestamps.pop(key, None)
            return None
        
        self.logger.debug(f"Cache hit for '{key}' ({len(self._cache[key])} tools)")
        return self._cache[key]
    
    def set(self, key: str, tools: List[Tool]) -> None:
        """
        Cache tools with timestamp.
        
        Args:
            key: Cache key
            tools: List of tools to cache
        """
        self._cache[key] = tools
        self._timestamps[key] = time.time()
        self.logger.debug(f"Cached {len(tools)} tools for '{key}'")
    
    def is_expired(self, key: str) -> bool:
        """
        Check if cache entry is expired.
        
        Args:
            key: Cache key
        
        Returns:
            True if expired or not found, False otherwise
        """
        if key not in self._timestamps:
            return True
        
        age = time.time() - self._timestamps[key]
        return age > self._ttl
    
    def clear(self) -> None:
        """Clear all cache entries."""
        count = len(self._cache)
        self._cache.clear()
        self._timestamps.clear()
        self.logger.debug(f"Cleared cache ({count} entries)")
    
    def clear_key(self, key: str) -> None:
        """
        Clear specific cache entry.
        
        Args:
            key: Cache key to clear
        """
        self._cache.pop(key, None)
        self._timestamps.pop(key, None)
        self.logger.debug(f"Cleared cache entry '{key}'")


class GCMToolLoader:
    """
    Tool loader for GCM MCP server.
    
    Provides methods to load, search, and filter tools from the GCM MCP server.
    Supports both discovery mode (dynamic tool loading) and standard mode
    (all tools loaded). Implements caching to improve performance.
    
    Discovery Mode Tools (when enabled):
    - search_tools: Search for available tools
    - get_schema: Get schema for specific tool
    - list_tools: List all available tools
    - get_tags: Get available OpenAPI tags
    - execute: Execute tool in sandboxed environment
    
    Standard Mode Tools (when disabled):
    - All 26 GCM application tools loaded directly
    
    Example:
        >>> tool_loader = GCMToolLoader(mcp_client)
        >>> tools = await tool_loader.load_tools()
        >>> key_tools = await tool_loader.load_tools_by_tag("keys")
    """
    
    def __init__(self, mcp_client, cache_ttl: int = 3600):
        """
        Initialize tool loader.
        
        Args:
            mcp_client: GCMMCPClient instance
            cache_ttl: Cache TTL in seconds (default: 3600 = 1 hour)
        """
        self.mcp_client = mcp_client
        self.cache = ToolCache(ttl=cache_ttl)
        self.logger = get_mcp_logger()
        
        self.analytics = ToolAnalytics()
        self.logger.debug(f"GCMToolLoader initialized with cache_ttl={cache_ttl}s")
    
    async def load_tools(self, force_refresh: bool = False) -> List[Tool]:
        """
        Load all tools from MCP server.
        
        Returns cached tools if available and not expired, otherwise
        fetches from server. In discovery mode, returns 5 discovery tools.
        In standard mode, returns all 26 application tools.
        
        Args:
            force_refresh: If True, bypass cache and fetch fresh tools
        
        Returns:
            List of LangChain Tool objects
        
        Raises:
            MCPConnectionError: If not connected to MCP server
            MCPToolError: If tool loading fails
        """
        cache_key = "all_tools"
        
        # Check cache first (unless force refresh)
        if not force_refresh:
            cached_tools = self.cache.get(cache_key)
            if cached_tools is not None:
                return cached_tools
        
        self.logger.info("Loading tools from MCP server")
        
        try:
            # Get tools from MCP client
            tools = await self.mcp_client.get_tools()
            
            # Cache tools
            self.cache.set(cache_key, tools)
            
            self.logger.info(f"Successfully loaded {len(tools)} tools")
            
            return tools
            
        except Exception as e:
            self.logger.error(f"Failed to load tools: {e}")
            from gcm_agent.mcp import MCPToolError
            raise MCPToolError(f"Failed to load tools: {e}") from e
    
    async def load_tools_by_tag(self, tag: str) -> List[Tool]:
        """
        Load tools by OpenAPI tag.
        
        Filters tools based on their OpenAPI tag. This is useful for
        loading only specific categories of tools (e.g., "keys", "certificates").
        
        Note: Tag filtering works best in standard mode. In discovery mode,
        use the get_tags and search_tools discovery tools instead.
        
        Args:
            tag: OpenAPI tag to filter by
        
        Returns:
            List of tools matching the tag
        
        Raises:
            MCPToolError: If tool loading fails
        """
        cache_key = f"tag_{tag}"
        
        # Check cache first
        cached_tools = self.cache.get(cache_key)
        if cached_tools is not None:
            return cached_tools
        
        self.logger.info(f"Loading tools for tag '{tag}'")
        
        try:
            # Get all tools
            all_tools = await self.load_tools()
            
            # Filter by tag
            # Note: Tool metadata may contain tag information
            # This is a simplified implementation - actual tag filtering
            # may require accessing tool metadata or using discovery tools
            filtered_tools = []
            for tool in all_tools:
                # Check if tool name or description contains tag
                # This is a heuristic approach
                if tag.lower() in tool.name.lower() or tag.lower() in tool.description.lower():
                    filtered_tools.append(tool)
            
            # Cache filtered tools
            self.cache.set(cache_key, filtered_tools)
            
            self.logger.info(f"Found {len(filtered_tools)} tools for tag '{tag}'")
            
            return filtered_tools
            
        except Exception as e:
            self.logger.error(f"Failed to load tools by tag '{tag}': {e}")
            from gcm_agent.mcp import MCPToolError
            raise MCPToolError(f"Failed to load tools by tag: {e}") from e
    
    async def search_tools(self, query: str) -> List[Tool]:
        """
        Search for tools matching query.
        
        In discovery mode, uses the search_tools discovery tool to search
        the MCP server. In standard mode, performs local search on loaded tools.
        
        Args:
            query: Search query string
        
        Returns:
            List of tools matching the query
        
        Raises:
            MCPToolError: If search fails
        """
        self.logger.info(f"Searching tools with query: '{query}'")
        
        try:
            # Check if in discovery mode
            if self.mcp_client.discovery_mode:
                # Use search_tools discovery tool
                result = await self.mcp_client.execute_tool(
                    "search_tools",
                    {"query": query}
                )
                
                # Parse result and convert to tools
                # Note: This is a simplified implementation
                # Actual implementation depends on search_tools response format
                self.logger.info(f"Search returned: {result}")
                
                # For now, fall back to local search
                # In production, parse the search result properly
                return await self._local_search(query)
            else:
                # Perform local search
                return await self._local_search(query)
                
        except Exception as e:
            self.logger.error(f"Failed to search tools: {e}")
            from gcm_agent.mcp import MCPToolError
            raise MCPToolError(f"Failed to search tools: {e}") from e
    
    async def _local_search(self, query: str) -> List[Tool]:
        """
        Perform local search on loaded tools.
        
        Args:
            query: Search query string
        
        Returns:
            List of tools matching the query
        """
        # Get all tools
        all_tools = await self.load_tools()
        
        # Search in tool name and description
        query_lower = query.lower()
        matching_tools = []
        
        for tool in all_tools:
            if (query_lower in tool.name.lower() or 
                query_lower in tool.description.lower()):
                matching_tools.append(tool)
        
        self.logger.info(f"Local search found {len(matching_tools)} matching tools")
        
        return matching_tools
    
    async def get_tool_schema(self, tool_name: str) -> Dict[str, Any]:
        """
        Get schema for specific tool.
        
        In discovery mode, uses the get_schema discovery tool to retrieve
        the tool's schema from the MCP server. In standard mode, extracts
        schema from loaded tool.
        
        Args:
            tool_name: Name of the tool
        
        Returns:
            Tool schema as dictionary
        
        Raises:
            ToolNotFoundError: If tool not found
            MCPToolError: If schema retrieval fails
        """
        self.logger.info(f"Getting schema for tool '{tool_name}'")
        
        try:
            # Check if in discovery mode
            if self.mcp_client.discovery_mode:
                # Use get_schema discovery tool
                result = await self.mcp_client.execute_tool(
                    "get_schema",
                    {"tool_name": tool_name}
                )
                
                self.logger.info(f"Retrieved schema for '{tool_name}'")
                return result
            else:
                # Get schema from loaded tool
                all_tools = await self.load_tools()
                
                for tool in all_tools:
                    if tool.name == tool_name:
                        # Extract schema from tool
                        schema = {
                            "name": tool.name,
                            "description": tool.description,
                            "args_schema": tool.args if hasattr(tool, "args") else None,
                        }
                        return schema
                
                # Tool not found
                from gcm_agent.mcp import ToolNotFoundError
                raise ToolNotFoundError(f"Tool '{tool_name}' not found")
                
        except Exception as e:
            self.logger.error(f"Failed to get schema for '{tool_name}': {e}")
            from gcm_agent.mcp import MCPToolError
            raise MCPToolError(f"Failed to get tool schema: {e}") from e
    
    def get_cached_tools(self) -> Optional[List[Tool]]:
        """
        Get cached tools without fetching from server.
        
        Returns:
            List of cached tools if available and not expired, None otherwise
        """
        return self.cache.get("all_tools")
    
    def clear_cache(self, key: Optional[str] = None) -> None:
        """
        Clear tool cache.
        
        Forces tools to be refetched on next load operation.
        
        Args:
            key: Specific cache key to clear, or None to clear all
        """
        if key:
            self.cache.clear_key(key)
            self.logger.info(f"Cleared cache for key '{key}'")
        else:
            self.cache.clear()
            self.logger.info("Cleared all tool cache")
    
    async def load_prioritized_tools(self, force_refresh: bool = False) -> List[Tool]:
        """
        Load tools prioritized by usage analytics.
        
        Returns tools sorted by usage frequency and success rate,
        with most important tools first. This helps the LLM select
        the right tools faster by presenting commonly used tools first.
        
        Args:
            force_refresh: If True, bypass cache and fetch fresh tools
        
        Returns:
            List of tools sorted by priority (most important first)
        
        Raises:
            MCPConnectionError: If not connected to MCP server
            MCPToolError: If tool loading fails
        """
        # Load all tools
        all_tools = await self.load_tools(force_refresh=force_refresh)
        
        # Get prioritized tool names from analytics
        prioritized_names = self.analytics.get_prioritized_tool_list()
        
        if not prioritized_names:
            # No analytics data yet, return tools as-is
            self.logger.info("No analytics data available, returning unprioritized tools")
            return all_tools
        
        # Create a mapping of tool name to tool object
        tool_map = {tool.name: tool for tool in all_tools}
        
        # Build prioritized list
        prioritized_tools = []
        seen_tools = set()
        
        # Add tools in priority order
        for tool_name in prioritized_names:
            if tool_name in tool_map:
                prioritized_tools.append(tool_map[tool_name])
                seen_tools.add(tool_name)
        
        # Add any remaining tools that weren't in analytics
        for tool in all_tools:
            if tool.name not in seen_tools:
                prioritized_tools.append(tool)
        
        self.logger.info(
            f"Prioritized {len(prioritized_tools)} tools based on usage analytics "
            f"({len(prioritized_names)} with analytics data)"
        )
        
        return prioritized_tools
    
    def get_tool_analytics_summary(self) -> Dict[str, Any]:
        """
        Get summary of tool usage analytics.
        
        Returns:
            Dictionary with analytics summary including:
            - most_used: Top 10 most used tools
            - total_tools_tracked: Number of tools with analytics data
            - recent_pattern: Usage pattern for last 24 hours
        """
        most_used = self.analytics.get_most_used_tools(limit=10)
        recent_pattern = self.analytics.get_recent_usage_pattern(hours=24)
        all_stats = self.analytics.get_all_statistics()
        
        return {
            "most_used": most_used,
            "total_tools_tracked": len(all_stats),
            "recent_pattern": recent_pattern,
            "statistics": all_stats,
        }
    
    async def list_available_tags(self) -> List[str]:
        """
        List available OpenAPI tags.
        
        In discovery mode, uses the get_tags discovery tool. In standard mode,
        extracts tags from loaded tools.
        
        Returns:
            List of available tags
        
        Raises:
            MCPToolError: If tag listing fails
        """
        self.logger.info("Listing available tags")
        
        try:
            # Check if in discovery mode
            if self.mcp_client.discovery_mode:
                # Use get_tags discovery tool
                result = await self.mcp_client.execute_tool("get_tags", {})
                
                # Parse result
                # Note: Actual implementation depends on get_tags response format
                self.logger.info(f"Available tags: {result}")
                return result if isinstance(result, list) else []
            else:
                # Extract tags from loaded tools
                all_tools = await self.load_tools()
                
                # Extract unique tags from tool names/descriptions
                # This is a heuristic approach
                tags = set()
                for tool in all_tools:
                    # Extract potential tags from tool name
                    # e.g., "list_keys" -> "keys"
                    parts = tool.name.split("_")
                    if len(parts) > 1:
                        tags.add(parts[-1])
                
                tag_list = sorted(list(tags))
                self.logger.info(f"Extracted {len(tag_list)} tags from tools")
                
                return tag_list
                
        except Exception as e:
            self.logger.error(f"Failed to list tags: {e}")
            from gcm_agent.mcp import MCPToolError
            raise MCPToolError(f"Failed to list tags: {e}") from e
    
    async def get_tool_count(self) -> int:
        """
        Get total number of available tools.
        
        Returns:
            Number of tools
        """
        tools = await self.load_tools()
        return len(tools)
    
    def is_discovery_mode(self) -> bool:
        """
        Check if tool loader is in discovery mode.
        
        Returns:
            True if in discovery mode, False otherwise
        """
        return self.mcp_client.discovery_mode
