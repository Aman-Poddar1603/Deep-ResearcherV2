import asyncio
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


async def main():
    async with streamablehttp_client("http://localhost:8001/mcp") as (read, write, *_):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()

            print("\nAvailable tools:\n")

            for item in tools:
                tool = item[0] if isinstance(item, tuple) else item
                print(f"- {tool.title}: {tool}")


asyncio.run(main())