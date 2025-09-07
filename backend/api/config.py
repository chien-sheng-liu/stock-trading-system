from fastapi import APIRouter
import os
import importlib

router = APIRouter()


def _detect_openai_sdk():
    info = {"installed": False, "sdk": "none", "version": "unknown"}
    try:
        openai = importlib.import_module("openai")
        info["installed"] = True
        info["version"] = getattr(openai, "__version__", "unknown")
        try:
            from openai import OpenAI  # type: ignore
            info["sdk"] = "new"
        except Exception:
            info["sdk"] = "legacy" if hasattr(openai, "ChatCompletion") else "unknown"
    except ImportError:
        pass
    return info


@router.get("/config")
def get_config():
    key = os.getenv("OPENAI_API_KEY")
    # Default to an instruct-capable model for the Completions API
    model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo-instruct")
    sdk = _detect_openai_sdk()

    has_key = bool(key)
    sdk_ok = bool(sdk["installed"])
    enabled = has_key and sdk_ok

    return {
        "ai": {
            "enabled": enabled,
            "has_key": has_key,
            "sdk_installed": sdk_ok,
            "sdk": sdk.get("sdk", "unknown"),
            "sdk_version": sdk.get("version", "unknown"),
            "model": model,
            "api": "completions",
        },
        "app": {
            "version": "1.0.0",
        },
    }
