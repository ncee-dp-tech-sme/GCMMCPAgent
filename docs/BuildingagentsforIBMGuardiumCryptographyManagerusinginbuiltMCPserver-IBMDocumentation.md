Building agents for IBM Guardium Cryptography Manager Last Updated: 2026-05-26 

Edit online 

2.0.1.0 and later Managing enterprise cryptographic assets and enforcing security policies requires reliable automation. IBM® Guardium® Cry Before you begin 

– Access to a running Guardium Cryptography Manager deployment 

– IBM WatsonX API key and Project ID 

– Python 3.11+ 

– Install dependencies from the requirements.txt file. 

pip install \-r requirements.txt 

▪ The requirements.txt file contains the following details. 

\# requirements.txt   
langchain   
langgraph   
langchain-ibm   
langchain-core   
langchain-mcp-adapters   
httpx   
pydantic-settings   
python-dotenv   
langsmith==0.7.10 

**Key technologies:** 

– Agent framework: LangGraph StateGraph wrapping langchain.agents.create\_agent 

– LLM backend: IBM WatsonX (langchain-ibm) 

– MCP transport: langchain-mcp-adapters (streamable-http) 

– MCP server: IBM Guardium Cryptography Manager MCP Server (remote, Bearer JWT auth) 

– Language: Python 3.11 

![][image1]**Note:** You can use any model and provider through the appropriate LangChain integration or import. For more information, see LangC About this task 

Complete the following steps to integrate Guardium Cryptography Manager MCP server to your AI agent. 

Procedure 

1\. **Build a Basic LangGraph Agent** 

Run the following command to build an LLM wrapped in a LangGraph StateGraph 

import asyncio   
from langchain\_ibm import ChatWatsonx   
from langchain.agents import create\_agent   
from langgraph.graph import StateGraph, MessagesState, START, END   
from langchain\_core.messages import HumanMessage 

SYSTEM\_PROMPT \= "You are a helpful assistant." 

def build\_agent(llm):   
react\_agent \= create\_agent(model=llm, tools=\[\], system\_prompt=SYSTEM\_PROMPT)  
async def agent\_node(state: MessagesState) \-\> dict:   
result \= await react\_agent.ainvoke({"messages": state\["messages"\]})   
return {"messages": result\["messages"\]} 

graph \= StateGraph(MessagesState)   
graph.add\_node("agent", agent\_node)   
graph.add\_edge(START, "agent")   
graph.add\_edge("agent", END)   
return graph.compile() 

async def main():   
llm \= ChatWatsonx(model\_id="ibm/granite-3-8b-instruct", ...)   
agent \= build\_agent(llm)   
history \= \[\]   
while True:   
question \= input("You: ").strip()   
history.append(HumanMessage(content=question))   
result \= await agent.ainvoke({"messages": history})   
history \= result\["messages"\]   
ai\_msgs \= \[m for m in history if getattr(m, "type", None) \== "ai"   
and not getattr(m, "tool\_calls", None)\]   
print(f"Agent: {ai\_msgs\[-1\].content}\\n") 

asyncio.run(main()) . 

2\. **Connect the Guardium Cryptography Manager MCP Server** 

Run the following command to configure a MultiServerMCPClient from langchain-mcp-adapters and load those tools into the ag 

\# gcm\_mcp.py   
import httpx   
from langchain\_mcp\_adapters.client import MultiServerMCPClient 

GCM\_URL \= "https://\<GCM\_HOSTNAME\>:\<API\_PORT\>/ibm/mcp/mcp" 

def \_client\_factory(\*\*kwargs) \-\> httpx.AsyncClient:   
kwargs.pop("verify", None)   
return httpx.AsyncClient(verify=True, \*\*kwargs) 

def \_build\_config() \-\> dict:   
return {   
"gcm": {   
"transport": "streamable\_http",   
"url": GCM\_URL, 

}   
}   
"httpx\_client\_factory": \_client\_factory, 

async def get\_tools() \-\> list:   
return await MultiServerMCPClient(\_build\_config()).get\_tools() 

![][image2]**Note:** SSL verification is enabled by default. When you use a trusted certificate from your certificate authority, verification works w 

3\. **Add authentication** 

There is a two-step authorization flow: 

a. Obtain an OAuth2 access token from Keycloak. 

b. Authorize with Guardium Cryptography Manager's user management endpoint. 

