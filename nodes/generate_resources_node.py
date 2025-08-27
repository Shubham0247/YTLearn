from typing import Dict, Any, List
from tools.search_tool import search_related_resources
from state.app_state import YouTubeVideoState


def generate_resources_node(state: YouTubeVideoState) -> Dict[str, Any]:
    """Generate related resources based on video content."""
    try:
        # Use video title as the search topic
        topic = state.get("video_title", "")
        if not topic:
            topic = state.get("video_transcript", "")[:100]  # Use first 100 characters of transcript if title is not available
        
        # Search for related resources
        resources = search_related_resources(topic)
        
        return {
            "related_resources": resources
        }
    except Exception as e:
        return {"error": f"Error generating resources: {str(e)}"}