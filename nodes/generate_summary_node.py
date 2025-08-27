from typing import Dict, Any, List
import json
import re
from llm.llm_config import get_llm
from state.app_state import YouTubeVideoState


def _safe_json_extract(text: str) -> Dict[str, Any]:
    """Attempt to extract a JSON object from arbitrary LLM text output."""
    try:
        return json.loads(text)
    except Exception:
        pass
    # Try to find the first {...} block
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            return {}
    return {}


def generate_summary_node(state: YouTubeVideoState) -> Dict[str, Any]:
    """Generate a structured summary and key points from the video transcript."""
    try:
        provider = state.get("llm_provider") or "groq"
        api_key = state.get("api_key") or state.get("groq_api_key")
        llm = get_llm(temperature=0.3, api_key=api_key, provider=provider)

        transcript_excerpt = state["video_transcript"][:8000]

        prompt = f"""
You are a precise summarizer. Given a YouTube video transcript, produce a clear, strictly relevant summary followed by concise key points.

Return ONLY valid JSON with this schema:
{{
  "summary": "3-7 crisp sentences that explain the video clearly in plain language. Avoid fluff and speculation. Use only information present in the transcript.",
  "key_points": ["5-7 short bullets, each one sentence and highly informative"]
}}

Rules:
- Do not include information that is not present in the transcript.
- No marketing tone, no opinions, no repetition.
- Prefer simple sentences and concrete wording.
- If something is unknown from the transcript, omit it instead of guessing.

Transcript:
"""
        prompt += transcript_excerpt

        response = llm.invoke(prompt)
        content = response.content if hasattr(response, "content") else str(response)
        data = _safe_json_extract(content)

        summary_text = ""
        key_points_list: List[str] = []

        if isinstance(data, dict):
            summary_text = str(data.get("summary", "")).strip()
            key_points_raw = data.get("key_points", [])
            if isinstance(key_points_raw, list):
                key_points_list = [str(p).strip(" -•\t").strip() for p in key_points_raw if str(p).strip()]

        # Fallbacks if parsing failed
        if not summary_text:
            summary_fallback_prompt = f"Summarize clearly in 5-7 sentences, strictly based on this transcript:\n\n{transcript_excerpt}\n\nSummary:"
            summary_resp = llm.invoke(summary_fallback_prompt)
            summary_text = summary_resp.content if hasattr(summary_resp, "content") else str(summary_resp)

        if not key_points_list:
            kp_fallback_prompt = f"Extract 5-7 concise, highly informative bullet points from this transcript. One sentence each.\n\n{transcript_excerpt}\n\nBullets:"
            kp_resp = llm.invoke(kp_fallback_prompt)
            kp_text = kp_resp.content if hasattr(kp_resp, "content") else str(kp_resp)
            key_points_list = [
                line.strip(" -•\t").strip()
                for line in kp_text.split("\n")
                if line.strip()
            ][:7]

        # Trim to safe sizes
        key_points_list = key_points_list[:7]

        return {
            "summary": summary_text.strip(),
            "key_points": key_points_list,
        }
    except Exception as e:
        return {"error": f"Error generating summary: {str(e)}"}