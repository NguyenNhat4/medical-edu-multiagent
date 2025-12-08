import streamlit as st
import json
from nodes import InterviewerNode, PlannerNode, ContentGeneratorBatchNode
from utils.db import get_db_connection, init_db, log_message

# Page Config
st.set_page_config(page_title="Medical Agent", layout="wide")

# Init DB
if "db_conn" not in st.session_state:
    st.session_state.db_conn = get_db_connection()
    init_db(st.session_state.db_conn)

# Init State
if "messages" not in st.session_state:
    st.session_state.messages = [] # Chat history
if "app_state" not in st.session_state:
    st.session_state.app_state = "interview" # interview, confirm, execution, result
if "requirements" not in st.session_state:
    st.session_state.requirements = {}

def reset_app():
    st.session_state.messages = []
    st.session_state.app_state = "interview"
    st.session_state.requirements = {}
    st.rerun()

# Sidebar
with st.sidebar:
    st.title("Medical Training Agent")
    st.markdown("---")
    if st.button("Reset Conversation"):
        reset_app()

    st.markdown("### Debug Info")
    st.caption(f"State: {st.session_state.app_state}")
    if st.session_state.requirements:
        st.caption("Requirements:")
        st.json(st.session_state.requirements)

# --- INTERVIEW PHASE ---
if st.session_state.app_state == "interview":
    st.subheader("Gathering Requirements (Thu thập yêu cầu)")

    # Display Chat
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat Input
    if prompt := st.chat_input("Mô tả nhu cầu đào tạo của bạn... (Ví dụ: Tạo bài giảng về Tim mạch cho sinh viên)"):
        # User Message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Log to DB
        log_message(st.session_state.db_conn, "USER_INPUT", prompt)

        # Agent Logic
        with st.spinner("Agent đang suy nghĩ..."):
            # Prepare shared store
            # InterviewerNode expects 'history'
            shared = {"history": st.session_state.messages, "requirements": {}}

            # Run Node directly (Single Turn)
            interviewer = InterviewerNode()
            action = interviewer.run(shared)

            # Process Response
            last_resp = shared.get("last_agent_response", {})

            if action == "done":
                st.session_state.requirements = shared["requirements"]
                st.session_state.app_state = "confirm"
                st.rerun()
            else:
                # Ask question
                question = last_resp.get("question", "Tôi cần thêm thông tin.")
                st.session_state.messages.append({"role": "assistant", "content": question})
                with st.chat_message("assistant"):
                    st.markdown(question)

# --- CONFIRM PHASE ---
elif st.session_state.app_state == "confirm":
    st.subheader("Xác nhận yêu cầu (Confirmation)")
    st.info("Vui lòng kiểm tra thông tin dưới đây trước khi tạo tài liệu.")

    reqs = st.session_state.requirements

    col1, col2 = st.columns(2)
    with col1:
        st.text_input("Chủ đề (Topic)", value=reqs.get("topic", ""), disabled=True)
        st.text_input("Đối tượng (Audience)", value=reqs.get("audience", ""), disabled=True)
    with col2:
        artifacts = reqs.get("artifacts", [])
        if not isinstance(artifacts, list): artifacts = [artifacts]
        st.multiselect("Tài liệu cần tạo (Artifacts)", options=["lecture", "slide", "note", "student"], default=artifacts, disabled=True)

    st.markdown("---")
    c1, c2 = st.columns([1, 4])
    if c1.button("Đồng ý & Tạo (Approve)"):
        st.session_state.app_state = "execution"
        st.rerun()

    if c2.button("Sửa lại (Modify)"):
        st.warning("Hệ thống sẽ reset hội thoại để bạn nhập lại yêu cầu.")
        reset_app()

# --- EXECUTION PHASE ---
elif st.session_state.app_state == "execution":
    st.subheader("Đang tạo tài liệu (Generating Content)...")

    progress_bar = st.progress(0, text="Khởi động Agents...")

    shared = {
        "requirements": st.session_state.requirements,
        "history": st.session_state.messages
    }

    # Run Flow Logic manually to update progress
    try:
        # Planner
        progress_bar.progress(20, text="Planner Agent: Đang lập dàn ý (Planning)...")
        log_message(st.session_state.db_conn, "SYSTEM", "Starting Planner")

        planner = PlannerNode()
        planner.run(shared)

        # Generator
        progress_bar.progress(50, text="Sub-Agents: Đang viết nội dung chi tiết...")
        log_message(st.session_state.db_conn, "SYSTEM", "Starting Generator Batch")

        generator = ContentGeneratorBatchNode()
        generator.run(shared)

        progress_bar.progress(100, text="Hoàn tất!")

        # Store results
        st.session_state.results = shared.get("generated_content", {})
        st.session_state.plan_outline = shared.get("plan_outline", "")
        st.session_state.app_state = "result"
        st.rerun()

    except Exception as e:
        st.error(f"Đã xảy ra lỗi: {e}")
        log_message(st.session_state.db_conn, "ERROR", str(e))
        st.exception(e)

# --- RESULT PHASE ---
elif st.session_state.app_state == "result":
    st.subheader("Kết quả (Final Artifacts)")
    st.success("Đã tạo xong tài liệu!")

    with st.expander("Xem Dàn ý (Plan Outline)"):
        st.markdown(st.session_state.plan_outline)

    results = st.session_state.results
    if results:
        tabs = st.tabs(list(results.keys()))

        for i, (key, content) in enumerate(results.items()):
            with tabs[i]:
                st.markdown(content)
                st.download_button(f"Download {key}.md", content, file_name=f"{key}.md")
    else:
        st.warning("Không có nội dung nào được tạo.")

    st.markdown("---")
    if st.button("Bắt đầu phiên mới"):
        reset_app()
