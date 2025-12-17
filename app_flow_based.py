"""
Streamlit App - Flow-Based Architecture

This app demonstrates proper flow usage where:
1. Nodes are connected into flows (not called individually)
2. Flows orchestrate the entire workflow
3. Clean separation between UI and business logic
"""

import streamlit as st
import time
import os
import asyncio
import logging
from pocketflow import Flow, AsyncFlow

# Import nodes for flow construction
from nodes.interview import InterviewerNode, PlannerNode
from nodes.research import ResearcherNode
from nodes.generation import QueryGeneratorNode, ContentWriterNode, DocumentGeneratorNode
from utils.app_config import AppConfig
from rag_agent import MedicalRAG
from web_search_processor_agent.web_search_agent import WebSearchAgent

# Configure logging
logging.basicConfig(level=logging.INFO)

# Page Config
st.set_page_config(
    page_title="Medical Education Assistant",
    page_icon="🏥",
    layout="wide"
)

# ==================== FLOW DEFINITIONS ====================

def create_interview_flow():
    """
    Create interview flow: Interview → Plan

    Flow returns to interview if more info needed,
    proceeds to plan when requirements complete.
    """
    interviewer = InterviewerNode()
    planner = PlannerNode()

    # Connect: interview loops or proceeds to plan
    interviewer - "ask" >> interviewer  # Loop if more info needed
    interviewer - "done" >> planner     # Proceed when done

    return Flow(start=interviewer)


def create_content_generation_flow():
    """
    Create complete content generation flow:
    Research → Generate Queries → Write Content → Generate Document

    All nodes connected in sequence, fully automated.
    """
    # Create nodes
    researcher = ResearcherNode()
    query_generator = QueryGeneratorNode()
    content_writer = ContentWriterNode()
    doc_generator = DocumentGeneratorNode()

    # Connect nodes in sequence
    researcher >> query_generator >> content_writer >> doc_generator

    # Return async flow (researcher and writer are async)
    return AsyncFlow(start=researcher)


def create_research_flow():
    """
    Create standalone research flow:
    Research → Generate Queries

    Useful for just building knowledge base without content generation.
    """
    researcher = ResearcherNode()
    query_generator = QueryGeneratorNode()

    researcher >> query_generator

    return AsyncFlow(start=researcher)


# ==================== SESSION STATE INIT ====================

if "stage" not in st.session_state:
    st.session_state.stage = "interview"  # interview, plan, executing, done

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "agent", "content": "Xin chào! Tôi là Trợ lý Y khoa AI. Bạn cần tạo tài liệu về chủ đề gì?"}
    ]

if "shared" not in st.session_state:
    with st.spinner("Đang khởi tạo hệ thống..."):
        # Initialize config and agents
        config = AppConfig()
        rag_agent = MedicalRAG(config)
        web_search_agent = WebSearchAgent(config)

        # Shared store for flows
        st.session_state.shared = {
            "chat_history": [],
            "requirements": {},
            "blueprint": [],
            "blueprint_with_queries": [],
            "research_log": [],
            "doc_sections": [],
            "output_file": None,

            # Dependencies for nodes
            "rag_agent": rag_agent,
            "web_search_agent": web_search_agent
        }

# ==================== STAGE 1: INTERVIEW ====================

