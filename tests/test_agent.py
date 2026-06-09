"""Tests for LangGraph agent initialization, prompt wiring, and tool orchestration."""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from gcm_agent.agent.gcm_agent import GCMAgent
from gcm_agent.agent.prompts import get_system_prompt
from gcm_agent.config.config_manager import WatsonXConfig, AgentConfig, LLMProviderConfig


class TestGCMAgent:
    """Test GCM agent functionality."""
    
    @pytest.mark.asyncio
    @patch('gcm_agent.agent.gcm_agent.ChatWatsonx')
    @patch('langchain.agents.create_agent')
    async def test_initialize_agent(self, mock_create_agent, mock_llm_class):
        """Test agent initialization with LLM and tools."""
        mock_llm = Mock()
        mock_llm_class.return_value = mock_llm
        
        mock_graph = Mock()
        mock_create_agent.return_value = mock_graph
        
        mock_mcp_client = AsyncMock()
        mock_tool_loader = AsyncMock()
        mock_tool_loader.load_tools.return_value = [Mock(name='test_tool')]
        
        watsonx_config = WatsonXConfig(
            project_id='test_project_id',
            model='ibm/granite-13b-chat-v2'
        )
        agent_config = AgentConfig(
            discovery_mode=False,
            max_iterations=10
        )
        llm_config = LLMProviderConfig(
            provider='watsonx',
            watsonx_config=watsonx_config,
            watsonx_api_key='test_api_key'
        )
        
        agent = GCMAgent(
            mcp_client=mock_mcp_client,
            tool_loader=mock_tool_loader,
            agent_config=agent_config,
            llm_config=llm_config
        )
        
        await agent.initialize()
        
        assert mock_llm_class.called
        assert mock_create_agent.called
    
    @pytest.mark.asyncio
    @patch('gcm_agent.agent.gcm_agent.ChatWatsonx')
    @patch('langchain.agents.create_agent')
    async def test_chat(self, mock_create_agent, mock_llm_class):
        """Test processing a user message through the agent."""
        from langchain_core.messages import AIMessage
        
        mock_llm = Mock()
        mock_llm_class.return_value = mock_llm
        
        mock_graph = AsyncMock()
        mock_graph.ainvoke.return_value = {
            'messages': [
                AIMessage(content='Test response')
            ]
        }
        mock_create_agent.return_value = mock_graph
        
        mock_mcp_client = AsyncMock()
        mock_tool_loader = AsyncMock()
        mock_tool_loader.load_tools.return_value = [Mock(name='test_tool')]
        
        watsonx_config = WatsonXConfig(
            project_id='test_project_id',
            model='ibm/granite-13b-chat-v2'
        )
        agent_config = AgentConfig(
            discovery_mode=False,
            max_iterations=10
        )
        llm_config = LLMProviderConfig(
            provider='watsonx',
            watsonx_config=watsonx_config,
            watsonx_api_key='test_api_key'
        )
        
        agent = GCMAgent(
            mcp_client=mock_mcp_client,
            tool_loader=mock_tool_loader,
            agent_config=agent_config,
            llm_config=llm_config
        )
        
        await agent.initialize()
        response = await agent.chat('Test query')
        
        assert response == 'Test response'
        assert mock_graph.ainvoke.called
    
    @pytest.mark.asyncio
    @patch('gcm_agent.agent.gcm_agent.ChatWatsonx')
    @patch('langchain.agents.create_agent')
    async def test_agent_with_tools(self, mock_create_agent, mock_llm_class):
        """Test agent initialization with multiple tools."""
        mock_llm = Mock()
        mock_llm_class.return_value = mock_llm
        
        mock_graph = Mock()
        mock_create_agent.return_value = mock_graph
        
        mock_mcp_client = AsyncMock()
        mock_tool_loader = AsyncMock()
        mock_tool_loader.load_tools.return_value = [
            Mock(name='list_keys'),
            Mock(name='create_key'),
            Mock(name='delete_key')
        ]
        
        watsonx_config = WatsonXConfig(
            project_id='test_project_id',
            model='ibm/granite-13b-chat-v2'
        )
        agent_config = AgentConfig(
            discovery_mode=False,
            max_iterations=10
        )
        llm_config = LLMProviderConfig(
            provider='watsonx',
            watsonx_config=watsonx_config,
            watsonx_api_key='test_api_key'
        )
        
        agent = GCMAgent(
            mcp_client=mock_mcp_client,
            tool_loader=mock_tool_loader,
            agent_config=agent_config,
            llm_config=llm_config
        )
        
        await agent.initialize()
        
        # Verify tools were passed to agent creation
        call_args = mock_create_agent.call_args
        assert call_args is not None
    
    @pytest.mark.asyncio
    @patch('gcm_agent.agent.gcm_agent.ChatWatsonx')
    @patch('langchain.agents.create_agent')
    async def test_agent_history(self, mock_create_agent, mock_llm_class):
        """Test agent maintains conversation history."""
        from langchain_core.messages import AIMessage
        
        mock_llm = Mock()
        mock_llm_class.return_value = mock_llm
        
        mock_graph = AsyncMock()
        mock_graph.ainvoke.return_value = {
            'messages': [
                AIMessage(content='Response 1')
            ]
        }
        mock_create_agent.return_value = mock_graph
        
        mock_mcp_client = AsyncMock()
        mock_tool_loader = AsyncMock()
        mock_tool_loader.load_tools.return_value = [Mock(name='test_tool')]
        
        watsonx_config = WatsonXConfig(
            project_id='test_project_id',
            model='ibm/granite-13b-chat-v2'
        )
        agent_config = AgentConfig(
            discovery_mode=False,
            max_iterations=10
        )
        llm_config = LLMProviderConfig(
            provider='watsonx',
            watsonx_config=watsonx_config,
            watsonx_api_key='test_api_key'
        )
        
        agent = GCMAgent(
            mcp_client=mock_mcp_client,
            tool_loader=mock_tool_loader,
            agent_config=agent_config,
            llm_config=llm_config
        )
        
        await agent.initialize()
        
        # Process multiple messages
        await agent.chat('Query 1')
        await agent.chat('Query 2')
        
        # Verify history is maintained
        assert len(agent.history) > 0


