from pocketflow import Node, BatchNode
from utils.call_llm import call_llm
import json

class InterviewerNode(Node):
    def prep(self, shared):
        return shared.get("history", [])

    def exec(self, history):
        print("\n--- Bắt đầu thu thập yêu cầu (Requirement Gathering) ---\n")

        conversation = []

        # Limit max turns to prevent infinite loops in edge cases
        for _ in range(15):
            # Construct prompt to decide next move
            prompt = f"""
Bạn là một trợ lý ảo hỗ trợ xây dựng bài giảng y khoa (Medical Agent).
Mục tiêu: Thu thập đầy đủ thông tin từ người dùng.

Các thông tin bắt buộc cần có:
1. Chủ đề (Topic)
2. Đối tượng người nghe (Audience) - Sinh viên Y, Bác sĩ nội trú, hay Bệnh nhân?
3. Các tài liệu cần tạo (Artifacts). Chỉ chấp nhận các loại sau (có thể chọn nhiều):
   - "lecture" (Bài giảng chi tiết dạng đọc)
   - "slide" (Nội dung Slide)
   - "note" (Ghi chú giảng viên)
   - "student" (Tài liệu ôn tập cho sinh viên)

Lịch sử hội thoại:
{json.dumps(conversation, ensure_ascii=False)}

Nhiệm vụ:
- Phân tích hội thoại.
- Nếu ĐÃ ĐỦ thông tin: Trả về JSON với key "status": "done" và "requirements".
- Nếu CHƯA ĐỦ: Trả về JSON với key "status": "ask" và "question" (câu hỏi ngắn gọn, lịch sự bằng tiếng Việt).

Format JSON output (KHÔNG kèm markdown):
{{
  "status": "done" | "ask",
  "question": "...",
  "requirements": {{
      "topic": "...",
      "audience": "...",
      "artifacts": ["lecture", "slide", ...]
  }}
}}
"""
            response = call_llm(prompt)
            # Basic cleaning
            response = response.replace("```json", "").replace("```", "").strip()

            try:
                data = json.loads(response)
            except Exception as e:
                # If JSON fails, ask again or retry. Here we just print and continue logic
                print(f"[Debug] Lỗi parse JSON: {e}. Raw: {response}")
                continue

            if data.get("status") == "done":
                reqs = data.get("requirements", {})
                print(f"\n[System] Đã xác nhận yêu cầu: {reqs.get('topic')}")
                print(f"[System] Các tài liệu sẽ tạo: {reqs.get('artifacts')}")
                return reqs
            else:
                question = data.get("question", "Bạn cần tôi giúp gì thêm?")
                print(f"\nAgent: {question}")
                user_ans = input("User: ")
                conversation.append({"role": "agent", "content": question})
                conversation.append({"role": "user", "content": user_ans})

        # Fallback if loop ends
        print("[System] Đã đạt giới hạn câu hỏi. Sử dụng thông tin hiện có.")
        return {"topic": "Unknown", "audience": "General", "artifacts": ["lecture"]}

    def post(self, shared, prep_res, requirements):
        shared["requirements"] = requirements
        return "default"

class PlannerNode(Node):
    def prep(self, shared):
        return shared["requirements"]

    def exec(self, requirements):
        print("\n[System] Đang lập dàn ý (Planning)...")
        prompt = f"""
Dựa trên yêu cầu sau, hãy lập một Dàn ý (Outline) chi tiết cho bài giảng y khoa.

Topic: {requirements.get('topic')}
Audience: {requirements.get('audience')}

Output mong muốn:
1. Tiêu đề bài giảng.
2. Các phần chính (I, II, III...) và nội dung tóm tắt.
3. Phân bổ thời gian dự kiến.

Hãy trình bày dưới dạng văn bản rõ ràng (Markdown). Ngôn ngữ: Tiếng Việt.
"""
        return call_llm(prompt)

    def post(self, shared, prep_res, outline):
        shared["plan_outline"] = outline
        return "default"

class RefinerNode(Node):
    def prep(self, shared):
        return shared["plan_outline"]

    def exec(self, outline):
        print("\n--- Đề xuất Dàn ý (Outline) ---\n")
        print(outline)
        print("\n--------------------------------\n")
        print("Bạn có đồng ý với dàn ý này không? (Gõ 'ok' để tiếp tục, hoặc nhập nội dung cần sửa đổi)")
        return input("User: ")

    def post(self, shared, prep_res, user_input):
        clean_input = user_input.lower().strip()
        if clean_input in ["ok", "yes", "y", "đồng ý"]:
            return "approved"
        else:
            # Append feedback to requirements to refine the plan
            old_topic = shared["requirements"].get("topic", "")
            shared["requirements"]["topic"] = f"{old_topic} (Lưu ý thêm: {user_input})"
            return "revise"

class ContentGeneratorBatchNode(BatchNode):
    def prep(self, shared):
        reqs = shared["requirements"]
        outline = shared["plan_outline"]
        artifacts = reqs.get("artifacts", [])

        # Normalize artifacts list just in case
        if not isinstance(artifacts, list):
            artifacts = ["lecture"]

        tasks = []
        for art in artifacts:
            tasks.append({
                "type": art,
                "outline": outline,
                "requirements": reqs
            })

        if not tasks:
            print("[Warning] Không có tài liệu nào được chọn. Mặc định tạo Bài giảng.")
            tasks.append({"type": "lecture", "outline": outline, "requirements": reqs})

        return tasks

    def exec(self, task):
        art_type = task["type"]
        outline = task["outline"]
        reqs = task["requirements"]

        print(f"\n[System] Đang tạo nội dung cho: {art_type.upper()}...")

        type_instructions = {
            "lecture": "Viết bài giảng chi tiết, chuyên sâu, giọng văn học thuật y khoa.",
            "slide": "Viết nội dung Slide dạng Markdown. Dùng '---' phân cách các slide. Ít chữ, nhiều ý chính.",
            "note": "Viết ghi chú cho giảng viên: Cần nhấn mạnh điểm nào? Câu hỏi tương tác là gì?",
            "student": "Viết tài liệu ôn tập cho sinh viên: Tóm tắt key points, câu hỏi trắc nghiệm tự luyện."
        }

        instruction = type_instructions.get(art_type, "Viết nội dung chi tiết.")

        prompt = f"""
Bạn là chuyên gia y khoa.
Nhiệm vụ: Tạo tài liệu loại '{art_type}'.
Chủ đề: {reqs['topic']}
Đối tượng: {reqs['audience']}
Dàn ý:
{outline}

Yêu cầu định dạng: {instruction}
Ngôn ngữ: Tiếng Việt.
"""
        content = call_llm(prompt)
        return {"type": art_type, "content": content}

    def post(self, shared, prep_res, exec_res_list):
        results = {}
        for item in exec_res_list:
            results[item["type"]] = item["content"]
        shared["generated_content"] = results
        return "default"
