from pocketflow import Node
from utils.call_llm import call_llm
import yaml

class InterviewerNode(Node):
    def prep(self, shared):
        return shared.get("chat_history", [])

    def exec(self, history):
        history_text = ""
        for msg in history:
            role = "User" if msg['role'] == "user" else "Agent"
            history_text += f"{role}: {msg['content']}\n"

        prompt = f"""
Bạn là Trợ lý Y khoa (Medical Agent).
Nhiệm vụ: Hỏi để làm rõ yêu cầu về:
1. Chủ đề (Topic)
2. Đối tượng (Audience)
3. Mục tiêu (Objectives)
4. Định dạng tài liệu (Outputs): Slide (PPTX) hay Tài liệu chi tiết (DOCX) hoặc cả hai?

Nếu ĐÃ ĐỦ thông tin: status='done'.
Nếu CHƯA ĐỦ: status='ask', đặt câu hỏi ngắn gọn.

Hội thoại:
{history_text}

Output YAML:
```yaml
status: ask  # or done
message: "..."
requirements:
  topic: "..."
  audience: "..."
  objectives: "..."
  outputs: ["slide", "doc"] # List các định dạng
```
"""
        try:
            response = call_llm(prompt)
            # Basic cleaning
            if "```yaml" in response:
                clean = response.split("```yaml")[1].split("```")[0].strip()
            elif "```" in response:
                 clean = response.split("```")[1].split("```")[0].strip()
            else:
                clean = response.strip()

            return yaml.safe_load(clean)
        except Exception as e:
            print(f"Error parsing YAML: {e}")
            return {"status": "ask", "message": "Có lỗi xử lý, vui lòng nhắc lại."}

    def post(self, shared, prep_res, exec_res):
        if not isinstance(exec_res, dict):
             exec_res = {"status": "ask", "message": "Lỗi định dạng phản hồi."}

        shared["interview_result"] = exec_res
        if exec_res.get("status") == "done":
            shared["requirements"] = exec_res.get("requirements")
        return "default"

class PlannerNode(Node):
    def prep(self, shared):
        reqs = shared.get("requirements", {})
        feedback = shared.get("plan_feedback", None)
        return {"reqs": reqs, "feedback": feedback}

    def exec(self, inputs):
        reqs = inputs.get("reqs", {})
        feedback = inputs.get("feedback")

        if not reqs:
            return {"blueprint": []}

        prompt = f"""
Lập dàn ý bài giảng (Blueprint) cho:
Topic: {reqs.get('topic')}
Audience: {reqs.get('audience')}
Objectives: {reqs.get('objectives')}
Outputs: {reqs.get('outputs')}

"""
        if feedback:
            prompt += f"\nLƯU Ý QUAN TRỌNG: Người dùng yêu cầu sửa đổi dàn ý trước đó như sau: '{feedback}'. Hãy điều chỉnh lại cấu trúc cho phù hợp."

        prompt += """
Output YAML list:
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
            if "```yaml" in response:
                clean = response.split("```yaml")[1].split("```")[0].strip()
            elif "```" in response:
                 clean = response.split("```")[1].split("```")[0].strip()
            else:
                clean = response.strip()
            return yaml.safe_load(clean)
        except Exception as e:
            print(f"Error parsing YAML: {e}")
            return {"blueprint": []}

    def post(self, shared, prep_res, exec_res):
        if isinstance(exec_res, dict):
            shared["blueprint"] = exec_res.get("blueprint", [])
        else:
            shared["blueprint"] = []
        # Clear feedback after processing so it doesn't persist forever if we loop back differently
        # But for 'Regenerate', we might want to keep it until confirmed.
        # Actually, app.py sets it. We can clear it here or let app.py manage it.
        # Let's clear it to be safe.
        if "plan_feedback" in shared:
            del shared["plan_feedback"]
        return "default"

class ResearcherNode(Node):
    def prep(self, shared):
        idx = self.params.get("index")
        if idx is not None and "blueprint" in shared and idx < len(shared["blueprint"]):
            item = shared["blueprint"][idx]
            return item
        return None

    def exec(self, item):
        if not item: return "No item"

        prompt = f"""
