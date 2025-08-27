from typing import Dict, Any
from tools.youtube_tool import get_video_title, get_video_transcript
from state.app_state import YouTubeVideoState


def process_video_node(state: YouTubeVideoState) -> Dict[str, Any]:
    """Process the YouTube video and extract title and transcript with improved error handling."""
    try:
        video_url = state["video_url"]
        
        if not video_url or not video_url.strip():
            return {"error": "Please provide a valid YouTube URL"}
        
        # Validate YouTube URL format
        if not ("youtube.com" in video_url or "youtu.be" in video_url):
            return {"error": "Please provide a valid YouTube URL (youtube.com or youtu.be)"}
        
        video_title = None
        video_transcript = None
        errors = []
        
        # Get video title with fallback
        try:
            video_title = get_video_title(video_url)

        except Exception as title_error:
            error_msg = f"Could not retrieve video title: {str(title_error)}"
            errors.append(error_msg)

            # Continue processing - we can still get transcript without title
        
        # Get video transcript with detailed error reporting
        try:
            video_transcript = get_video_transcript(video_url)
            if not (video_transcript and len(video_transcript.strip()) >= 10):
                error_msg = "Retrieved transcript is too short or empty"
                errors.append(error_msg)
    
        except Exception as transcript_error:
            error_msg = f"Could not retrieve transcript: {str(transcript_error)}"
            errors.append(error_msg)

        
        # Determine if we have enough data to proceed
        if not video_transcript or len(video_transcript.strip()) < 10:
            if errors:
                return {"error": f"Failed to process video. Issues encountered: {'; '.join(errors)}. The video might not have captions available or may be private/restricted."}
            else:
                return {"error": "Could not retrieve a valid transcript from this video. The video might not have captions available."}
        
        # If we don't have a title but have transcript, use a fallback title
        if not video_title:
            try:
                from tools.youtube_tool import extract_video_id
                video_id = extract_video_id(video_url)
                video_title = f"YouTube Video ({video_id})"
            except:
                video_title = "YouTube Video"
        
        result = {
            "video_title": video_title,
            "video_transcript": video_transcript
        }
        
        # Add warnings if there were non-critical errors
        if errors and video_transcript:
            result["warnings"] = errors
        
        return result
        
    except Exception as e:
        return {"error": f"Unexpected error processing video: {str(e)}. Please check if the URL is valid and the video is publicly accessible."}