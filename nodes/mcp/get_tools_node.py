import logging
from pocketflow import Node
from utils.tool_registry import get_tools


class GetToolsNode(Node):
    """
    Node for retrieving available MCP tools.

    Fetches tool definitions from MCP server and formats them
    for use in decision-making and execution.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.logger = logging.getLogger(__name__)

    def prep(self, shared):
        """
        Initialize tool retrieval.

        Args:
            shared: Shared data store

        Returns:
            None
        """
        self.logger.info("Getting available tools...")
        return None

    def exec(self, _):
        """
        Retrieve tools from the MCP server.

        Returns:
            List of tool definitions
        """
        tools = get_tools()
        self.logger.info(f"Retrieved {len(tools)} tools from MCP server")
        return tools

    def post(self, shared, prep_res, exec_res):
        """
        Store tools and format tool information.

        Args:
            shared: Shared data store
            prep_res: Prepared input (None)
            exec_res: List of tools

        Returns:
            Action string
        """
        tools = exec_res
        shared["tools"] = tools

        # Format tool information for later use
        tool_info = []
        for i, tool in enumerate(tools, 1):
            properties = tool.inputSchema.get('properties', {})
            required = tool.inputSchema.get('required', [])

            params = []
            for param_name, param_info in properties.items():
                param_type = param_info.get('type', 'unknown')
                req_status = "(Required)" if param_name in required else "(Optional)"
                params.append(f"    - {param_name} ({param_type}): {req_status}")

            tool_info.append(
                f"[{i}] {tool.name}\n  Description: {tool.description}\n  Parameters:\n" +
                "\n".join(params)
            )

        shared["tool_info"] = "\n".join(tool_info)
        self.logger.info("Tool information formatted and stored")

        return "decide"