Run the following command to set your credentials in .env or export them as environment variables. 

GCM\_URL=https://\<gcm-hostname\>:\<api-port\>/ibm/mcp/mcp   
GCM\_HOSTNAME=\<gcm-hostname\>   
USERNAME=\<gcm-username\>   
PASSWORD=\<gcm-password\>   
CLIENT\_ID=\<keycloak-client-id\>   
CLIENT\_SECRET=\<keycloak-client-secret\>   
LLM\_WATSONX\_API\_KEY=\<your-api-key\>   
LLM\_WATSONX\_PROJECT\_ID=\<your-project-id\>   
WATSONX\_MODEL=\<watsonx-model-id\> \# e.g. ibm/granite-3-8b-instruct 

\# auth/gcm\_token\_manager.py   
import base64   
import httpx   
import os   
from typing import Optional 

def get\_gcm\_token(verbose: bool \= True) \-\> Optional\[str\]:   
return \_fetch\_token(verbose=verbose) 

def \_fetch\_token(verbose: bool \= True) \-\> Optional\[str\]:   
gcm\_hostname \= os.getenv("GCM\_HOSTNAME")   
keycloak\_port \= os.getenv("KEYCLOAK\_PORT", "443")   
api\_port \= os.getenv("API\_PORT", "443")   
realm \= os.getenv("REALM", "master")   
username \= os.getenv("USERNAME")  
password \= os.getenv("PASSWORD")   
client\_id \= os.getenv("CLIENT\_ID")   
client\_secret \= os.getenv("CLIENT\_SECRET") 

keycloak\_url \= f"https://{gcm\_hostname}:{keycloak\_port}"   
gcm\_base\_url \= f"https://{gcm\_hostname}:{api\_port}"   
token\_endpoint \= f"{keycloak\_url}/realms/{realm}/protocol/openid-connect/token" 

\# 1\) Request OAuth token from Keycloak   
basic \= base64.b64encode(f"{client\_id}:{client\_secret}".encode()).decode() with httpx.Client(verify=True, timeout=30.0) as client:   
token\_resp \= client.post(   
token\_endpoint,   
data={   
"grant\_type": "password",   
"username": username,   
"password": password, 

},   
"scope": "openid", 

headers={"Authorization": f"Basic {basic}"}, )   
token\_resp.raise\_for\_status()   
access\_token \= token\_resp.json().get("access\_token") if not access\_token:   
return None 

\# 2\) Authorize against GCM user management endpoint auth\_resp \= client.post(   
f"{gcm\_base\_url}/ibm/usermanagement/api/v2/authorization", json={"tenantId": ""},   
headers={"Authorization": f"Bearer {access\_token}"}, )   
auth\_resp.raise\_for\_status() 

return access\_token 

4\. **Wire the authorization manager into the agent's MCP client factory** 

Integrate the following code to wire the authorization manager into the agent's MCP connection or connector so each request automatica 

\# mcp\_servers/gcm\_mcp.py   
import httpx   
from auth.gcm\_token\_manager import get\_gcm\_token 

def \_client\_factory(\*\*kwargs) \-\> httpx.AsyncClient:   
token \= get\_gcm\_token(verbose=False) or ""   
headers \= dict(kwargs.pop("headers", None) or {})   
headers\["Authorization"\] \= f"Bearer {token}"   
return httpx.AsyncClient(verify=True, headers=headers, \*\*kwargs) 

def \_build\_config() \-\> dict:   
if not get\_gcm\_token(verbose=False):   
raise ValueError("Failed to obtain a GCM JWT token \- check credentials in .env.")   
return {   
"gcm": {   
"transport": "streamable\_http",   
"url": GCM\_URL, 

}   
}   
"httpx\_client\_factory": \_client\_factory, 

![][image3]**Note:** Once token retrieval and Guardium Cryptography Manager authorization are working, enable token caching to reduce repea 

5\. **Verify whether MCP tools are loaded successfully** 

At this point, the agent has access to all the 26 tools exposed by the Guardium Cryptography Manager MCP server. 

\[debug\] GCM MCP loaded 26 tools   
\[debug\] tools: search\_policies, fetch\_policy\_by\_id, create\_policy, get\_violation\_by\_id, create\_violation\_ticket, fetch\_policy\_v 

6\. **Consolidate the LLM, tools, graph, and system prompt** 

