import streamlit as st
import time
import os
from nodes import InterviewerNode, PlannerNode, ResearcherNode, ContentWriterNode, PPTGeneratorNode

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
                # Run the node
                # Note: node.run(shared) returns the action string (e.g., "default")
                # But inside the node, it updates shared["interview_result"]
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
    st.info(f"**Chủ đề:** {reqs.get('topic')}\n\n**Đối tượng:** {reqs.get('audience')}\n\n**Mục tiêu:** {reqs.get('objectives')}")

    if not st.session_state.shared.get("blueprint"):
        with st.spinner("Đang lập dàn ý..."):
            planner = PlannerNode()
            try:
                planner.run(st.session_state.shared)
            except Exception as e:
                st.error(f"Lỗi lập dàn ý: {e}")

            # If blueprint is still empty, retry or show error
            if not st.session_state.shared.get("blueprint"):
                st.warning("Không tạo được dàn ý. Vui lòng thử lại.")
            else:
                st.rerun()

    blueprint = st.session_state.shared.get("blueprint", [])

    st.write("### Dàn ý đề xuất:")

    new_blueprint = []
    # Use index to make unique keys
    for i, item in enumerate(blueprint):
        with st.expander(f"Slide {i+1}: {item.get('title')}", expanded=True):
            title = st.text_input("Tiêu đề", item.get('title'), key=f"title_{i}")
            desc = st.text_area("Mô tả / Nội dung", item.get('description'), key=f"desc_{i}")
            new_blueprint.append({"title": title, "description": desc})

    st.write("---")
    st.subheader("🛠️ Chỉnh sửa bằng AI")
    feedback = st.text_area("Nhập yêu cầu chỉnh sửa...", key="planner_feedback_input")
    if st.button("✨ Sửa dàn ý"):
        if feedback.strip():
            with st.spinner("Đang cập nhật dàn ý..."):
                st.session_state.shared["blueprint"] = new_blueprint
                st.session_state.shared["planner_feedback"] = feedback

                planner = PlannerNode()
                planner.run(st.session_state.shared)
                st.rerun()
        else:
            st.warning("Vui lòng nhập nội dung cần chỉnh sửa.")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Xác nhận & Tạo bài giảng", type="primary"):
            st.session_state.shared["blueprint"] = new_blueprint
            st.session_state.stage = "executing"
            st.rerun()

    with col2:
        if st.button("🔄 Lập lại dàn ý"):
            st.session_state.shared["blueprint"] = []
            st.session_state.shared["planner_feedback"] = ""
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
        status_text.text(f"Đang xử lý Slide {i+1}/{total_steps}: {item['title']}...")

        # 1. Research
        researcher.set_params({"index": i})
        researcher.run(st.session_state.shared)

        # 2. Write
        writer.set_params({"index": i})
        writer.run(st.session_state.shared)

        progress_bar.progress((i + 1) / total_steps)

    status_text.text("Đang tạo file PPTX...")
    ppt_gen = PPTGeneratorNode()
    ppt_gen.run(st.session_state.shared)

    st.session_state.stage = "done"
    st.rerun()

# --- STAGE 4: DONE ---
elif st.session_state.stage == "done":
    st.title("✅ Hoàn tất!")
    st.balloons()

    filename = st.session_state.shared.get("output_file")

    if filename and os.path.exists(filename):
        with open(filename, "rb") as f:
            st.download_button(
                label="📥 Tải xuống Slide (.pptx)",
                data=f,
                file_name=os.path.basename(filename),
                mime="application/vnd.openxmlformats-officedocument.presentationml.presentation"
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
