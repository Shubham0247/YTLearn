from typing import List, Dict, TypedDict
from langgraph.graph import MessagesState

class YouTubeVideoState(MessagesState):
    video_url: str
    # LLM provider and runtime key for Streamlit Cloud usage
    llm_provider: str
    api_key: str
    # Backward-compat (will be ignored if api_key is present)
    groq_api_key: str
    video_title: str
    video_transcript: str
    summary: str
    key_points: List[str]
    quiz_questions: List[Dict]
    related_resources: List[Dict]
    current_question_index: int
    user_answers: Dict[int, str]
    quiz_score: int
    error: str