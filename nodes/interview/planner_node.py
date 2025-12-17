import logging
import yaml
from pocketflow import Node
from utils.call_llm import call_llm
from utils.yaml_utils import parse_yaml_robustly


class PlannerNode(Node):
    """
    Node for creating and refining content blueprints based on user requirements.

    Creates a structured outline (blueprint) for educational content with:
    - Title for each section
    - Description of what that section should cover
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.logger = logging.getLogger(__name__)

    def prep(self, shared):
        """
        Read requirements, current blueprint, and any feedback from shared store.

        Args:
            shared: Shared data store

        Returns:
            Dict with reqs, current_blueprint, and feedback
        """
        return {
            "reqs": shared.get("requirements", {}),
            "current_blueprint": shared.get("blueprint", []),
            "feedback": shared.get("planner_feedback", "")
        }

    def exec(self, inputs):
        """
        Generate or refine content blueprint using LLM.

        Args:
            inputs: Dict with requirements, current blueprint, and feedback

        Returns:
            Dict with blueprint list
        """
        reqs = inputs.get("reqs", {})
        current_blueprint = inputs.get("current_blueprint", [])
        feedback = inputs.get("feedback", "")

        if not reqs:
            self.logger.warning("No requirements provided for planning")
            return {"blueprint": []}

        # If feedback provided, refine existing blueprint
        if feedback:
            prompt = f"""
Bạn là chuyên gia soạn bài giảng y khoa.
Nhiệm vụ: Cập nhật dàn ý bài giảng dựa trên yêu cầu chỉnh sửa của người dùng.
Bạn có thể thêm, bớt hoặc sửa đổi các slide nếu cần thiết.

Thông tin bài giảng:
Topic: {reqs.get('topic')}
Audience: {reqs.get('audience')}
Objectives: {reqs.get('objectives')}

Dàn ý hiện tại:
{yaml.dump(current_blueprint, allow_unicode=True)}

Yêu cầu chỉnh sửa: "{feedback}"

Output YAML list mới (Cập nhật hoàn chỉnh):
Important: Quote strings.

```yaml
blueprint:
  - title: "..."
    description: "..."
```
"""
        else:
            # Create new blueprint
            prompt = f"""
Lập dàn ý bài giảng (Blueprint) cho:
Topic: {reqs.get('topic')}
Audience: {reqs.get('audience')}
Objectives: {reqs.get('objectives')}

Tạo dàn ý chi tiết với 5-7 phần chính. Mỗi phần cần:
- Title: Tiêu đề rõ ràng, súc tích (Tập trung vào nội dung chuyên môn)
- Description: Mô tả chi tiết nội dung cần trình bày

YÊU CẦU QUAN TRỌNG:
1. KHÔNG tạo các phần Chào hỏi, Giới thiệu chung chung, Lời kết, Cảm ơn (Ví dụ: "Chào mừng", "Giới thiệu bản thân", "Kết luận chung").
2. Tập trung thẳng vào các kiến thức cốt lõi (Core Knowledge).
3. Đảm bảo cấu trúc logic, đi từ cơ bản đến nâng cao.

Output YAML list. Important: Quote strings.
```yaml
blueprint:
  - title: "..."
    description: "..."
  - title: "..."
    description: "..."
```
"""

        try:
            response = call_llm(prompt)
            result = parse_yaml_robustly(response)
            if not result:
                raise ValueError("Failed to parse YAML")

            self.logger.info(f"Generated blueprint with {len(result.get('blueprint', []))} sections")
            return result
        except Exception as e:
            self.logger.error(f"Error parsing YAML: {e}")
            self.logger.error(f"Raw Response: {response}")
            return {"blueprint": []}

    def post(self, shared, prep_res, exec_res):
        """
        Store blueprint in shared store.

        Args:
            shared: Shared data store
            prep_res: Prepared inputs
            exec_res: Execution results with blueprint

        Returns:
            Action string
        """
        if isinstance(exec_res, dict):
            shared["blueprint"] = exec_res.get("blueprint", [])
        else:
            shared["blueprint"] = []

        # Log the blueprint
        if shared["blueprint"]:
            self.logger.info("Blueprint created successfully:")
            for idx, item in enumerate(shared["blueprint"], 1):
                self.logger.info(f"  {idx}. {item.get('title', 'N/A')}")

        return "default"


def main():
    """
    Test function for PlannerNode.
    """
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("\n" + "="*60)
    print("Testing PlannerNode")
    print("="*60 + "\n")

    # Test scenario 1: Create new blueprint
    print("Test 1: Creating new blueprint")
    shared = {
        "requirements": {
            "topic": "Diabetes Management",
            "audience": "Medical students (3rd year)",
            "objectives": "Understand diagnosis, treatment protocols, and patient management"
        }
    }

    planner = PlannerNode()
    action = planner.run(shared)

    print(f"Action: {action}")
    print(f"Blueprint sections: {len(shared.get('blueprint', []))}")
    for idx, section in enumerate(shared.get('blueprint', []), 1):
        print(f"\n{idx}. {section.get('title')}")
        print(f"   Description: {section.get('description')[:100]}...")

    # Test scenario 2: Refine blueprint with feedback
    print("\n" + "="*60)
    print("Test 2: Refining blueprint with feedback")
    print("="*60 + "\n")

    shared["planner_feedback"] = "Add more detail about Type 1 vs Type 2 diabetes differences"

    action = planner.run(shared)
    print(f"Action: {action}")
    print(f"Updated blueprint sections: {len(shared.get('blueprint', []))}")
    for idx, section in enumerate(shared.get('blueprint', []), 1):
        print(f"\n{idx}. {section.get('title')}")


if __name__ == "__main__":
    main()
