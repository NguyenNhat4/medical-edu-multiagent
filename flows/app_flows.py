from pocketflow import Flow, AsyncFlow
from nodes import InterviewerNode, PlannerNode, ResearcherNode, ContentWriterNode, DocGeneratorNode

def create_interview_flow():
    """
    Creates a flow for the interview stage.
    Interact with the user to gather requirements.
    """
    interviewer = InterviewerNode()

    # Simple flow: Interviewer -> (user feedback via loop in app) -> Done
    # The actual looping logic happens in app.py via st.rerun based on status
    # But we can model the decision point here.

    # We just return the node wrapped in a Flow for consistency
    return Flow(start=interviewer)

def create_planning_flow():
    """
    Creates a flow for the planning stage.
    Generates a blueprint based on requirements.
    """
    planner = PlannerNode()
    return Flow(start=planner)

def create_execution_flow():
    """
    Creates the main execution flow:
    Research -> Ingest -> Write -> Generate Doc

    This matches the user's pipeline:
    "research from pubmed -> chunk -> ingest to qdrant -> rerank most relelance document -> syntisize -> and actually create word document"
    """

    # 1. Research & Ingest (Parallel for all blueprint items)
    # ResearcherNode handles: Query Gen -> Search (Pubmed/Web) -> Ingest to Qdrant
    researcher = ResearcherNode()

    # 2. Synthesize Content (Parallel for all blueprint items)
    # ContentWriterNode handles: Retrieve (Rerank) -> Synthesize (Write)
    content_writer = ContentWriterNode()

    # 3. Create Document
    # DocGeneratorNode handles: Assembly of sections -> Word Doc
    doc_generator = DocGeneratorNode()

    # Connect them
    researcher >> content_writer >> doc_generator

    return AsyncFlow(start=researcher)
