from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.prebuilt import create_react_agent

from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import os
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
model = ChatOpenAI(model="gpt-4o-mini")

server_params = StdioServerParameters(
    command="python",
    # Make sure to update to the full absolute path to your math_server.py file
    args=["math_server.py"],
)

import asyncio

async def main():
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize the connection
            await session.initialize()

            # Get tools
            tools = await load_mcp_tools(session)

            # Create and run the agent
            agent = create_react_agent(model, tools)
            agent_response = await agent.ainvoke({"messages": "what's (3 + 5) x 12?"})
            for m in agent_response["messages"]:
                m.pretty_print()

# Run the async function
if __name__ == "__main__":
    asyncio.run(main())