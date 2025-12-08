from pocketflow import Node
from utils.call_llm import call_llm
import yaml
import json

class InterviewerNode(Node):
    def prep(self, shared):
        return shared.get("chat_history", [])

    def exec(self, history):
        # Convert history to string for prompt
        history_str = json.dumps(history, ensure_ascii=False)

        prompt = f"""
Bạn là một trợ lý ảo hỗ trợ xây dựng bài giảng y khoa (Medical Agent).
Mục tiêu: Thu thập đầy đủ thông tin từ người dùng.

Các thông tin bắt buộc cần có:
1. Chủ đề (Topic)
2. Đối tượng người nghe (Audience) - Sinh viên Y, Bác sĩ nội trú, hay Bệnh nhân?
3. Các tài liệu cần tạo (Artifacts). Chỉ chấp nhận các loại sau (có thể chọn nhiều):
   - "lecture" (Bài giảng chi tiết)
   - "slide" (Nội dung Slide)
   - "note" (Ghi chú giảng viên)
   - "student" (Tài liệu ôn tập cho sinh viên)

Lịch sử hội thoại:
{history_str}

Nhiệm vụ:
- Phân tích hội thoại.
- Nếu ĐÃ ĐỦ thông tin: Trả về status "done" và requirements.
- Nếu CHƯA ĐỦ: Trả về status "ask" và câu hỏi tiếp theo.

OUTPUT FORMAT: REQUIRED YAML (No Markdown, pure YAML)
```yaml
status: done # or ask
question: "Câu hỏi của bạn..." # null if done
requirements: # null if ask
  topic: "..."
  audience: "..."
  artifacts: ["lecture", "slide"]
```
"""
        return call_llm(prompt)

    def post(self, shared, prep_res, exec_res):
        # Clean response
        clean_res = exec_res.replace("```yaml", "").replace("```", "").strip()
        try:
            data = yaml.safe_load(clean_res)
        except Exception as e:
            print(f"Error parsing YAML: {e}\nRaw: {exec_res}")
            # Fallback
            data = {"status": "ask", "question": "Xin lỗi, tôi gặp lỗi hệ thống. Bạn có thể nhắc lại không?"}

        shared["last_agent_response"] = data

        if data.get("status") == "done":
            shared["requirements"] = data.get("requirements")
            return "done"
        else:
            return "ask"

class PlannerNode(Node):
    def prep(self, shared):
        return shared.get("requirements", {})

    def exec(self, requirements):
        prompt = f"""
Dựa trên yêu cầu sau, hãy lập một Dàn ý (Outline) chi tiết cho bài giảng y khoa.
Phân chia task cụ thể cho các sub-agents.

Input Requirements:
{json.dumps(requirements, ensure_ascii=False)}

OUTPUT FORMAT: REQUIRED YAML
```yaml
outline: |
  # Tiêu đề bài giảng
  ## Phần 1...
  ## Phần 2...
subtasks:
  - title: "Soạn bài giảng chi tiết"
    description: "Viết nội dung đầy đủ..."
  - title: "Soạn nội dung Slide"
    description: "Tóm tắt ý chính..."
```
"""
        return call_llm(prompt)

    def post(self, shared, prep_res, exec_res):
        clean_res = exec_res.replace("```yaml", "").replace("```", "").strip()
        try:
            data = yaml.safe_load(clean_res)
            shared["plan_outline"] = data.get("outline", "")
            shared["subtasks"] = data.get("subtasks", [])
        except Exception as e:
            print(f"Error parsing Plan YAML: {e}")
            shared["plan_outline"] = exec_res
            shared["subtasks"] = []
        return "default"

class ContentGeneratorBatchNode(BatchNode):
    def prep(self, shared):
        reqs = shared.get("requirements", {})
        outline = shared.get("plan_outline", "")
        artifacts = reqs.get("artifacts", [])

        # Ensure list
        if not isinstance(artifacts, list):
            artifacts = [artifacts] if artifacts else []

        tasks = []
        for art in artifacts:
            tasks.append({
                "type": art,
                "outline": outline,
                "requirements": reqs
            })
        return tasks

    def exec(self, task):
        art_type = task["type"]
        outline = task["outline"]
        reqs = task["requirements"]

        prompt = f"""
Bạn là Sub-Agent chuyên trách.
Nhiệm vụ: Tạo tài liệu loại '{art_type}'.
Chủ đề: {reqs.get('topic')}
Đối tượng: {reqs.get('audience')}
Dàn ý chung:
{outline}

Yêu cầu: Viết nội dung chất lượng cao bằng tiếng Việt.
Trả về YAML:
```yaml
type: "{art_type}"
content: |
  ... Nội dung chi tiết ...
```
"""
        res = call_llm(prompt)
        # Parse result immediately to extract content
        clean_res = res.replace("```yaml", "").replace("```", "").strip()
        try:
            data = yaml.safe_load(clean_res)
            return {"type": art_type, "content": data.get("content", res)}
        except:
            return {"type": art_type, "content": res}

    def post(self, shared, prep_res, exec_res_list):
        results = {}
        for item in exec_res_list:
            results[item["type"]] = item["content"]
        shared["generated_content"] = results
        return "default"
