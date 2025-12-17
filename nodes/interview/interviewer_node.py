import logging
import yaml
from pocketflow import Node
from utils.call_llm import call_llm
from utils.yaml_utils import parse_yaml_robustly


class InterviewerNode(Node):
    """
    Node for interviewing users to gather requirements for educational content.

    Collects three key pieces of information:
    1. Topic - What subject to cover
    2. Audience - Who the content is for
    3. Objectives - What the content should achieve
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.logger = logging.getLogger(__name__)

    def prep(self, shared):
        """
        Read chat history and current requirements from shared store.

        Args:
            shared: Shared data store

        Returns:
            Tuple of (chat_history, requirements)
        """
        return shared.get("chat_history", []), shared.get("requirements", {})

    def exec(self, inputs):
        """
        Use LLM to analyze conversation and determine next action.

        Args:
            inputs: Tuple of (history, requirements)

        Returns:
            Dict with status, message, and requirements
        """
        history, reqs = inputs

        history_text = ""
        for msg in history:
            role = "User" if msg['role'] == "user" else "Agent"
            history_text += f"{role}: {msg['content']}\n"

        # Format current requirements as YAML for context
        reqs_text = yaml.dump(reqs, default_flow_style=False, allow_unicode=True) if reqs else "Chưa có thông tin."

        prompt = f"""
Bạn là Trợ lý Y khoa (Medical Agent).
Nhiệm vụ: Thu thập thông tin từ người dùng để xây dựng bài giảng.
Cần 3 thông tin quan trọng:
1. Chủ đề (Topic)
2. Đối tượng (Audience)
3. Mục tiêu (Objectives)

Trạng thái hiện tại (Thông tin đã biết):
{reqs_text}

Lịch sử hội thoại:
{history_text}

HÃY SUY NGHĨ:
- Nếu thiếu thông tin nào -> Hỏi thông tin đó.
- Nếu người dùng thay đổi ý định -> Cập nhật thông tin mới.
- Nếu đã đủ 3 thông tin -> Xác nhận (done).

OUTPUT FORMAT (YAML):
Vui lòng trả về YAML trong block code. Luôn luôn quote (ngoặc kép) các giá trị string để tránh lỗi parse.

```yaml
status: "ask"  # hoặc "done"
message: "Câu hỏi tiếp theo hoặc xác nhận..."
requirements:
  topic: "..."      # Giữ nguyên hoặc cập nhật
  audience: "..."   # Giữ nguyên hoặc cập nhật
  objectives: "..." # Giữ nguyên hoặc cập nhật
```
"""
        try:
            response = call_llm(prompt)
            result = parse_yaml_robustly(response)
            if not result:
                raise ValueError("Failed to parse YAML")
            return result
        except Exception as e:
            self.logger.error(f"Error parsing YAML: {e}")
            self.logger.error(f"Raw Response: {response}")
            return {"status": "ask", "message": "Có lỗi xử lý, vui lòng nhắc lại."}

    def post(self, shared, prep_res, exec_res):
        """
        Store interview results and determine next action.

        Args:
            shared: Shared data store
            prep_res: Prepared inputs
            exec_res: Execution results

        Returns:
            Action string ("ask" or "done")
        """
        if not isinstance(exec_res, dict):
            exec_res = {"status": "ask", "message": "Lỗi định dạng phản hồi."}

        shared["interview_result"] = exec_res

        if exec_res.get("status") == "done":
            shared["requirements"] = exec_res.get("requirements")
            self.logger.info(f"Requirements collected: {shared['requirements']}")
            return "done"

        return "ask"


def main():
    """
    Test function for InterviewerNode.
    """
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("\n" + "="*60)
    print("Testing InterviewerNode")
    print("="*60 + "\n")

    # Test scenario 1: Empty requirements
    print("Test 1: Starting fresh interview")
    shared = {
        "chat_history": [
            {"role": "user", "content": "I want to create a lesson about diabetes"}
        ],
        "requirements": {}
    }

    interviewer = InterviewerNode()
    action = interviewer.run(shared)

    print(f"Action: {action}")
    print(f"Message: {shared['interview_result']['message']}")
    print(f"Requirements: {shared.get('requirements', {})}")

    # Test scenario 2: Partial requirements
    print("\n" + "="*60)
    print("Test 2: Continuing interview with partial requirements")
    print("="*60 + "\n")

    shared = {
        "chat_history": [
            {"role": "user", "content": "I want to create a lesson about diabetes"},
            {"role": "assistant", "content": "Who is your target audience?"},
            {"role": "user", "content": "Medical students in their 3rd year"}
        ],
        "requirements": {
            "topic": "Diabetes Management",
            "audience": "Medical students (3rd year)"
        }
    }

    action = interviewer.run(shared)
    print(f"Action: {action}")
    print(f"Message: {shared['interview_result']['message']}")
    print(f"Requirements: {shared.get('requirements', {})}")


if __name__ == "__main__":
    main()