Run the following command. 

\# agent/qa\_agent.py   
SYSTEM\_PROMPT \= (   
"You are a helpful assistant with access to IBM Guardium Cryptography Manager (GCM) tools. "   
"Always call the appropriate tool to answer the user's question directly.\\n\\n"   
"After a tool returns data, present the ACTUAL VALUES \- real hostnames, IPs, cert names, etc. "   
"Do NOT describe the fields or paraphrase the schema." ) 

async def load\_tools() \-\> list:   
gcm\_tools \= await get\_gcm\_tools()   
print(f" \[ok\] GCM MCP \- {len(gcm\_tools)} tool(s) loaded")   
return gcm\_tools 

\# build\_agent() graph structure is the same as Step 1; it now receives real MCP tools.  
7\. **Wire the authorization manager, MCP client, LLM, and LangGraph agent together in main.py** 

Run the following command. 

\# main.py   
async def main():   
tools \= await load\_tools()   
llm \= build\_llm()   
agent \= build\_agent(llm, tools) 

history \= \[\]   
while True:   
question \= input("You: ").strip()   
... 

8\. **Run the main.py command.** 

python main.py 

Sample output: 

You: How many IT assets are there in total?   
Agent: There are 42 IT assets in total. 

You: List all certificates expiring soon.   
Agent: Found 3 certificates expiring within 30 days:   
1\. web-lb-01.example.com \- expires 2026-03-28 (Self-signed)   
2\. api-gw-prod \- expires 2026-04-02 (CA-signed)   
3\. db-cluster-tls \- expires 2026-04-10 (CA-signed) 

You: Which of those has the most policy violations?   
Agent: web-lb-01.example.com has the highest violation count with 7 active violations. 

Results 

The agent now has real‑time access to Guardium Cryptography Manager data and can handle multi‑turn follow‑up queries. For persistence a –   
**Using dynamic tool with IBM Guardium Cryptography Manager MCP Server** 

2.0.1.1 and later The IBM Guardium Cryptography Manager MCP Server redefines how you engage with backend systems by transforming A 

Expanding Agent Capabilities Using External MCP Servers As you develop more scenarios, your agent needs additional tools. With this example, you can integrate Slack’s official MCP server alongside Before you begin 

– Add the following to your .env file. 

SLACK\_BOT\_TOKEN=xoxb-your-bot-token   
SLACK\_TEAM\_ID=your-slack-team-id 

– Implementation steps: 

\# mcp\_servers/slack\_mcp.py   
import os   
from langchain\_mcp\_adapters.client import MultiServerMCPClient 

SLACK\_BOT\_TOKEN \= os.getenv("SLACK\_BOT\_TOKEN")   
SLACK\_TEAM\_ID \= os.getenv("SLACK\_TEAM\_ID") 

def \_build\_config() \-\> dict:   
"""Build configuration for the Slack MCP server."""   
if not SLACK\_BOT\_TOKEN:   
raise ValueError("SLACK\_BOT\_TOKEN is required — set it in .env")   
if not SLACK\_TEAM\_ID:   
raise ValueError("SLACK\_TEAM\_ID is required — set it in .env") 

config: dict \= {   
"slack": {   
"transport": "stdio",   
"command": "npx",   
"args": \[   
"-y", 

\],   
"@modelcontextprotocol/server-slack" 

"env": {   
"SLACK\_BOT\_TOKEN": SLACK\_BOT\_TOKEN, 

} 

}  
"SLACK\_TEAM\_ID": SLACK\_TEAM\_ID,   
}   
return config 

def get\_mcp\_client() \-\> MultiServerMCPClient:   
"""Return a MultiServerMCPClient wired to the Slack MCP server."""   
return MultiServerMCPClient(\_build\_config()) 

async def get\_tools() \-\> list:   
"""Convenience helper — returns ready-to-use LangChain tool objects."""   
return await get\_mcp\_client().get\_tools() 

About this task 

The official Slack MCP server provides tools for interacting with Slack workspaces. It enables agents to: 

– List channels and users 

– Post messages to channels 

– Reply to threads 

– Add reactions to messages 

The following table highlights the differences between the Slack MCP Server and the Guardium Cryptography Manager MCP server. Table 1\. TDE key management supported databases in Guardium Cryptography Manager 

