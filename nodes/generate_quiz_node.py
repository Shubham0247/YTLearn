from typing import Dict, Any, List
import random
import re
import json
from llm.llm_config import get_llm
from state.app_state import YouTubeVideoState


def _extract_answer_index(answer_text: str) -> int:
    """Map answer like 'A' or 'A.' or 'Option A' to index 0..3. Returns -1 if unknown."""
    if not answer_text:
        return -1
    match = re.search(r"[A-D]", answer_text.upper())
    if not match:
        return -1
    letter = match.group(0)
    return {"A": 0, "B": 1, "C": 2, "D": 3}.get(letter, -1)


def generate_quiz_node(state: YouTubeVideoState) -> Dict[str, Any]:
    """Generate a dynamic MCQ quiz from video transcript with robust parsing and correct answer tagging.

    Strategy:
    1) Ask for strict JSON first for reliability.
    2) If JSON fails or yields no items, fall back to line-based parser.
    """
    try:
        # Lower temperature for more deterministic structure; include variation token to diversify across runs
        variation_token = str(random.randint(1, 10**9))
        provider = state.get("llm_provider") or "groq"
        api_key = state.get("api_key") or state.get("groq_api_key")
        llm = get_llm(temperature=0.4, api_key=api_key, provider=provider)

        transcript = state['video_transcript'][:12000]

        # 1) JSON-first prompt
        json_prompt = f"""
You are generating a quiz STRICTLY from the transcript. Return ONLY JSON, no extra text.

Schema:
{{
  "questions": [
    {{
      "question": "string",
      "options": ["string","string","string","string"],
      "answer_index": 0-3
    }}
  ]
}}

Rules:
- 10 questions total, each with 4 options, exactly one correct.
- No trick questions, no "All of the above".
- Use only transcript facts; be unambiguous.
- Vary phrasing across runs via VARIATION_TOKEN.

VARIATION_TOKEN: {variation_token}

Transcript:
{transcript}
"""

        json_resp = llm.invoke(json_prompt)
        json_text = json_resp.content if hasattr(json_resp, 'content') else str(json_resp)

        def try_parse_json(text: str) -> List[Dict[str, Any]]:
            try:
                data = json.loads(text)
            except Exception:
                # Attempt to extract first {...} or [...] block
                m = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", text)
                if not m:
                    return []
                try:
                    data = json.loads(m.group(1))
                except Exception:
                    return []
            if isinstance(data, list):
                items = data
            elif isinstance(data, dict):
                items = data.get('questions') or data.get('quiz') or []
            else:
                return []
            normalized: List[Dict[str, Any]] = []
            for item in items:
                if not isinstance(item, dict):
                    continue
                q_text = str(item.get('question', '')).strip()
                opts = item.get('options', [])
                ans_idx = item.get('answer_index')
                if not q_text or not isinstance(opts, list) or len(opts) != 4:
                    continue
                try:
                    ans_idx = int(ans_idx)
                except Exception:
                    continue
                if not (0 <= ans_idx < 4):
                    continue
                normalized.append({
                    'question': q_text,
                    'options': [str(o).strip() for o in opts][:4],
                    'correct_index': ans_idx,
                    'correct_text': str(opts[ans_idx]).strip(),
                })
            return normalized

        normalized_questions: List[Dict[str, Any]] = try_parse_json(json_text)

        # 2) Fallback to line-based parsing if JSON yielded nothing
        if not normalized_questions:
            # Generate quiz questions in line format
            quiz_prompt = f"""Create 10 concept-check multiple-choice questions (MCQs) strictly from this transcript. Vary phrasing across different VARIATION_TOKENs.

Transcript (truncate if needed):
{transcript}

Format each item exactly as:
Question 1: <question text>
A. <option A>
B. <option B>
C. <option C>
D. <option D>
Answer: <one letter A-D>

Rules:
- Questions must be unambiguous and based only on the transcript.
- Options should be plausible; only one correct answer.
- Avoid "All of the above"; avoid negation traps.

VARIATION_TOKEN: {variation_token}
"""

            quiz_response = llm.invoke(quiz_prompt)
            quiz_content = quiz_response.content if hasattr(quiz_response, 'content') else str(quiz_response)

            # Parse quiz questions (line-based)
            questions: List[Dict[str, Any]] = []
            current_question: Dict[str, Any] = {}

            for raw_line in quiz_content.split('\n'):
                line = raw_line.strip()
                if not line:
                    continue
                if line.startswith('Question') or re.match(r'^(Q\d+|\d+[\).:])', line):
                    if current_question:
                        questions.append(current_question)
                    q_text = line.split(':', 1)[1].strip() if ':' in line else re.sub(r'^(Q\d+|\d+[\).:])\s*', '', line)
                    current_question = {
                        'question': q_text,
                        'options': [],
                        'answer': ''
                    }
                elif re.match(r'^[ABCD][\).]', line):
                    option_text = re.split(r'[\).]', line, 1)[1].strip()
                    if 'options' in current_question:
                        current_question['options'].append(option_text)
                elif line.lower().startswith('answer'):
                    current_question['answer'] = line.split(':', 1)[1].strip() if ':' in line else ''

            # Add the last question
            if current_question:
                questions.append(current_question)

            # Normalize, compute correct indices, and optionally shuffle options per question
            for q in questions:
                options = q.get('options', [])
                if not isinstance(options, list) or len(options) < 4:
                    continue
                options = options[:4]
                answer_index = _extract_answer_index(q.get('answer', ''))
                if answer_index == -1 and q.get('answer') in options:
                    answer_index = options.index(q['answer'])
                if answer_index < 0 or answer_index >= len(options):
                    continue
                indexed_options = list(enumerate(options))
                random.shuffle(indexed_options)
                new_options = [text for _, text in indexed_options]
                new_correct_index = next(i for i, (old_idx, _) in enumerate(indexed_options) if old_idx == answer_index)
                normalized_questions.append({
                    'question': q.get('question', 'Question').strip(),
                    'options': new_options,
                    'correct_index': new_correct_index,
                    'correct_text': new_options[new_correct_index],
                })

        # If more than 10 questions parsed, sample 10
        if len(normalized_questions) > 10:
            normalized_questions = random.sample(normalized_questions, 10)

        return {
            "quiz_questions": normalized_questions,
            "current_question_index": 0,
            "user_answers": {},
            "quiz_score": 0
        }
    except Exception as e:
        return {"error": f"Error generating quiz: {str(e)}"}