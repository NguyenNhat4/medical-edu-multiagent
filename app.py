import streamlit as st
import time
import os
import asyncio
from nodes import InterviewerNode, PlannerNode, ResearcherNode, ContentWriterNode, DocGeneratorNode
from utils.app_config import AppConfig
from rag_agent import MedicalRAG
from web_search_processor_agent import WebSearchProcessorAgent

# Page Config
st.set_page_config(page_title="Trợ lý Tài liệu Y khoa", page_icon="🏥", layout="wide")

# --- CACHED RESOURCES ---
@st.cache_resource
def load_models_cached():
    """Load embedding models once and cache them globally."""
    from utils.get_embedding import EmbeddingModels
    return EmbeddingModels()

# Load models immediately
with st.spinner("Đang tải các mô hình AI (lần đầu sẽ mất khoảng 1 phút)..."):
    models = load_models_cached()
    from utils.get_embedding import set_models
    set_models(models)

# Session State Init
if "stage" not in st.session_state:
    st.session_state.stage = "interview" # interview, plan, executing, done
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "agent", "content": "Xin chào! Tôi là Trợ lý Y khoa. Bạn cần soạn tài liệu về chủ đề gì?"}]

if "shared" not in st.session_state:
    with st.spinner("Đang khởi tạo hệ thống..."):
        config = AppConfig()
        rag_agent = MedicalRAG(config)
        web_search_processor_agent = WebSearchProcessorAgent(config)

        st.session_state.shared = {
            "chat_history": [{"role": "agent", "content": "Xin chào! Tôi là Trợ lý Y khoa. Bạn cần soạn tài liệu về chủ đề gì?"}],
            "requirements": {},
            "blueprint": [],
            "research_data": [],
            "doc_sections": [],
            "rag_agent": rag_agent,
            "web_search_processor_agent": web_search_processor_agent
        }

# --- STAGE 1: INTERVIEW ---
if st.session_state.stage == "interview":
    st.title("Trợ lý Y khoa AI")

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
    st.title("📋 Kế hoạch tài liệu (Blueprint)")

    reqs = st.session_state.shared.get("requirements", {})
    st.info(f"**Chủ đề:** {reqs.get('topic')}\n\n**Đối tượng:** {reqs.get('audience')}\n\n**Mục tiêu:** {reqs.get('objectives')}")

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

                planner = PlannerNode()
                planner.run(st.session_state.shared)
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
        # 1. Research
        status_text.text("Đang tìm kiếm thông tin (Search & Ingest)...")
        researcher = ResearcherNode()
        try:
            loop = asyncio.get_running_loop()
            loop.run_until_complete(researcher.run_async(st.session_state.shared))
        except RuntimeError:
            asyncio.run(researcher.run_async(st.session_state.shared))
        progress_bar.progress(30)

        # 2. Write
        status_text.text("Đang soạn thảo nội dung (Retrieval & Content Writing)...")
        writer = ContentWriterNode()
        # Use asyncio.run for async node in synchronous Streamlit app
        try:
            loop = asyncio.get_running_loop()
            loop.run_until_complete(writer.run_async(st.session_state.shared))
        except RuntimeError:
            asyncio.run(writer.run_async(st.session_state.shared))
        progress_bar.progress(60)

        # 3. Doc Generation
        status_text.text("Đang tạo file DOCX (Doc Generation)...")
        doc_gen = DocGeneratorNode()
        doc_gen.run(st.session_state.shared)
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
