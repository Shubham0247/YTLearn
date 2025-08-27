import os
from typing import Optional
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from langchain_huggingface import HuggingFaceEndpoint

load_dotenv()

def get_llm(*, model: Optional[str] = None, temperature: Optional[float] = None, max_tokens: Optional[int] = None, api_key: Optional[str] = None, provider: Optional[str] = None):
    """Initialize and return a configured chat LLM for the selected provider.

    Parameters
    ----------
    model: Optional[str]
        Optional model name override. Defaults to "qwen/qwen3-32b".
    temperature: Optional[float]
        Optional temperature override. Defaults to 0.7.
    max_tokens: Optional[int]
        Optional max_tokens override. Defaults to 2048.
    """
    try:
        chosen = (provider or os.getenv("LLM_PROVIDER") or "groq").strip().lower()
        # Normalize common variants (e.g., "hugging face" → "huggingface")
        chosen = chosen.replace(" ", "").replace("-", "").replace("_", "")
        resolved_model = model or (
            "gpt-4o-mini" if chosen == "openai" else
            "Qwen/Qwen3-8B" if chosen == "huggingface" else
            "qwen/qwen3-32b"
        )
        resolved_temperature = 0.7 if temperature is None else float(temperature)
        resolved_max_tokens = 2048 if max_tokens is None else int(max_tokens)

        if chosen == "openai":
            key = api_key or os.getenv("OPENAI_API_KEY")
            if not key:
                raise ValueError("OPENAI_API_KEY not found. Provide it in the UI or environment.")
            return ChatOpenAI(
                model=resolved_model,
                api_key=key,
                temperature=resolved_temperature,
                max_tokens=resolved_max_tokens,
            )
        elif chosen in ("huggingface", "hf"):
            key = api_key or os.getenv("HUGGINGFACEHUB_API_TOKEN")
            if not key:
                raise ValueError("HUGGINGFACEHUB_API_TOKEN not found. Provide it in the UI or environment.")
            if not key.startswith("hf_"):
                raise ValueError("Invalid Hugging Face token format. It should start with 'hf_'.")
            return HuggingFaceEndpoint(
                repo_id=resolved_model,
                task="text-generation",
                huggingfacehub_api_token=key,
                temperature=resolved_temperature,
                max_new_tokens=resolved_max_tokens,
            )
        else:  # groq default
            key = api_key or os.getenv("GROQ_API_KEY")
            if not key:
                raise ValueError("GROQ_API_KEY not found. Provide it in the UI or environment.")
            return ChatGroq(
                model=resolved_model,
                groq_api_key=key,
                temperature=resolved_temperature,
                max_tokens=resolved_max_tokens,
            )
    except Exception as e:
        raise Exception(f"Error initializing LLM: {str(e)}")