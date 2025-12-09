from pocketflow import Flow
from nodes import InterviewerNode, PlannerNode, ResearcherNode, ContentWriterNode, DocGeneratorNode

def create_medical_agent_flow():
    interviewer = InterviewerNode()
    planner = PlannerNode()
    researcher = ResearcherNode()
    writer = ContentWriterNode()
    generator = DocGeneratorNode()
    
    # Define the sequence
    # Note: Logic for transitions (ask/done) is usually handled by the orchestrator (app.py)
    # or via Action returns.
    # Here we define the linear content generation flow.
    
    planner >> researcher
    researcher >> writer
    writer >> generator

    # We return a flow starting from Planner, assuming requirements are gathered.
    return Flow(start=planner)
