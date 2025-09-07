import os
from dotenv import load_dotenv

# Load .env file from the backend directory
load_dotenv()
try:
    module_dir = os.path.dirname(os.path.abspath(__file__))
    # Assumes services/ is one level deep from backend/
    env_path = os.path.join(os.path.dirname(module_dir), ".env")
    if os.path.isfile(env_path):
        load_dotenv(env_path, override=False)
except Exception:
    pass

def get_openai_completion():
    """
    Returns a function to call the OpenAI completions API,
    handling both new and legacy SDKs. Returns None if unavailable.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)

        def _completion(prompt, model, temperature, max_tokens=1024):
            return client.completions.create(
                model=model,
                max_tokens=max_tokens,
                prompt=prompt,
                temperature=temperature,
            )
        return _completion
    except Exception:
        try:
            import openai as _openai
            _openai.api_key = api_key

            def _completion(prompt, model, temperature, max_tokens=1024):
                return _openai.Completion.create(
                    model=model,
                    max_tokens=max_tokens,
                    prompt=prompt,
                    temperature=temperature,
                )
            return _completion
        except Exception:
            return None

# Singleton instance of the completion function that can be imported elsewhere
completion_client = get_openai_completion()