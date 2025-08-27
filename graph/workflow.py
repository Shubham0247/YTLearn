from langgraph.graph import StateGraph, END
from state.app_state import YouTubeVideoState
from nodes.process_video_node import process_video_node
from nodes.generate_summary_node import generate_summary_node
from nodes.generate_quiz_node import generate_quiz_node
from nodes.generate_resources_node import generate_resources_node

def create_workflow():
    """Create and return the LangGraph workflow."""
    # Define the workflow
    workflow = StateGraph(YouTubeVideoState)
    
    # Add nodes
    workflow.add_node("process_video", process_video_node)
    workflow.add_node("generate_summary", generate_summary_node)
    workflow.add_node("generate_quiz", generate_quiz_node)
    workflow.add_node("generate_resources", generate_resources_node)
    
    # Add edges
    workflow.add_edge("process_video", "generate_summary")
    workflow.add_edge("generate_summary", "generate_quiz")
    workflow.add_edge("generate_summary", "generate_resources")
    
    # Set entry point
    workflow.set_entry_point("process_video")
    
    # Compile the workflow
    app = workflow.compile()
    
    return app