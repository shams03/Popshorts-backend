# LLM wrappers: Gemini primary, Groq (Llama) fallback for structured JSON

from pydantic import BaseModel
from google import genai
from dotenv import load_dotenv
import os
import json

load_dotenv()

# Prefer GEMINI_API_KEY (project .env); fall back to GOOGLE_API_KEY
_api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

# gemini-2.5-flash is blocked for many new API keys; override via GEMINI_MODEL if needed
DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")

# Groq fallback (text LLM only — not used for images)
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "auto").lower()  # auto | gemini | groq

client = genai.Client(api_key=_api_key) if _api_key else None

_groq_client = None


def _get_groq_client():
    global _groq_client
    if _groq_client is not None:
        return _groq_client
    if not GROQ_API_KEY:
        return None
    try:
        from groq import Groq
        _groq_client = Groq(api_key=GROQ_API_KEY)
        return _groq_client
    except Exception as e:
        print(f"⚠️  Groq client unavailable: {e}")
        return None


def llm_query(prompt: str) -> str:
    """Simple text generation (Gemini → Groq fallback)."""
    if LLM_PROVIDER != "groq" and client is not None:
        try:
            response = client.models.generate_content(
                model=DEFAULT_MODEL,
                contents=prompt,
            )
            print(response.text)
            return response.text
        except Exception as e:
            print(f"⚠️  Gemini llm_query failed: {e}")
            if LLM_PROVIDER == "gemini":
                raise

    groq = _get_groq_client()
    if groq is None:
        raise RuntimeError("No LLM available. Set GEMINI_API_KEY and/or GROQ_API_KEY.")

    completion = groq.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )
    text = completion.choices[0].message.content
    print(text)
    return text


def _llm_structured_gemini(prompt: str, output_model: BaseModel, model: str):
    if client is None:
        raise RuntimeError("GEMINI_API_KEY not set")
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_json_schema": output_model.model_json_schema(),
        },
    )
    return output_model.model_validate_json(response.text)


def _llm_structured_groq(prompt: str, output_model: BaseModel):
    groq = _get_groq_client()
    if groq is None:
        raise RuntimeError("GROQ_API_KEY not set or groq package missing")

    schema = output_model.model_json_schema()
    system = (
        "You are a JSON API. Return ONLY valid JSON matching this schema. "
        "No markdown fences, no commentary.\n\n"
        f"JSON Schema:\n{json.dumps(schema)}"
    )
    completion = groq.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        response_format={"type": "json_object"},
    )
    text = completion.choices[0].message.content
    return output_model.model_validate_json(text)


def llm_structured(
    prompt: str,
    output_model: BaseModel,
    model: str = None,
):
    """
    Structured JSON output.
    Provider order when LLM_PROVIDER=auto: Gemini first, then Groq (Llama).
    """
    model = model or DEFAULT_MODEL
    errors = []

    use_gemini = LLM_PROVIDER in ("auto", "gemini")
    use_groq = LLM_PROVIDER in ("auto", "groq")

    if use_gemini:
        try:
            result = _llm_structured_gemini(prompt, output_model, model)
            print(f"✅ LLM structured via Gemini ({model})")
            return result
        except Exception as e:
            errors.append(f"gemini: {e}")
            print(f"⚠️  Gemini structured failed: {e}")
            if LLM_PROVIDER == "gemini":
                raise

    if use_groq:
        try:
            result = _llm_structured_groq(prompt, output_model)
            print(f"✅ LLM structured via Groq ({GROQ_MODEL})")
            return result
        except Exception as e:
            errors.append(f"groq: {e}")
            print(f"⚠️  Groq structured failed: {e}")
            if LLM_PROVIDER == "groq":
                raise

    raise RuntimeError(
        "All LLM providers failed. "
        + " | ".join(errors)
        + " — set GEMINI_API_KEY and/or GROQ_API_KEY (and pip install groq)."
    )
