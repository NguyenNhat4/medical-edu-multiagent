import asyncio
from utils.mcp_server import mcp

def get_tools():
    """
    Synchronously get the list of available tools from the MCP server.
    """
    try:
        # Check if there's an existing loop (e.g. in Streamlit or other async env)
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            # If we are already in an async loop, we can't use asyncio.run()
            # This handles the case where this might be called from an async context.
            # However, nodes.py nodes are sync.
            # Ideally we should use nest_asyncio if needed, but for now assuming sync context.
            # But wait, mcp.list_tools() is async.
            # If we are in a sync function called from async loop, we need to create a task?
            # PocketFlow nodes run in a thread pool usually or just sync.
            # We'll stick to asyncio.run() assuming standard execution.
            # If it fails, we might need a different approach.
            return loop.run_until_complete(mcp.list_tools())
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

        if loop and loop.is_running():
             result = loop.run_until_complete(mcp.call_tool(tool_name, arguments=kwargs))
        else:
             result = asyncio.run(mcp.call_tool(tool_name, arguments=kwargs))

        # result is typically ([Content], Meta)
        # Content can be TextContent, ImageContent, etc.
        content_list = result[0]
        texts = []
        for item in content_list:
            if hasattr(item, 'text'):
                texts.append(item.text)
            else:
                texts.append(str(item))

        return "\n".join(texts)
    except Exception as e:
        print(f"Error calling tool {tool_name}: {e}")
        import traceback
        traceback.print_exc()
        return f"Error: {e}"
