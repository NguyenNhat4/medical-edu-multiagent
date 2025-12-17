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

import logging

logger = logging.getLogger(__name__)

async def call_tool_async(tool_name, kwargs):
    """
    Asynchronously call a tool from the MCP server.
    This avoids blocking the event loop when called from async contexts.
    """
    try:
        logger.info(f"Async calling tool: {tool_name} with args keys: {list(kwargs.keys())}")
        result = await mcp.call_tool(tool_name, arguments=kwargs)

        # result is typically ([Content], Meta)
        content_list = result[0]
        texts = []
        for item in content_list:
            if hasattr(item, 'text'):
                texts.append(item.text)
            else:
                texts.append(str(item))

        output = "\n".join(texts)
        logger.info(f"Tool {tool_name} completed successfully.")
        return output
    except Exception as e:
        logger.error(f"Error calling tool {tool_name} asynchronously: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return f"Error: {e}"

def call_tool(tool_name, kwargs):
    """
    Synchronously call a tool from the MCP server.
    WARNING: Use call_tool_async if running inside an async loop.
    """
    try:
        logger.info(f"Sync calling tool: {tool_name}")
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
             logger.warning(f"Detected running event loop for sync tool call: {tool_name}. This often fails.")
             # This will likely raise RuntimeError: This event loop is already running
             result = loop.run_until_complete(mcp.call_tool(tool_name, arguments=kwargs))
        else:
             result = asyncio.run(mcp.call_tool(tool_name, arguments=kwargs))

        # result is typically ([Content], Meta)
        content_list = result[0]
        texts = []
        for item in content_list:
            if hasattr(item, 'text'):
                texts.append(item.text)
            else:
                texts.append(str(item))

        return "\n".join(texts)
    except Exception as e:
        logger.error(f"Error calling tool {tool_name}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return f"Error: {e}"
