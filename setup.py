"""Setup script for packaging and installing the GCM LangChain Agent."""

from setuptools import find_packages, setup

setup(
    name="gcm-agent",
    version="0.1.0",
    description="LangChain-based agent for IBM Guardium Cryptography Manager MCP integration.",
    packages=find_packages(include=["gcm_agent", "gcm_agent.*"]),
    include_package_data=True,
    install_requires=[
        "langchain>=0.1.0",
        "langchain-mcp-adapters>=0.1.0",
        "langgraph>=0.0.40",
        "langchain-ibm>=0.1.0",
        "httpx>=0.25.0",
        "keyring>=24.0.0",
        "gradio>=4.0.0",
        "pydantic>=2.0.0",
        "python-dotenv>=1.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
        ]
    },
)

# Made with Bob
