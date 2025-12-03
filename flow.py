from pocketflow import Flow
from nodes import InterviewerNode, PlannerNode, RefinerNode, ContentGeneratorBatchNode

def create_medical_agent_flow():
    interviewer = InterviewerNode()
    planner = PlannerNode()
    refiner = RefinerNode()
    generator = ContentGeneratorBatchNode()
    
    # Connections
    interviewer >> planner
    planner >> refiner
    
    # Branching
    refiner - "revise" >> planner
    refiner - "approved" >> generator

    return Flow(start=interviewer)
