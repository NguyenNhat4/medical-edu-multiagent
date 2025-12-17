import logging
from pocketflow import Node
from utils.tool_registry import call_tool


class ExecuteToolNode(Node):
    """
    Node for executing the chosen MCP tool.

    Takes the selected tool name and parameters,
    calls the tool, and returns the result.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.logger = logging.getLogger(__name__)

    def prep(self, shared):
        """
        Prepare tool execution parameters.

        Args:
            shared: Shared data store

        Returns:
            Tuple of (tool_name, parameters)
        """
        tool_name = shared.get("tool_name")
        parameters = shared.get("parameters")

        self.logger.info(f"Preparing to execute tool: {tool_name}")
        self.logger.info(f"Parameters: {parameters}")

        return tool_name, parameters

    def exec(self, inputs):
        """
        Execute the chosen tool.

        Args:
            inputs: Tuple of (tool_name, parameters)

        Returns:
            Tool execution result
        """
        tool_name, parameters = inputs

        self.logger.info(f"Executing tool '{tool_name}' with parameters: {parameters}")
        result = call_tool(tool_name, parameters)

        self.logger.info(f"Tool execution completed")
        return result

    def post(self, shared, prep_res, exec_res):
        """
        Store tool result and log output.

        Args:
            shared: Shared data store
            prep_res: Prepared inputs
            exec_res: Tool execution result

        Returns:
            Action string
        """
        shared["tool_result"] = exec_res

        self.logger.info(f"\nTool Result: {exec_res}")
        print(f"\n✅ Final Answer: {exec_res}")

        return "done"