if st.session_state.stage == "interview":
    st.title("🏥 Trợ lý Y khoa AI - Thu thập yêu cầu")

    # Display chat history
    for msg in st.session_state.messages:
        role = "user" if msg["role"] == "user" else "assistant"
        with st.chat_message(role):
            st.write(msg["content"])

    # User input
    if prompt := st.chat_input("Nhập yêu cầu của bạn..."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.session_state.shared["chat_history"].append({"role": "user", "content": prompt})

        with st.chat_message("user"):
            st.write(prompt)

        # Process with interview flow
        with st.chat_message("assistant"):
            with st.spinner("Đang suy nghĩ..."):
                try:
                    # Create and run interview flow
                    interview_flow = create_interview_flow()
                    interview_flow.run(st.session_state.shared)

                    # Get result
                    result = st.session_state.shared.get("interview_result", {})
                    message = result.get("message", "...")
                    status = result.get("status", "ask")

                    # Display response
                    st.write(message)
                    st.session_state.messages.append({"role": "agent", "content": message})
                    st.session_state.shared["chat_history"].append({"role": "agent", "content": message})

                    # Check if done
                    if status == "done":
                        st.success("✅ Đã hiểu yêu cầu! Chuyển sang lập kế hoạch...")
                        time.sleep(1)
                        st.session_state.stage = "plan"
                        st.rerun()

                except Exception as e:
                    st.error(f"Lỗi: {e}")
                    import traceback
                    st.code(traceback.format_exc())

# ==================== STAGE 2: PLAN ====================

elif st.session_state.stage == "plan":
    st.title("📋 Kế hoạch tài liệu (Blueprint)")

    # Display requirements
    reqs = st.session_state.shared.get("requirements", {})
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📚 Chủ đề", reqs.get('topic', 'N/A'))
    with col2:
        st.metric("👥 Đối tượng", reqs.get('audience', 'N/A'))
    with col3:
        st.metric("🎯 Mục tiêu", len(reqs.get('objectives', '')))

    st.info(f"**Mục tiêu chi tiết:** {reqs.get('objectives', 'N/A')}")

    # Generate blueprint if not exists
    if not st.session_state.shared.get("blueprint"):
        with st.spinner("Đang tạo dàn ý bằng AI..."):
            try:
                # Use planner node directly (single node, no flow needed)
                planner = PlannerNode()
                planner.run(st.session_state.shared)

                if st.session_state.shared.get("blueprint"):
                    st.rerun()
                else:
                    st.warning("Không tạo được dàn ý. Vui lòng thử lại.")

            except Exception as e:
                st.error(f"Lỗi: {e}")

    # Display and edit blueprint
    blueprint = st.session_state.shared.get("blueprint", [])

    if blueprint:
        st.write("### 📝 Dàn ý đề xuất:")

        new_blueprint = []
        for i, item in enumerate(blueprint):
            with st.expander(f"📄 Phần {i+1}: {item.get('title', 'N/A')}", expanded=True):
                title = st.text_input(
                    "Tiêu đề",
                    value=item.get('title', ''),
                    key=f"title_{i}"
                )
                desc = st.text_area(
                    "Mô tả nội dung",
                    value=item.get('description', ''),
                    height=100,
                    key=f"desc_{i}"
                )
                new_blueprint.append({"title": title, "description": desc})

        # AI refinement
        st.write("---")
        st.subheader("🤖 Chỉnh sửa dàn ý bằng AI")

        col_feedback, col_button = st.columns([3, 1])
        with col_feedback:
            feedback = st.text_area(
                "Nhập yêu cầu chỉnh sửa (ví dụ: 'Thêm phần về biến chứng')",
                key="planner_feedback_input",
                height=80
            )
        with col_button:
            st.write("")  # Spacing
            st.write("")  # Spacing
            if st.button("✨ Sửa dàn ý", use_container_width=True):
                if feedback.strip():
                    with st.spinner("Đang cập nhật dàn ý bằng AI..."):
                        st.session_state.shared["blueprint"] = new_blueprint
                        st.session_state.shared["planner_feedback"] = feedback

                        planner = PlannerNode()
                        planner.run(st.session_state.shared)
                        st.rerun()
                else:
                    st.warning("⚠️ Vui lòng nhập yêu cầu chỉnh sửa")

        # Action buttons
        st.write("---")
        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("🔄 Tạo lại dàn ý", use_container_width=True):
                st.session_state.shared["blueprint"] = []
                st.session_state.shared["planner_feedback"] = ""
                st.rerun()

        with col2:
            if st.button("◀️ Quay lại", use_container_width=True):
                st.session_state.stage = "interview"
                st.session_state.shared["blueprint"] = []
                st.rerun()

        with col3:
            if st.button("✅ Xác nhận & Tạo tài liệu", type="primary", use_container_width=True):
                st.session_state.shared["blueprint"] = new_blueprint
                st.session_state.stage = "executing"
                st.rerun()

# ==================== STAGE 3: EXECUTION ====================

elif st.session_state.stage == "executing":
    st.title("⚙️ Đang tạo tài liệu...")

    # Progress indicators
    progress_bar = st.progress(0, text="Bắt đầu...")
    status_container = st.container()

    try:
        # Create content generation flow
        content_flow = create_content_generation_flow()

        # Phase 1: Research
        with status_container:
            st.write("### 🔍 Giai đoạn 1: Nghiên cứu")
            st.info("Đang tìm kiếm thông tin từ PubMed và các nguồn web...")

        progress_bar.progress(10, text="Đang nghiên cứu...")

        # Phase 2: Run complete flow
        with status_container:
            st.write("### 🚀 Đang thực thi quy trình hoàn chỉnh...")

            # Run async flow
            try:
                loop = asyncio.get_running_loop()
                loop.run_until_complete(content_flow.run_async(st.session_state.shared))
            except RuntimeError:
                asyncio.run(content_flow.run_async(st.session_state.shared))

        progress_bar.progress(100, text="Hoàn tất!")

        # Show completion
        with status_container:
            st.success("✅ Tạo tài liệu thành công!")

            # Display research log
            research_log = st.session_state.shared.get("research_log", [])
            if research_log:
                with st.expander(f"📊 Chi tiết nghiên cứu ({len(research_log)} mục)", expanded=False):
                    for i, log in enumerate(research_log, 1):
                        st.write(f"{i}. {log}")

            # Display generated queries
            queries = st.session_state.shared.get("blueprint_with_queries", [])
            if queries:
                with st.expander(f"🔍 Truy vấn được tạo ({len(queries)} mục)", expanded=False):
                    for item in queries:
                        st.write(f"**{item.get('title')}**")
                        st.code(item.get('query', 'N/A'), language="text")

        time.sleep(1)
        st.session_state.stage = "done"
        st.rerun()

    except Exception as e:
        progress_bar.progress(0, text="Lỗi!")
        st.error(f"❌ Lỗi trong quá trình thực thi: {e}")

        with st.expander("📋 Chi tiết lỗi", expanded=True):
            import traceback
            st.code(traceback.format_exc())

        if st.button("🔄 Thử lại"):
            st.rerun()

# ==================== STAGE 4: DONE ====================

elif st.session_state.stage == "done":
    st.title("✅ Hoàn tất!")
    st.balloons()

    # Get results
    filename = st.session_state.shared.get("output_file")
    doc_sections = st.session_state.shared.get("doc_sections", [])
    research_log = st.session_state.shared.get("research_log", [])

    # Statistics
    st.write("### 📊 Thống kê")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("📄 Số phần", len(doc_sections))

    with col2:
        total_subsections = sum(len(sec.get('body', [])) for sec in doc_sections)
        st.metric("📝 Tiểu mục", total_subsections)

    with col3:
        st.metric("🔍 Nguồn", len(research_log))

    with col4:
        if filename and os.path.exists(filename):
            file_size = os.path.getsize(filename) / 1024  # KB
            st.metric("📦 Kích thước", f"{file_size:.1f} KB")

    # Download button
    st.write("### 📥 Tải xuống")
    if filename and os.path.exists(filename):
        with open(filename, "rb") as f:
            st.download_button(
                label="📥 Tải xuống tài liệu (.docx)",
                data=f,
                file_name=os.path.basename(filename),
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True
            )
    else:
        st.warning("⚠️ Không tìm thấy file tài liệu")

    # Preview content
    st.write("### 📖 Xem trước nội dung")

    for i, sec in enumerate(doc_sections, 1):
        with st.expander(f"📄 Phần {i}: {sec.get('title', 'N/A')}", expanded=False):
            for block in sec.get('body', []):
                if block.get('heading'):
                    st.markdown(f"**{block.get('heading')}**")
                if block.get('content'):
                    st.write(block.get('content'))

    # Research details
    if research_log:
        with st.expander(f"🔬 Chi tiết nghiên cứu ({len(research_log)} nguồn)", expanded=False):
            for i, log in enumerate(research_log, 1):
                st.write(f"{i}. {log}")

    # Action buttons
    st.write("---")
    col1, col2 = st.columns(2)

    with col1:
        if st.button("📝 Tạo tài liệu mới", use_container_width=True, type="primary"):
            # Reset all state
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

    with col2:
        if st.button("◀️ Quay lại chỉnh sửa", use_container_width=True):
            st.session_state.stage = "plan"
            st.rerun()

# ==================== SIDEBAR ====================

with st.sidebar:
    st.title("ℹ️ Thông tin")

    st.write(f"**Giai đoạn:** {st.session_state.stage.title()}")

    if st.session_state.shared.get("requirements"):
        st.write("---")
        st.write("**📋 Yêu cầu:**")
        reqs = st.session_state.shared["requirements"]
        st.write(f"- Chủ đề: {reqs.get('topic', 'N/A')}")
        st.write(f"- Đối tượng: {reqs.get('audience', 'N/A')}")

    if st.session_state.shared.get("blueprint"):
        st.write("---")
        st.write(f"**📝 Dàn ý:** {len(st.session_state.shared['blueprint'])} phần")

    st.write("---")
    st.write("**🏗️ Kiến trúc:**")
    st.code("""
Flow-Based
├─ Interview Flow
│  └─ Interview → Plan
├─ Content Flow
│  └─ Research → Query
     → Write → Document
└─ Clean & Modular
    """, language="text")

    st.write("---")
    if st.button("🔄 Reset", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
