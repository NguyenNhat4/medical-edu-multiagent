import streamlit as st
import time
import os
from nodes import InterviewerNode, PlannerNode, ResearcherNode, ContentWriterNode, PPTGeneratorNode, DocGeneratorNode

# Page Config
st.set_page_config(page_title="Trợ lý Bài giảng Y khoa", page_icon="🏥", layout="wide")

# Session State Init
if "stage" not in st.session_state:
    st.session_state.stage = "interview" # interview, plan, executing, done
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "agent", "content": "Xin chào! Tôi là Trợ lý Y khoa. Bạn cần soạn bài giảng về chủ đề gì?"}]
if "shared" not in st.session_state:
    st.session_state.shared = {
        "chat_history": [{"role": "agent", "content": "Xin chào! Tôi là Trợ lý Y khoa. Bạn cần soạn bài giảng về chủ đề gì?"}],
        "requirements": {},
        "blueprint": [],
        "research_data": {},
        "slides_data": {}
    }

# --- STAGE 1: INTERVIEW ---
if st.session_state.stage == "interview":
    st.title("🏥 Trợ lý Y khoa AI - Thu thập yêu cầu")

    # Display Chat
    for msg in st.session_state.messages:
        role = "user" if msg["role"] == "user" else "assistant"
        with st.chat_message(role):
            st.write(msg["content"])

    # Input
    if prompt := st.chat_input("Nhập yêu cầu của bạn..."):
        # User turn
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.session_state.shared["chat_history"].append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        # Agent turn
        with st.chat_message("assistant"):
            with st.spinner("Đang suy nghĩ..."):
                interviewer = InterviewerNode()
                try:
                    interviewer.run(st.session_state.shared)
                except Exception as e:
                    st.error(f"Lỗi hệ thống: {e}")
                    st.stop()

                result = st.session_state.shared.get("interview_result", {})
                status = result.get("status", "ask")
                message = result.get("message", "...")

                st.write(message)
                st.session_state.messages.append({"role": "agent", "content": message})
                st.session_state.shared["chat_history"].append({"role": "agent", "content": message})

                if status == "done":
                    st.success("Đã hiểu yêu cầu! Chuyển sang lập kế hoạch...")
                    time.sleep(1)
                    st.session_state.stage = "plan"
                    st.rerun()

# --- STAGE 2: PLAN ---
elif st.session_state.stage == "plan":
    st.title("📋 Kế hoạch bài giảng (Blueprint)")

    reqs = st.session_state.shared.get("requirements", {})
    outputs = reqs.get('outputs', [])
    st.info(f"**Chủ đề:** {reqs.get('topic')}\n\n**Đối tượng:** {reqs.get('audience')}\n\n**Định dạng:** {outputs}")

    # If blueprint is empty, run planner
    if not st.session_state.shared.get("blueprint"):
        with st.spinner("Đang lập dàn ý..."):
            planner = PlannerNode()
            try:
                planner.run(st.session_state.shared)
            except Exception as e:
                st.error(f"Lỗi lập dàn ý: {e}")

            if not st.session_state.shared.get("blueprint"):
                st.warning("Không tạo được dàn ý. Vui lòng thử lại.")
            else:
                st.rerun()

    blueprint = st.session_state.shared.get("blueprint", [])

    st.write("### Dàn ý đề xuất:")

    # Show feedback section FIRST or AFTER? Usually after checking the list.

    new_blueprint = []
    for i, item in enumerate(blueprint):
        with st.expander(f"Phần {i+1}: {item.get('title')}", expanded=True):
            title = st.text_input("Tiêu đề", item.get('title'), key=f"title_{i}")
            desc = st.text_area("Mô tả / Nội dung", item.get('description'), key=f"desc_{i}")
            new_blueprint.append({"title": title, "description": desc})

    st.divider()
    st.subheader("Góp ý & Chỉnh sửa")
    feedback = st.text_area("Bạn có muốn điều chỉnh gì về cấu trúc dàn ý không? (Ví dụ: Thêm phần biến chứng, bỏ phần lịch sử...)", key="plan_feedback_input")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 Tái tạo dàn ý theo góp ý"):
            if feedback:
                st.session_state.shared["plan_feedback"] = feedback
                st.session_state.shared["blueprint"] = [] # Clear to force rerun
                st.rerun()
            else:
                st.warning("Vui lòng nhập nội dung góp ý để tái tạo.")

    with col2:
        if st.button("✅ Xác nhận & Tạo nội dung", type="primary"):
            st.session_state.shared["blueprint"] = new_blueprint
            st.session_state.stage = "executing"
            st.rerun()

# --- STAGE 3: EXECUTION ---
elif st.session_state.stage == "executing":
    st.title("⚙️ Đang khởi tạo nội dung...")

    blueprint = st.session_state.shared.get("blueprint", [])
    total_steps = len(blueprint)

    progress_bar = st.progress(0)
    status_text = st.empty()

    researcher = ResearcherNode()
    writer = ContentWriterNode()

    # Run Batch
    for i, item in enumerate(blueprint):
        status_text.text(f"Đang xử lý Phần {i+1}/{total_steps}: {item['title']}...")

        # 1. Research
        researcher.set_params({"index": i})
        researcher.run(st.session_state.shared)

        # 2. Write
        writer.set_params({"index": i})
        writer.run(st.session_state.shared)

        progress_bar.progress((i + 1) / total_steps)

    reqs = st.session_state.shared.get("requirements", {})
    outputs = reqs.get("outputs", [])
    # Normalize
    if isinstance(outputs, str): outputs = [outputs]
    outputs_str = str(outputs).lower()

    # Generate PPTX
    if "slide" in outputs_str or "ppt" in outputs_str:
        status_text.text("Đang tạo file PPTX...")
        ppt_gen = PPTGeneratorNode()
        ppt_gen.run(st.session_state.shared)

    # Generate DOCX
    if "doc" in outputs_str or "tài liệu" in outputs_str or "word" in outputs_str:
        status_text.text("Đang tạo file DOCX...")
        doc_gen = DocGeneratorNode()
        doc_gen.run(st.session_state.shared)

    st.session_state.stage = "done"
    st.rerun()

# --- STAGE 4: DONE ---
elif st.session_state.stage == "done":
    st.title("✅ Hoàn tất!")
    st.balloons()

    pptx_file = st.session_state.shared.get("pptx_file")
    docx_file = st.session_state.shared.get("docx_file")

    col1, col2 = st.columns(2)

    with col1:
        if pptx_file and os.path.exists(pptx_file):
            with open(pptx_file, "rb") as f:
                st.download_button(
                    label="📥 Tải xuống Slide (.pptx)",
                    data=f,
                    file_name=os.path.basename(pptx_file),
                    mime="application/vnd.openxmlformats-officedocument.presentationml.presentation"
                )

    with col2:
        if docx_file and os.path.exists(docx_file):
            with open(docx_file, "rb") as f:
                st.download_button(
                    label="📥 Tải xuống Tài liệu (.docx)",
                    data=f,
                    file_name=os.path.basename(docx_file),
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )

    st.write("### Nội dung chi tiết:")
    slides_data = st.session_state.shared.get("slides_data", {})
    sorted_keys = sorted(slides_data.keys())
    for k in sorted_keys:
        slide = slides_data[k]
        with st.expander(f"{slide.get('title')}"):
            st.write(slide.get('content'))
            st.caption(f"Note: {slide.get('speaker_notes')}")

    if st.button("Làm bài mới"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
