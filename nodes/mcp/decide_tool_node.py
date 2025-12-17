import logging
from pocketflow import Node
from utils.call_llm import call_llm
from utils.yaml_utils import parse_yaml_robustly


class DecideToolNode(Node):
    """
    Node for deciding which MCP tool to use based on user question.

    Uses LLM to:
    1. Analyze the user's question
    2. Select appropriate tool
    3. Extract parameters from the question
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.logger = logging.getLogger(__name__)

    def prep(self, shared):
        """
        Prepare prompt for LLM decision-making.

        Args:
            shared: Shared data store

        Returns:
            Formatted prompt string
        """
        tool_info = shared.get("tool_info", "No tools available")
        question = shared.get("question", "")

        prompt = f"""
### CONTEXT
You are an assistant that can use tools via Model Context Protocol (MCP).

### ACTION SPACE
{tool_info}

### TASK
Answer this question: "{question}"

## NEXT ACTION
Analyze the question, extract any numbers or parameters, and decide which tool to use.
Return your response in this format:

```yaml
thinking: |
    <your step-by-step reasoning about what the question is asking and what numbers to extract>
tool: <name of the tool to use>
reason: <why you chose this tool>
parameters:
    <parameter_name>: <parameter_value>
    <parameter_name>: <parameter_value>
```
IMPORTANT:
1. Extract numbers from the question properly
2. Use proper indentation (4 spaces) for multi-line fields
3. Use the | character for multi-line text fields
"""
        return prompt

    def exec(self, prompt):
        """
        Call LLM to decide which tool to use.

        Args:
            prompt: Formatted prompt

        Returns:
            LLM response with decision
        """
        self.logger.info("Analyzing question and deciding which tool to use...")
        response = call_llm(prompt)
        return response

    def post(self, shared, prep_res, exec_res):
        """
        Extract decision from YAML and save to shared context.

        Args:
            shared: Shared data store
            prep_res: Prepared prompt
            exec_res: LLM response

        Returns:
            Action string
        """
        try:
            decision = parse_yaml_robustly(exec_res)

            if not decision:
                raise ValueError("Failed to parse YAML decision")

            shared["tool_name"] = decision["tool"]
            shared["parameters"] = decision["parameters"]
            shared["thinking"] = decision.get("thinking", "")

            self.logger.info(f"Selected tool: {decision['tool']}")
            self.logger.info(f"Extracted parameters: {decision['parameters']}")

            return "execute"
        except Exception as e:
            self.logger.error(f"Error parsing LLM response: {e}")
            self.logger.error(f"Raw response: {exec_res}")
            return None
