Using dynamic tool with IBM Guardium Cryptography Manager MCP Server 

Last Updated: 2026-05-27 

Edit online 

2.0.1.1 and later The IBM® Guardium® Cryptography Manager MCP Server redefines how you engage with backend 

systems by transforming APIs into intelligent, discoverable tools accessible directly through AI assistants. Instead of requiring complex integrations or specialized technical expertise, you can simply describe your goals, and the server automatically identifies and performs the necessary actions. This approach makes backend capabilities more intuitive, scalable, and seamlessly aligned with real-world business workflows. By leveraging discovery tools, the Guardium Cryptography Manager MCP Server intelligently manages performance, dynamically discovering and applying the most relevant capabilities based on user intent. 

**A simpler way to access system capabilities** 

Guardium Cryptography Manager MCP removes the complexity of working with the individual APIs, making backend operations instantly available as easy‑to‑use tools. Powered by `openapispec`, the platform allows you to: – Retrieve essential information such as policies, assets, audit logs, certificates, and violations. – Perform key actions like creating, updating, or listing resources. 

– Interact with systems using natural language instead of technical API calls. 

– Run the following command for OpenAPI backend configuration. 

`version: 1`   
`backends:`   
`- name: <backend identifier>`   
`prefix: <prefix added to all generated MCP tools via openapispec>`   
`type: <source of OpenAPI spec (url or file)>`   
`location: <URL or file path of OpenAPI spec>`   
`server: <target backend server URL>` 

– Update the `charts/aim-mcp-server/values.yaml` file to apply changes to `OpenAPI` backend configuration. 

By eliminating the need for deep technical expertise or manual integrations, Guardium Cryptography Manager MCP significantly reduces the effort required to get started. You can focus on driving outcomes and business value, while the system seamlessly handles the performance. 

**Unlocking possibilities without prior knowledge** 

In complex systems, one of the greatest hurdles is simply knowing what is available. Guardium Cryptography Manager MCP eliminates this challenge by making every tool visible and easy to explore. You can, – Search capabilities using straightforward keywords 

– Browse tools organized by functionality 

– Preview details of each tool before using it

Discovery is now no longer limited to what you already know. Instead, you can dynamically explore, learn, and leverage new capabilities as you work, turning the unknown into opportunity.   
**From individual tasks to seamless workflows** 

Guardium Cryptography Manager MCP goes beyond executing single operations, it empowers users to orchestrate entire processes effortlessly. 

– Combine multiple steps into one streamlined request 

– Automate repetitive workflows to save time and reduce errors 

– Run complex processes without manual coordination 

For example, generating a compliance report no longer requires juggling separate tasks. Data retrieval, analysis, and follow-up actions can all be handled automatically in a single flow, transforming fragmented work into smooth, end to-end execution. 

**Intelligent problem solving with discovery tools** 

For advanced scenarios, discovery tools empower the system to determine the best way to solve a problem without requiring users to manage the details themselves. 

Instead of manually: 

– Identifying the right tools 

– Calling them in sequence 

– Handling intermediate results 

iscovery tools deliver: 

– Automatic discovery of relevant tools 

– Smart selection of only what’s needed 

– Execution of complete workflows in a single run 

The result is reduced complexity, greater efficiency, and the ability to tackle sophisticated use cases with minimal effort, turning complex challenges into streamlined solutions. 

Activate discovery tools in your AI assistant by adding a header. 

`headers = {`   
`"Authorization": "Bearer YOUR_JWT_TOKEN",`   
`"x-mcp-enable-discovery": "true" # Enable discovery tools`   
`}` 

Where, the `x-mcp-enable-discovery` header controls whether the client receives: 

– `true`: 4 discovery tools (search, get\_schema, list\_tools, and tags) and execute tool 

– `false` or omitted: All application tools (standard behavior) 

This gives you flexibility to choose the right mode for each use case. 

**Dynamic tool discovery and On-demand tool loading** 

discovery tools changes how AI assistants interact with tools by providing: 

–   
Dynamic tool discovery: Instead of loading all the available tools, the AI assistant receives the following four discovery tools and one execute tool. 

▪ `search`: Find tools by keywords or patterns 

▪ `get_schema`: Get detailed information about specific tools 

▪ `list_tools`: Browse all available tools 

▪ `tags`: Explore tools organized by categories 

▪ `execute`: Run workflows in a sandboxed environment 

– On-demand tool loading: The AI assistant can: 

▪ Search for relevant tools based on the task 

▪ Load only the tools it needs 

▪ Understand tool parameters before using them 

▪ Execute multiple operations efficiently

**Full visibility and control over capabilities** 

All backend APIs are surfaced as tools, giving users complete insight into what the system can do. At the same time, access is carefully managed to maintain security and governance. With Guardium Cryptography Manager MCP:   
– Only relevant tools are shown to each user 

– Sensitive operations can be restricted 

– Access rights can be tailored by role 

**Guardium Cryptography Manager MCP supports fine-grained access control over MCP tools using Role-based access control (RBAC) configuration.** 

`version: 1`   
`backends:`   
`- name: <backend identifier>`   
`prefix: <prefix added to all generated MCP tools via openapispec>`   
`type: <source of OpenAPI spec (url or file)>`   
`location: <URL or file path of OpenAPI spec>`   
`server: <target backend server URL>`   
`rbac:`   
`default_behaviour: enabled # all tools visible by default`   
`tags:`   
`- name: <openapispec tags>`   
`enabled: <we can enable or disable tools under this particular tag by mentioning true/false> - name: <openapispec tags>` 

`enabled: <we can enable or disable tools under this particular tag by mentioning true/false> exclusion: <we can disable/enable a tag but allow/disallow specific tools within it>` 

`- <name of allowed/disallowed tool within this tag>` 

**Built for scale and real-world usage** 

– The system remains efficient and easy to use, even with a large number of tools 

– Only relevant capabilities are surfaced when needed 

– Users are not overwhelmed by underlying system complexity 

– Performance stays consistent across large API ecosystems 

– All AI-generated code runs in a secure, sandboxed environment 

– Resource limits prevent runaway or excessive execution 

– RBAC is enforced on every tool call 

– Existing clients continue to work without any changes 

– Discovery tools is optional and enabled through a header 

– Users can switch between modes on a per-request basis 

– Well-suited for enterprise environments with diverse and evolving capabilities 

**Extending beyond standard capabilities** 

The platform is built for flexibility, enabling organizations to go beyond out-of-the-box functionality and shape it to their unique needs. 

With Guardium Cryptography Manager MCP, users and teams can: 

– Introduce custom tools for specific workflows 

– Combine multiple capabilities into tailored solutions 

– Align the system with their business processes 

This ensures the platform grows alongside customer needs, empowering them to innovate rather than being limited to only dynamically generated tools. 

**Customer impact** 

By adopting Guardium Cryptography Manager MCP, organizations experience a fundamental shift in how work gets done 

– Accelerated task completion with streamlined workflows 

– Reduced reliance on engineering teams for everyday operations 

– Less effort spent learning APIs or managing technical details 

– Expanded automation capabilities across processes 

– Enhanced control over system access and usage

**Parent topic:**   
Building agents for IBM Guardium Cryptography Manager using inbuilt MCP server