import json
import os

try:
    import ollama
except ImportError:  # pragma: no cover - optional dependency in some environments
    ollama = None

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover - optional dependency in some environments
    OpenAI = None


DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "phi3:mini")
ACTIVE_BACKEND = os.getenv("LLM_BACKEND", "ollama").lower()
ACTIVE_MODEL = os.getenv("LLM_MODEL", DEFAULT_MODEL)
SUPPORTED_BACKENDS = ("ollama", "openai", "mock")
MODEL_OPTIONS = {
    "ollama": ["phi3:mini", "llama3.2", "mistral", "qwen2.5:7b", "deepseek-r1:8b"],
    "openai": ["gpt-4o-mini", "gpt-4o", "gpt-4.1-mini", "gpt-4.1"],
    "mock": ["mock"],
}


def set_active_backend(backend, model_name=None):
    global ACTIVE_BACKEND, ACTIVE_MODEL
    normalized_backend = (backend or "ollama").lower()
    if normalized_backend not in SUPPORTED_BACKENDS:
        raise ValueError(f"Unsupported backend '{backend}'. Supported backends: {', '.join(SUPPORTED_BACKENDS)}")

    ACTIVE_BACKEND = normalized_backend
    default_model = MODEL_OPTIONS.get(normalized_backend, ["mock"])[0]
    if model_name:
        ACTIVE_MODEL = model_name
    elif normalized_backend == "ollama":
        ACTIVE_MODEL = os.getenv("OLLAMA_MODEL", default_model)
    elif normalized_backend == "openai":
        ACTIVE_MODEL = os.getenv("OPENAI_MODEL", default_model)
    else:
        ACTIVE_MODEL = os.getenv("MOCK_MODEL", default_model)

    return ACTIVE_BACKEND


def get_model_options_for_backend(backend):
    normalized_backend = (backend or "ollama").lower()
    return list(MODEL_OPTIONS.get(normalized_backend, ["mock"]))


def get_active_backend():
    return ACTIVE_BACKEND


def get_active_model():
    return ACTIVE_MODEL


def _fallback_response(prompt):
    prompt_lower = prompt.lower()

    if "winner" in prompt_lower and "scores" in prompt_lower:
        winner = "Pro" if sum(ord(ch) for ch in prompt_lower) % 2 == 0 else "Against"
        scores = {
            "pro": {"logic": 8, "clarity": 9, "examples": 8},
            "against": {"logic": 7, "clarity": 7, "examples": 7},
        }
        if winner == "Against":
            scores = {
                "pro": {"logic": 7, "clarity": 7, "examples": 7},
                "against": {"logic": 8, "clarity": 9, "examples": 8},
            }
        return json.dumps({
            "winner": winner,
            "scores": scores,
            "reason": "The winning side offered clearer reasoning and stronger rebuttal quality.",
        })

    if "rebuttal" in prompt_lower:
        return "The opposing claim is too narrow and overlooks the broader practical impact of the issue."
    if "against" in prompt_lower:
        return "The idea is weak because it ignores the real costs, constraints, and implementation risk."
    return "The strongest case is that the topic creates measurable value by improving efficiency and reducing friction in practice."


def call_llm(prompt, response_schema=None):
    if ACTIVE_BACKEND == "mock":
        return _fallback_response(prompt)

    if ACTIVE_BACKEND == "openai":
        if OpenAI is None:
            raise RuntimeError("The OpenAI Python package is not installed.")
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set for the OpenAI backend.")

        client = OpenAI(api_key=api_key)
        request = {
            "model": ACTIVE_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
        }
        if response_schema is not None:
            request["response_format"] = {"type": "json_object"}

        response = client.chat.completions.create(**request)
        return response.choices[0].message.content

    if ollama is None:
        raise RuntimeError("The Ollama Python package is not installed.")

    try:
        request = {
            "model": ACTIVE_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "options": {
                "num_gpu": 0,
                "temperature": 0.1,
            },
        }
        if response_schema is not None:
            request["format"] = response_schema

        response = ollama.chat(**request)
        return response["message"]["content"]
    except Exception as exc:  # pragma: no cover - depends on local runtime
        raise RuntimeError(f"Could not get a response from {ACTIVE_BACKEND} model '{ACTIVE_MODEL}': {exc}") from exc