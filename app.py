import streamlit as st
import time
import os
import asyncio
import yaml
from flows.app_flows import create_interview_flow, create_planning_flow, create_execution_flow

# Page Config
st.set_page_config(page_title="Trợ lý Tài liệu Y khoa", page_icon="🏥", layout="wide")

def load_shared_context():
    """Load the initial shared state from YAML file."""
    try:
        with open("shared_context.yaml", "r") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        st.error("File 'shared_context.yaml' not found!")
        return {}

# Session State Init
if "stage" not in st.session_state:
    st.session_state.stage = "interview" # interview, plan, executing, done
if "messages" not in st.session_state:
    st.session_state.messages = []

if "shared" not in st.session_state:
    with st.spinner("Đang khởi tạo hệ thống..."):
        # Load Initial Shared State from YAML
        shared_state = load_shared_context()

        # Initialize UI messages from shared state if present
        if shared_state.get("chat_history"):
            st.session_state.messages = list(shared_state["chat_history"])

        st.session_state.shared = shared_state

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
                interview_flow = create_interview_flow()
                try:
                    # Run the flow with the shared state
                    interview_flow.run(st.session_state.shared)
                except Exception as e:
                    st.error(f"Lỗi hệ thống: {e}")
                    import traceback
                    st.write(traceback.format_exc())
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
    st.title("📋 Kế hoạch tài liệu (Blueprint)")

    reqs = st.session_state.shared.get("requirements", {})
    st.info(f"**Chủ đề:** {reqs.get('topic')}\n\n**Đối tượng:** {reqs.get('audience')}\n\n**Mục tiêu:** {reqs.get('objectives')}")

    if not st.session_state.shared.get("blueprint"):
        with st.spinner("Đang lập dàn ý..."):
            planning_flow = create_planning_flow()
            try:
                planning_flow.run(st.session_state.shared)
            except Exception as e:
                st.error(f"Lỗi lập dàn ý: {e}")

            if not st.session_state.shared.get("blueprint"):
                st.warning("Không tạo được dàn ý. Vui lòng thử lại.")
            else:
                st.rerun()

    blueprint = st.session_state.shared.get("blueprint", [])

    st.write("### Dàn ý đề xuất:")

    new_blueprint = []
    # Use index to make unique keys
    for i, item in enumerate(blueprint):
        with st.expander(f"Section {i+1}: {item.get('title')}", expanded=True):
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

                planning_flow = create_planning_flow()
                planning_flow.run(st.session_state.shared)
                st.rerun()
        else:
            st.warning("Vui lòng nhập nội dung cần chỉnh sửa.")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Xác nhận & Tạo tài liệu", type="primary"):
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

    progress_bar = st.progress(0)
    status_text = st.empty()

    try:
        status_text.text("Đang thực thi quy trình: Research -> Write -> Generate Doc...")

        execution_flow = create_execution_flow()

        # Run the full async flow
        try:
            loop = asyncio.get_running_loop()
            loop.run_until_complete(execution_flow.run_async(st.session_state.shared))
        except RuntimeError:
            asyncio.run(execution_flow.run_async(st.session_state.shared))

        progress_bar.progress(100)

        st.session_state.stage = "done"
        st.rerun()
    except Exception as e:
        st.error(f"Lỗi trong quá trình thực thi: {e}")
        st.write(e)
        import traceback
        st.write(traceback.format_exc())
        if st.button("Thử lại"):
            st.rerun()

# --- STAGE 4: DONE ---
elif st.session_state.stage == "done":
    st.title("✅ Hoàn tất!")
    st.balloons()

    filename = st.session_state.shared.get("output_file")

    if filename and os.path.exists(filename):
        with open(filename, "rb") as f:
            st.download_button(
                label="📥 Tải xuống Tài liệu (.docx)",
                data=f,
                file_name=os.path.basename(filename),
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )

    st.write("### Nội dung chi tiết:")
    doc_sections = st.session_state.shared.get("doc_sections", [])

    for sec in doc_sections:
        with st.expander(f"{sec.get('title')}", expanded=True):
            for block in sec.get('body', []):
                if block.get('heading'):
                    st.write(f"**{block.get('heading')}**")
                if block.get('content'):
                    st.write(block.get('content'))

    if st.button("Làm bài mới"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
