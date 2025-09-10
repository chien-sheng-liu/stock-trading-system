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
    Returns a function compatible with current call sites:
      fn(prompt, model, temperature, max_tokens=1024) -> response

    - If model looks like a chat model (e.g., gpt-4, gpt-4o, gpt-3.5-turbo),
      it uses Chat Completions and normalizes the return value to a dict:
         {"choices": [{"text": content}]}
    - Otherwise it uses the Completions API as-is.

    Returns None if no API key or SDK unavailable.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None

    def _is_chat_model(m: str) -> bool:
        ml = (m or "").lower()
        if not ml:
            return False
        # Explicit non-chat models (Completions API)
        if any(x in ml for x in ["instruct", "babbage-002", "davinci-002", "text-davinci"]):
            return False
        # Common chat models
        return any(x in ml for x in ["gpt-4", "gpt-4o", "gpt-3.5-turbo", "o1", "o3", "mini"])

    # Prefer 1.x client if available
    try:
        from openai import OpenAI  # type: ignore
        client = OpenAI(api_key=api_key)

        def _completion(prompt, model, temperature, max_tokens=1024):
            use_chat = _is_chat_model(str(model))
            if use_chat:
                try:
                    resp = client.chat.completions.create(
                        model=model,
                        messages=[{"role": "user", "content": str(prompt)}],
                        temperature=temperature,
                        max_tokens=max_tokens,
                    )
                    try:
                        content = resp.choices[0].message.content or ""
                    except Exception:
                        content = ""
                    return {"choices": [{"text": content}]}
                except Exception as e:
                    # Fallback: if model is not chat-capable, try Completions
                    msg = str(getattr(e, "message", "") or str(e))
                    if "not a chat model" in msg or "v1/chat/completions" in msg:
                        return client.completions.create(
                            model=model,
                            max_tokens=max_tokens,
                            prompt=prompt,
                            temperature=temperature,
                        )
                    raise
            # Completions path
            try:
                return client.completions.create(
                    model=model,
                    max_tokens=max_tokens,
                    prompt=prompt,
                    temperature=temperature,
                )
            except Exception as e:
                # If endpoint mismatch, try chat as fallback
                msg = str(getattr(e, "message", "") or str(e))
                if "use v1/chat/completions" in msg or "messages" in msg:
                    resp = client.chat.completions.create(
                        model=model,
                        messages=[{"role": "user", "content": str(prompt)}],
                        temperature=temperature,
                        max_tokens=max_tokens,
                    )
                    try:
                        content = resp.choices[0].message.content or ""
                    except Exception:
                        content = ""
                    return {"choices": [{"text": content}]}
                raise

        return _completion
    except Exception:
        # Legacy SDK fallback
        try:
            import openai as _openai  # type: ignore
            _openai.api_key = api_key

            def _completion(prompt, model, temperature, max_tokens=1024):
                use_chat = _is_chat_model(str(model))
                if use_chat:
                    try:
                        resp = _openai.ChatCompletion.create(
                            model=model,
                            messages=[{"role": "user", "content": str(prompt)}],
                            temperature=temperature,
                            max_tokens=max_tokens,
                        )
                        try:
                            content = resp["choices"][0]["message"]["content"]
                        except Exception:
                            content = ""
                        return {"choices": [{"text": content}]}
                    except Exception as e:
                        msg = str(getattr(e, "message", "") or str(e))
                        if "not a chat model" in msg or "v1/chat/completions" in msg:
                            return _openai.Completion.create(
                                model=model,
                                max_tokens=max_tokens,
                                prompt=prompt,
                                temperature=temperature,
                            )
                        raise
                # Completions path
                try:
                    return _openai.Completion.create(
                        model=model,
                        max_tokens=max_tokens,
                        prompt=prompt,
                        temperature=temperature,
                    )
                except Exception as e:
                    msg = str(getattr(e, "message", "") or str(e))
                    if "use v1/chat/completions" in msg or "messages" in msg:
                        resp = _openai.ChatCompletion.create(
                            model=model,
                            messages=[{"role": "user", "content": str(prompt)}],
                            temperature=temperature,
                            max_tokens=max_tokens,
                        )
                        try:
                            content = resp["choices"][0]["message"]["content"]
                        except Exception:
                            content = ""
                        return {"choices": [{"text": content}]}
                    raise

            return _completion
        except Exception:
            return None

# Singleton instance of the completion function that can be imported elsewhere
completion_client = get_openai_completion()