Vai trò: Medical Researcher.
Topic: {item.get('title')}
Description: {item.get('description')}
Tìm kiếm thông tin y khoa chính xác (Mock knowledge).

Output YAML:
```yaml
notes: |
  - Fact 1
  - Fact 2
```
"""
        try:
            response = call_llm(prompt)
            if "```yaml" in response:
                clean = response.split("```yaml")[1].split("```")[0].strip()
            elif "```" in response:
                 clean = response.split("```")[1].split("```")[0].strip()
            else:
                clean = response.strip()
            data = yaml.safe_load(clean)
            return data.get("notes", "")
        except:
            return "No info found."

    def post(self, shared, prep_res, notes):
        idx = self.params.get("index")
        if idx is not None:
            if "research_data" not in shared:
                shared["research_data"] = {}
            shared["research_data"][idx] = notes
        return "default"

class ContentWriterNode(Node):
    def prep(self, shared):
        idx = self.params.get("index")
        if idx is not None:
            item = shared["blueprint"][idx]
            notes = shared.get("research_data", {}).get(idx, "")
            return {"item": item, "notes": notes}
        return None

    def exec(self, inputs):
        if not inputs: return {}
        item = inputs["item"]

        prompt = f"""
Vai trò: Content Writer.
Nhiệm vụ: Viết nội dung chi tiết.
Topic: "{item.get('title')}"
Research: {inputs['notes']}

Output YAML:
```yaml
slide:
  title: "{item.get('title')}"
  content:
    - Point 1
    - Point 2
  speaker_notes: "..."
```
"""
        try:
            response = call_llm(prompt)
            if "```yaml" in response:
                clean = response.split("```yaml")[1].split("```")[0].strip()
            elif "```" in response:
                 clean = response.split("```")[1].split("```")[0].strip()
            else:
                clean = response.strip()
            return yaml.safe_load(clean)
        except:
            return {"slide": {"title": item.get('title', 'Unknown'), "content": ["Error"], "speaker_notes": ""}}

    def post(self, shared, prep_res, exec_res):
        idx = self.params.get("index")
        if idx is not None:
            if "slides_data" not in shared:
                shared["slides_data"] = {}
            if isinstance(exec_res, dict) and "slide" in exec_res:
                shared["slides_data"][idx] = exec_res["slide"]
            else:
                shared["slides_data"][idx] = {"title": "Error", "content": [], "speaker_notes": ""}
        return "default"

class PPTGeneratorNode(Node):
    def prep(self, shared):
        data = shared.get("slides_data", {})
        sorted_keys = sorted(data.keys())
        sorted_slides = [data[k] for k in sorted_keys]

        reqs = shared.get("requirements", {})
        topic = reqs.get("topic", "presentation") if reqs else "presentation"
        return {"slides": sorted_slides, "topic": topic}

    def exec(self, inputs):
        from utils.ppt_gen import generate_ppt
        import os

        os.makedirs("output", exist_ok=True)
        filename = f"output/{inputs['topic'].replace(' ', '_')}.pptx"

        try:
            generate_ppt(inputs["slides"], filename)
            return filename
        except Exception as e:
            print(f"PPT Generation Error: {e}")
            return None

    def post(self, shared, prep_res, filename):
        shared["pptx_file"] = filename
        return "default"

class DocGeneratorNode(Node):
    def prep(self, shared):
        data = shared.get("slides_data", {})
        sorted_keys = sorted(data.keys())
        sorted_slides = [data[k] for k in sorted_keys]

        reqs = shared.get("requirements", {})
        topic = reqs.get("topic", "document") if reqs else "document"
        return {"content": sorted_slides, "topic": topic}

    def exec(self, inputs):
        from utils.doc_gen import generate_doc
        import os

        os.makedirs("output", exist_ok=True)
        filename = f"output/{inputs['topic'].replace(' ', '_')}.docx"

        try:
            generate_doc(inputs["content"], filename, inputs["topic"])
            return filename
        except Exception as e:
            print(f"Doc Generation Error: {e}")
            return None

    def post(self, shared, prep_res, filename):
        shared["docx_file"] = filename
        return "default"
