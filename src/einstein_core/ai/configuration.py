"""Construction facultative du fournisseur à partir d'un secret fichier."""

from pydantic import SecretStr

from einstein_core.ai.provider import AnswerProvider
from einstein_core.ai.openai_provider import OpenAIProvider
from einstein_core.config import Settings


def configure_provider(settings: Settings) -> AnswerProvider | None:
    if not settings.ai_enabled or not settings.ai_model:
        return None
    if settings.ai_provider == "chatgpt":
        if not settings.ai_chatgpt_credentials_file or not settings.ai_chatgpt_credentials_file.is_file():
            return None
        # Import optionnel : les déploiements par clé n'exigent pas PyJWT.
        try:
            from einstein_core.ai.chatgpt_provider import ChatGPTProvider
        except ImportError:
            return None

        return ChatGPTProvider(
            credentials_file=settings.ai_chatgpt_credentials_file,
            model=settings.ai_model, timeout=settings.ai_timeout_seconds,
            max_output_chars=settings.ai_max_output_chars,
        )
    if not settings.ai_api_key_file:
        return None
    try:
        with settings.ai_api_key_file.open("rb") as file:
            raw = file.read(16385)
        if len(raw) > 16384:
            return None
        key = raw.decode("utf-8").strip()
    except (OSError, UnicodeError):
        return None
    if not key:
        return None
    return OpenAIProvider(
        api_key=SecretStr(key), model=settings.ai_model,
        timeout=settings.ai_timeout_seconds, max_output_tokens=settings.ai_max_output_tokens,
    )