**Feature Slack MCP server Deployment** Runs locally as a N 

**Authentication** Slack Bot Token **Primary Use Case** Interacting with Sla **Capabilities** List channels/users **Integration Style** Provides workspac 

Complete the following steps to integrate multiple MCP servers. 

Procedure 

1\. Update agent/qa\_agent.py to load tools from both the MCP servers. 

\# agent/qa\_agent.py   
from mcp\_servers.gcm\_mcp import get\_tools as get\_gcm\_tools   
from mcp\_servers.slack\_mcp import get\_tools as get\_slack\_tools 

async def load\_tools() \-\> list:   
"""Load tools from all configured MCP servers."""   
gcm\_tools \= await get\_gcm\_tools()   
print(f" \[ok\] GCM MCP \- {len(gcm\_tools)} tool(s) loaded") 

slack\_tools \= await get\_slack\_tools()   
print(f" \[ok\] Slack MCP \- {len(slack\_tools)} tool(s) loaded") 

\# Combine all tools   
all\_tools \= gcm\_tools \+ slack\_tools   
print(f" \[ok\] Total: {len(all\_tools)} tool(s) available") 

return all\_tools 

2\. Update the system prompt to reflect the new capabilities. 

SYSTEM\_PROMPT \= (   
"You are a helpful assistant with access to IBM Guardium Cryptography Manager (GCM) "   
"and Slack integration tools. "   
"Use GCM tools to query cryptographic assets, policies, and violations. "   
"Use Slack tools to notify teams or post updates to channels.\\n\\n"   
"Always call the appropriate tool to answer the user's question directly. "   
"After a tool returns data, present the ACTUAL VALUES \- real hostnames, IPs, cert names, etc. "   
"Do NOT describe the fields or paraphrase the schema." 

)

Sample output: Your agent can now coordinate actions across both systems simultaneously.   
You: Check for policy violations and post a summary to \#security-alerts 

Agent: \[Calling GCM tool: policy\_violations\_dashboard\]   
\[Calling Slack tool: post\_message\] 

Found 12 active policy violations. Summary posted to \#security-alerts: \- 7 violations on web-lb-01.example.com   
\- 3 violations on api-gw-prod   
\- 2 violations on db-cluster-tls 

You: List all certificates expiring in 30 days and notify the team 

Agent: \[Calling GCM tool: fetch\_detailed\_asset\_list\_by\_crypto\_objects\] \[Calling Slack tool: post\_message\] 

Found 3 certificates expiring within 30 days. Team notified in \#security-alerts. 

**Note:** Best practices for multiple MCP servers. 

▪ Load tools from all the servers during initialization to avoid runtime delays. ▪ Use clear naming conventions if tools from different servers have similar names. ▪ Recover connection failures so as not to crash the agent. 

▪ Consider tool execution order when orchestrating multi-system workflows.

[image1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAApkAAAAlCAYAAAAJOPJ1AAAAwUlEQVR4Xu3WwQmCYACG4Q8SPKoQhF2yU2fBFqhrg0j71FbtVOQI/hfheeDd4U2GZ53bZ/p3lyRJklZ3Seo+acalVpIkSSqQyZQkSVLxAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAIBtOz6qjK/T0luSJEla28FkSpIkqXS/yeyuu5znvSRJklSo5gu9ItxBbP5fmAAAAABJRU5ErkJggg==>

[image2]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAokAAAAlCAYAAAAulnOdAAAAvElEQVR4Xu3WMQqCAACG0R9BGiJpkyCwqTZdcq8DdI4G7+Oh6lJGOUhe4T347vAlzbDJ/X2VJEmSvt1el6Q8JLvuV9VKkiRJMYmSJElaBwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAsFQ/ynTjWZIkSZo7mkRJkiT995nEfV/k9KwkSZKkue0EPO96793HF8sAAAAASUVORK5CYII=>

[image3]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAokAAAAlCAYAAAAulnOdAAAAvklEQVR4Xu3WsQnCAABFwY8QLMSQTgRBK+0SC+11AOdIkXnMUGYpMbEIusIdvB1esu+WuQ8XSZIkaez2OiXFNlk3U2UtSZIkxSRKkiTpPwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgLnNo8i5P0qSJElTz51JlCRJ0k+fSayuixzaUpIkSfq2egPTfn/9Xi9p2gAAAABJRU5ErkJggg==>