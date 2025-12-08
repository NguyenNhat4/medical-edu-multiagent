from pocketflow import Flow
from nodes import InterviewerNode, PlannerNode, ContentGeneratorBatchNode

def create_interview_flow():
    """Flow for gathering requirements (Single turn)."""
    node = InterviewerNode()
    return Flow(start=node)

def create_execution_flow():
    """Flow for planning and generating content."""
    planner = PlannerNode()
    generator = ContentGeneratorBatchNode()
    
    # Connect Planner to Generator
    planner >> generator
    
    return Flow(start=planner)
