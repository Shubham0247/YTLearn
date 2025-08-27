import streamlit as st
from graph.workflow import create_workflow
from state.app_state import YouTubeVideoState
from nodes.generate_quiz_node import generate_quiz_node
import asyncio
import os

def _inject_global_styles():
    """Inject global CSS for a modern, clean UI."""
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
        html, body, [class*="css"]  {
            font-family: 'Inter', system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif;
        }
        .app-title {
            font-size: 2rem;
            font-weight: 700;
            margin: 0.2rem 0 1rem 0;
            background: linear-gradient(90deg, #2563eb 0%, #10b981 50%, #f59e0b 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .card {
            background: #ffffff;
            border: 1px solid rgba(0,0,0,0.06);
            border-radius: 12px;
            padding: 1rem 1.25rem;
            margin: 0.5rem 0 1rem 0;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
            transition: box-shadow 200ms ease;
        }
        .card:hover { box-shadow: 0 6px 18px rgba(0,0,0,0.08); }
        .summary-card { line-height: 1.6; font-size: 1.02rem; }
        .stButton>button {
            background: linear-gradient(90deg, #2563eb 0%, #10b981 100%);
            color: white;
            border: 0;
            padding: 0.6rem 1rem;
            border-radius: 8px;
            font-weight: 600;
            transition: transform 120ms ease, box-shadow 120ms ease;
        }
        .stButton>button:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(37, 99, 235, 0.25); }
        .stTabs [data-baseweb="tab-list"] { gap: 6px; }
        .stTabs [data-baseweb="tab"] { border-radius: 10px; padding: 8px 12px; background: rgba(37, 99, 235, 0.08); }
        .stTabs [aria-selected="true"] { background: rgba(16, 185, 129, 0.15); }
        </style>
        """,
        unsafe_allow_html=True,
    )

def main():
    st.set_page_config(page_title="YTLearn", page_icon="🎓", layout="wide")
    _inject_global_styles()
    st.markdown("<div class='app-title'>🎓 YTLearn — YouTube Video Learning Assistant</div>", unsafe_allow_html=True)
    
    # Initialize session state
    if "video_url" not in st.session_state:
        st.session_state.video_url = ""
    if "results" not in st.session_state:
        st.session_state.results = None
    if "quiz_started" not in st.session_state:
        st.session_state.quiz_started = False
    if "user_answers" not in st.session_state:
        st.session_state.user_answers = {}
    if "processing" not in st.session_state:
        st.session_state.processing = False
    if "error" not in st.session_state:
        st.session_state.error = ""
    if "attempted_quiz_generation" not in st.session_state:
        st.session_state.attempted_quiz_generation = False
    if "llm_provider" not in st.session_state:
        st.session_state.llm_provider = "Groq"
    if "api_key" not in st.session_state:
        st.session_state.api_key = ""
    # Display app description
    with st.container():
        st.markdown("""
        YTLearn helps you learn from YouTube videos by:
        - Generating concise summaries
        - Extracting key points
        - Creating interactive quizzes
        - Finding related educational resources
        
        **Note:** The video must have captions/subtitles available.
        """)
    
    # Provider and API key inputs
    providers = ["OpenAI", "Hugging Face", "Groq"]
    default_index = providers.index(st.session_state.llm_provider) if st.session_state.llm_provider in providers else 2
    provider = st.selectbox("Select LLM Provider", providers, index=default_index)
    st.session_state.llm_provider = provider

    key_placeholder = "sk-..." if provider == "OpenAI" else ("hf_..." if provider == "Hugging Face" else "gsk_...")
    api_key = st.text_input(
        f"Enter your {provider} API Key:",
        type="password",
        help="Your key is used only in your session and not stored on the server.",
        placeholder=key_placeholder,
        value=st.session_state.api_key,
    )
    st.session_state.api_key = api_key

    # Input for YouTube URL
    video_url = st.text_input(
        "Enter YouTube Video URL:",
        value=st.session_state.video_url,
        help="Paste a YouTube URL. The video must have captions available.",
        placeholder="https://www.youtube.com/watch?v=...",
    )
    
    col1, col2 = st.columns([1, 5])
    with col1:
        process_button = st.button("Process Video", type="primary")
    
    if process_button or (video_url != st.session_state.video_url and video_url != ""):
        if video_url:
            if not (api_key and api_key.strip()):
                st.warning("Please enter your API key to proceed.")
                return
            if provider == "Hugging Face" and not api_key.strip().startswith("hf_"):
                st.warning("Hugging Face tokens must start with 'hf_'. Please paste a valid token with API Inference 'Read' permission.")
                return
            st.session_state.video_url = video_url
            st.session_state.results = None
            st.session_state.quiz_started = False
            st.session_state.user_answers = {}
            st.session_state.processing = True
            st.session_state.error = ""
            
            try:
                with st.spinner("Processing video and generating content... This may take a minute."):
                    # Create workflow
                    app = create_workflow()
                    
                    # Initial state
                    initial_state = YouTubeVideoState(
                        video_url=video_url,
                        llm_provider=provider.lower(),
                        api_key=api_key.strip(),
                        groq_api_key="",
                        video_title="",
                        video_transcript="",
                        summary="",
                        key_points=[],
                        quiz_questions=[],
                        related_resources=[],
                        current_question_index=0,
                        user_answers={},
                        quiz_score=0,
                        error=""
                    )
                    
                    # Run the workflow
                    results = app.invoke(initial_state)
                    st.session_state.results = results
                    st.session_state.processing = False
                    
                    # Check for errors
                    if results.get("error"):
                        st.session_state.error = results["error"]
                        st.error(results["error"])
                    
            except Exception as e:
                st.session_state.processing = False
                st.session_state.error = f"Error processing video: {str(e)}"
                st.error(st.session_state.error)
        else:
            st.warning("Please enter a YouTube URL")
    
    # Display results if available
    if st.session_state.results:
        display_results(st.session_state.results)
        
    # We don't need this section anymore as quiz is displayed in the tabs


def display_results(results):
    """Display the video summary and key points."""
    # Check for errors first
    if results.get("error"):
        st.error(results["error"])
        return
    
    # Display video title if available
    if results.get("video_title"):
        st.subheader(f"📺 {results['video_title']}")
    
    # Display tabs for different sections
    tab1, tab2, tab3 = st.tabs(["📋 Summary & Key Points", "📚 Related Resources", "❓ Quiz"])
    
    with tab1:
        st.subheader("📋 Video Summary")
        if results.get("summary"):
            st.markdown(f"<div class='card summary-card'>{results['summary']}</div>", unsafe_allow_html=True)
        else:
            st.info("Summary not available.")
        
        st.subheader("🔑 Key Points")
        if results.get("key_points") and len(results["key_points"]) > 0:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            for i, point in enumerate(results["key_points"], 1):
                st.markdown(f"- {point}")
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.info("Key points not available.")
    
    with tab2:
        st.subheader("📚 Related Resources")
        if results.get("related_resources") and len(results["related_resources"]) > 0:
            for i, resource in enumerate(results["related_resources"], 1):
                with st.expander(f"{i}. {resource.get('title', 'Untitled')}"):
                    st.markdown(f"**Source**: [{resource.get('title', 'Untitled')}]({resource.get('url', '#')})")
                    st.markdown(f"**Content**: {resource.get('content', 'No content available')}")
        else:
            st.info("No related resources found for this video.")
    
    with tab3:
        st.subheader("❓ Quiz")
        # Attempt on-demand generation if quiz is missing but transcript is available
        if (not results.get("quiz_questions")) and results.get("video_transcript") and not st.session_state.attempted_quiz_generation:
            with st.spinner("Generating quiz questions..."):
                regen_state = YouTubeVideoState(
                    video_url=st.session_state.video_url,
                    llm_provider=st.session_state.llm_provider.lower(),
                    api_key=st.session_state.api_key,
                    groq_api_key="",
                    video_title=results.get('video_title', ''),
                    video_transcript=results.get('video_transcript', ''),
                    summary=results.get('summary', ''),
                    key_points=results.get('key_points', []),
                    quiz_questions=[],
                    related_resources=results.get('related_resources', []),
                    current_question_index=0,
                    user_answers={},
                    quiz_score=0,
                    error=results.get('error', ''),
                )
                regen = generate_quiz_node(regen_state)
                if regen.get('quiz_questions'):
                    st.session_state.results['quiz_questions'] = regen['quiz_questions']
                elif regen.get('error'):
                    st.error(regen['error'])
                st.session_state.attempted_quiz_generation = True
                st.rerun()

        if results.get("quiz_questions") and len(results["quiz_questions"]) > 0:
            if not st.session_state.quiz_started:
                st.write("Test your knowledge with a quiz based on the video content.")
                if st.button("Start Quiz", type="primary"):
                    st.session_state.quiz_started = True
                    # Initialize quiz state
                    st.session_state.current_question = 0
                    st.session_state.score = 0
                    st.session_state.quiz_completed = False
                    st.session_state.feedback = ""
                    st.session_state.user_answers = {}
                    st.rerun()
            else:
                # Call the display_quiz function to show the quiz
                display_quiz(results)
        else:
            st.info("Quiz not available. Try generating again.")
            if st.button("Generate Quiz Now"):
                with st.spinner("Generating quiz questions..."):
                    regen_state = YouTubeVideoState(
                        video_url=st.session_state.video_url,
                        llm_provider=st.session_state.llm_provider.lower(),
                        api_key=st.session_state.api_key,
                        groq_api_key="",
                        video_title=results.get('video_title', ''),
                        video_transcript=results.get('video_transcript', ''),
                        summary=results.get('summary', ''),
                        key_points=results.get('key_points', []),
                        quiz_questions=[],
                        related_resources=results.get('related_resources', []),
                        current_question_index=0,
                        user_answers={},
                        quiz_score=0,
                        error=results.get('error', ''),
                    )
                    regen = generate_quiz_node(regen_state)
                    if regen.get('quiz_questions'):
                        st.session_state.results['quiz_questions'] = regen['quiz_questions']
                        st.session_state.attempted_quiz_generation = True
                        st.rerun()
                    elif regen.get('error'):
                        st.error(regen['error'])


def display_quiz(results):
    """Display the quiz and handle user answers."""
    # Skip if there are no quiz questions
    if not results.get("quiz_questions") or len(results["quiz_questions"]) == 0:
        return
    
    # Skip if quiz hasn't started (handled in the tabs now)
    if not st.session_state.quiz_started:
        return
        
    # Initialize quiz state if needed
    if "current_question" not in st.session_state:
        st.session_state.current_question = 0
    if "score" not in st.session_state:
        st.session_state.score = 0
    if "quiz_completed" not in st.session_state:
        st.session_state.quiz_completed = False
    if "feedback" not in st.session_state:
        st.session_state.feedback = ""
    
    # Display quiz completion screen if quiz is done
    if st.session_state.quiz_completed:
        st.success(f"Quiz completed! Your score: {st.session_state.score}/{len(results['quiz_questions'])}")
        colA, colB = st.columns([1,1])
        with colA:
            if st.button("Restart Quiz (New Questions)"):
                # Regenerate a completely new quiz set using current transcript
                transcript = results.get('video_transcript') or st.session_state.results.get('video_transcript', '')
                regen_state = YouTubeVideoState(
                    video_url=st.session_state.video_url,
                    llm_provider=st.session_state.llm_provider.lower(),
                    api_key=st.session_state.api_key,
                    groq_api_key="",
                    video_title=results.get('video_title', ''),
                    video_transcript=transcript,
                    summary=results.get('summary', ''),
                    key_points=results.get('key_points', []),
                    quiz_questions=results.get('quiz_questions', []),
                    related_resources=results.get('related_resources', []),
                    current_question_index=0,
                    user_answers={},
                    quiz_score=0,
                    error=results.get('error', ''),
                )
                regen = generate_quiz_node(regen_state)
                if regen.get('quiz_questions'):
                    st.session_state.results['quiz_questions'] = regen['quiz_questions']
                # Reset quiz state
                st.session_state.current_question = 0
                st.session_state.score = 0
                st.session_state.quiz_completed = False
                st.session_state.feedback = ""
                st.session_state.user_answers = {}
                if 'answer_submitted' in st.session_state:
                    del st.session_state['answer_submitted']
                st.rerun()
        with colB:
            if st.button("Review Questions"):
                st.session_state.quiz_completed = False
                st.session_state.current_question = 0
                st.rerun()
        return
    
    # Get current question
    questions = results["quiz_questions"]
    if st.session_state.current_question >= len(questions):
        st.session_state.quiz_completed = True
        st.rerun()
        return
    
    current_q = questions[st.session_state.current_question]
    
    # Display question
    st.subheader(f"Question {st.session_state.current_question + 1} of {len(questions)}")
    st.write(current_q.get("question", "No question available"))
    
    # Display options
    options = current_q.get("options", [])
    correct_text = current_q.get("correct_text", None)
    correct_index = current_q.get("correct_index", None)
    
    # Create a unique key for this question
    q_key = f"q_{st.session_state.current_question}"
    
    # Display radio buttons for options (use indices to avoid string-equality pitfalls)
    option_indices = list(range(len(options)))
    user_choice_index = st.radio(
        "Select your answer:",
        option_indices,
        format_func=lambda i: options[i],
        key=q_key,
    )
    
    # Check answer button
    col1, col2 = st.columns([1, 5])
    with col1:
        if st.button("Submit Answer", key=f"submit_{st.session_state.current_question}"):
            # Store user's answer
            st.session_state.user_answers[st.session_state.current_question] = user_choice_index
            
            # Check if answer is correct
            # Ensure we have a valid correct_index; if missing, derive from correct_text
            if (correct_index is None or not isinstance(correct_index, int) or not (0 <= correct_index < len(options))) and isinstance(correct_text, str):
                try:
                    correct_index = options.index(correct_text)
                except ValueError:
                    correct_index = None

            is_correct = isinstance(user_choice_index, int) and isinstance(correct_index, int) and user_choice_index == correct_index

            if is_correct:
                st.session_state.score += 1
                st.session_state.feedback = "✅ Correct!"
            else:
                # Compute friendly correct label
                friendly_correct = (
                    options[correct_index]
                    if isinstance(correct_index, int) and 0 <= correct_index < len(options)
                    else (correct_text if isinstance(correct_text, str) else "(unavailable)")
                )
                st.session_state.feedback = f"❌ Incorrect. Correct answer: {friendly_correct}"
            
            # Show next question button
            st.session_state.answer_submitted = True
            st.rerun()
    
    # Display feedback if answer was submitted
    if "answer_submitted" in st.session_state and st.session_state.answer_submitted:
        st.markdown(f"**{st.session_state.feedback}**")
        
        # Next question button
        if st.button("Next Question", key=f"next_{st.session_state.current_question}"):
            st.session_state.current_question += 1
            st.session_state.feedback = ""
            if "answer_submitted" in st.session_state:
                del st.session_state.answer_submitted
            st.rerun()
    # This is the end of the display_quiz function

if __name__ == "__main__":
    main()