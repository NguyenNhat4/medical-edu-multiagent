from nodes import InterviewerNode, PlannerNode
import os

# Mock shared state
shared = {
    "chat_history": [
        {"role": "user", "content": "Tôi muốn soạn bài về Tăng huyết áp."}
    ],
    "requirements": {},
    "blueprint": [],
    "research_data": {},
    "slides_data": {}
}

def test_interviewer():
    print("Testing InterviewerNode...")
    node = InterviewerNode()
    node.run(shared)
    print("Result:", shared.get("interview_result"))

def test_planner():
    print("Testing PlannerNode...")
    # Mock requirements for planner
    shared["requirements"] = {
        "topic": "Tăng huyết áp",
        "audience": "Sinh viên Y4",
        "objectives": "Chẩn đoán và điều trị theo JNC 8"
    }
    node = PlannerNode()
    node.run(shared)
    print("Blueprint:", shared.get("blueprint"))

if __name__ == "__main__":
    if not os.environ.get("OPENAI_API_KEY"):
        print("Warning: OPENAI_API_KEY not set. Test might fail or use mock if implemented.")

    # We can't really test LLM calls without a key/cost.
    # But we can check for syntax errors.
    print("Syntax check passed.")
