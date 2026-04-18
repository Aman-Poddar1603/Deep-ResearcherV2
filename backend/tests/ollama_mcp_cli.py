import asyncio
import ollama

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


MCP_URL = "http://localhost:8001/mcp"
MODEL = "gemma4:e2b"

SYSTEM_PROMPT = """
You are an autonomous research agent that can use external tools.

You MUST decide when to call tools and how to use them correctly.

----------------------------------
HOW TOOL CALLING WORKS
----------------------------------

You follow this loop:

1. Understand the query
2. Decide if a tool is needed
3. Call the correct tool with valid arguments
4. Receive tool result
5. Continue reasoning or call another tool
6. Return final answer

----------------------------------
TOOL USAGE EXAMPLES (VERY IMPORTANT)
----------------------------------

Example 1: Web research

User: latest AI news

→ You MUST call:
web_search(query="latest AI news")

Then use the returned results to answer.


----------------------------------

Example 2: Get URLs only

User: give me links about LLM agents

→ Call:
search_urls_tool(query="LLM agents")

DO NOT scrape yet.


----------------------------------

Example 3: Read content from URLs

User: summarize these pages: [list of URLs]

→ Call:
read_webpages(urls=[...])

Then summarize results.


----------------------------------

Example 4: Single URL

User: summarize https://example.com

→ Call:
scrape_single_url(url="https://example.com")

----------------------------------

Example 5: YouTube

User: videos about black holes

→ Call:
youtube_search(query="black holes")

----------------------------------

Example 6: Images

User: show me images of mars

→ Call:
image_search_tool(queries=[("mars", 5)])
technically,
image_search_tool(queries=[("query", num_results)])

----------------------------------

Example 7: Image analysis

User: analyze these images: [urls]

→ Call:
understand_images_tool(paths=[...])

----------------------------------

Example 8: Documents

User: summarize this pdf

→ Call:
process_docs(paths=[...])

----------------------------------

Example 9: Multi-step reasoning

User: latest AI research papers summary

Step 1:
web_search(query="latest AI research papers")

Step 2:
Extract URLs

Step 3:
read_webpages(urls=[...])

Step 4:
Summarize results

----------------------------------
STRICT RULES
----------------------------------

- NEVER guess when a tool exists
- ALWAYS follow tool input schema exactly
- ALWAYS pass correct argument types
- NEVER call tools with missing fields
- NEVER hallucinate tool results

----------------------------------
WHEN TO NOT USE TOOLS
----------------------------------

- simple math
- general knowledge
- basic reasoning

----------------------------------
IMPORTANT
----------------------------------

You are NOT a chatbot.
You are an agent that THINKS and ACTS using tools.
"""


async def main():
    print("🚀 Streaming MCP + Ollama CLI...\n")

    async with streamablehttp_client(MCP_URL) as (read, write, _):
        async with ClientSession(read, write) as session:

            await session.initialize()

            tools_result = await session.list_tools()
            mcp_tools = tools_result.tools

            print("🔧 Loaded tools:", [t.name for t in mcp_tools])

            # 🔥 MCP → Ollama tool schema
            ollama_tools = []
            for t in mcp_tools:
                ollama_tools.append({
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description or t.title or "",
                        "parameters": t.inputSchema
                    }
                })

            messages = [{
                "role": "system",
                "content": SYSTEM_PROMPT
            }]

            print("\n💬 Ready (type exit)\n")

            while True:
                user = input("You: ")
                if user == "exit":
                    break

                messages.append({"role": "user", "content": user})

                while True:
                    # 🔥 STREAM ENABLED
                    stream = ollama.chat(
                        model=MODEL,
                        messages=messages,
                        tools=ollama_tools,
                        stream=True,
                        think=False
                    )

                    full_content = ""
                    tool_calls = None

                    print("\n🤖 ", end="", flush=True)

                    for chunk in stream:
                        msg = chunk["message"]

                        # 🧠 capture tool calls (they appear once)
                        if msg.get("tool_calls"):
                            tool_calls = msg["tool_calls"]

                        # 🧠 stream text tokens
                        content = msg.get("content", "")
                        if content:
                            print(content, end="", flush=True)
                            full_content += content

                    print()  # newline after stream

                    # 🧠 TOOL EXECUTION
                    if tool_calls:
                        for call in tool_calls:
                            name = call["function"]["name"]
                            args = call["function"]["arguments"]

                            print(f"\n⚙️ Calling: {name}({args})")

                            try:
                                result = await session.call_tool(
                                    name,
                                    arguments=args
                                )
                            except Exception as e:
                                result = f"ERROR: {str(e)}"

                            messages.append({
                                "role": "tool",
                                "name": name,
                                "content": str(result)
                            })

                    else:
                        messages.append({
                            "role": "assistant",
                            "content": full_content
                        })
                        break


if __name__ == "__main__":
    asyncio.run(main())