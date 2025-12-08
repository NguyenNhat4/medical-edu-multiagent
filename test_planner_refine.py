import sys
from unittest.mock import MagicMock

# Mock google.genai BEFORE importing nodes
mock_genai = MagicMock()
sys.modules["google"] = MagicMock()
sys.modules["google.genai"] = mock_genai

from nodes import PlannerNode
import unittest
from unittest.mock import patch

class TestPlannerNode(unittest.TestCase):
    @patch('nodes.call_llm')
    def test_refinement_execution(self, mock_call_llm):
        # Mock LLM response for refinement
        mock_call_llm.return_value = """
```yaml
blueprint:
  - title: "Refined Slide 1"
    description: "Refined Content"
```
"""
        node = PlannerNode()

        # Test Data
        shared = {
            "requirements": {"topic": "Flu", "audience": "Students", "objectives": "Learn"},
            "blueprint": [{"title": "Old Slide", "description": "Old Content"}],
            "planner_feedback": "Make it better"
        }

        # 1. Test Prep
        prep_res = node.prep(shared)

        # Check prep result
        self.assertIsInstance(prep_res, dict)
        if "feedback" in prep_res:
             print("Prep returned feedback (Success)")
        else:
             print("Prep returned old structure (Failure expected)")

        # 2. Test Exec
        # If prep returned old structure, we can't test exec with new logic unless we fake prep_res
        if "feedback" not in prep_res:
            # Fake it for testing exec logic independently if we were just testing exec
            # But we want to test integration of prep -> exec
            # So if prep fails, we expect failure.
            pass

        exec_res = node.exec(prep_res)

        # Verify LLM was called with feedback in prompt
        args, _ = mock_call_llm.call_args
        prompt = args[0]
        self.assertIn("Make it better", prompt, "Prompt did not contain feedback")
        self.assertIn("Old Slide", prompt, "Prompt did not contain old blueprint")

        # Verify output
        self.assertIn("blueprint", exec_res)
        self.assertEqual(exec_res['blueprint'][0]['title'], "Refined Slide 1")

if __name__ == '__main__':
    unittest.main()