class TestSystemPrompt:
    """Test system prompt configuration."""
    
    def test_system_prompt_exists(self):
        """Test that system prompt is defined."""
        prompt = get_system_prompt(discovery_mode=False)
        assert prompt is not None
        assert len(prompt) > 0
    
    def test_system_prompt_content(self):
        """Test system prompt contains key instructions."""
        prompt = get_system_prompt(discovery_mode=False)
        assert 'GCM' in prompt or 'Guardium' in prompt or 'cryptography' in prompt.lower()


    @patch('gcm_agent.agent.gcm_agent.ChatWatsonx')
    def test_initialize_llm_passes_verify_ssl(self, mock_chat_watsonx):
        """Test WatsonX SSL verification is passed to ChatWatsonx."""
        mock_mcp_client = AsyncMock()
        mock_tool_loader = AsyncMock()
        
        watsonx_config = WatsonXConfig(
            project_id='test_project_id',
            model='ibm/granite-13b-chat-v2',
            verify_ssl=False,
        )
        agent_config = AgentConfig(
            discovery_mode=False,
            max_iterations=10
        )
        llm_config = LLMProviderConfig(
            provider='watsonx',
            watsonx_config=watsonx_config,
            watsonx_api_key='test_api_key'
        )
        
        agent = GCMAgent(
            mcp_client=mock_mcp_client,
            tool_loader=mock_tool_loader,
            agent_config=agent_config,
            llm_config=llm_config
        )
        
        agent._initialize_llm()
        
        mock_chat_watsonx.assert_called_once()
        assert mock_chat_watsonx.call_args.kwargs["verify"] is False


# Made with Bob
