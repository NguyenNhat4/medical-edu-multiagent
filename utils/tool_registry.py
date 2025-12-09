import asyncio
from utils.mcp_server import mcp
import concurrent.futures

def _run_in_thread(coro):
    """Run a coroutine in a separate thread to avoid event loop conflicts."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(asyncio.run, coro)
        return future.result()

def get_tools():
    """
    Synchronously get the list of available tools from the MCP server.
    """
    try:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            # If loop is running, we cannot use asyncio.run() or loop.run_until_complete()
            # So we run in a separate thread.
            return _run_in_thread(mcp.list_tools())
        else:
            return asyncio.run(mcp.list_tools())
    except Exception as e:
        print(f"Error getting tools: {e}")
        return []

def call_tool(tool_name, kwargs):
    """
    Synchronously call a tool from the MCP server.
    """
    try:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        coro = mcp.call_tool(tool_name, arguments=kwargs)

        if loop and loop.is_running():
             result = _run_in_thread(coro)
        else:
             result = asyncio.run(coro)

        # result is typically ([Content], Meta) or CallToolResult
        # Based on FastMCP, it returns a CallToolResult which is iterable or has content.
        # Our test showed it prints as a tuple: ([TextContent...], Meta)

        # Safe extraction
        content_list = None
        if hasattr(result, 'content'):
            content_list = result.content
        elif isinstance(result, tuple) or isinstance(result, list):
            content_list = result[0]

        texts = []
        if content_list:
            for item in content_list:
                if hasattr(item, 'text'):
                    texts.append(item.text)
                else:
                    texts.append(str(item))
            return "\n".join(texts)

        return str(result)

    except Exception as e:
        print(f"Error calling tool {tool_name}: {e}")
        import traceback
        traceback.print_exc()
        return f"Error: {e}"
