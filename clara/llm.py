"""Model setup and the single `_llm(system, user)` call every other module uses."""
from smolagents.models import ChatMessage, MessageRole

from . import config


class MockModel:
    """Scripted stand-in so everything runs end to end without a key."""
    model_id = "mock"

    def generate(self, messages, **kwargs):
        system = messages[0].content[0]["text"]
        user = messages[-1].content[0]["text"]
        if "role-playing" in system:
            if "Thu 2pm" in user:
                return ChatMessage(role=MessageRole.ASSISTANT,
                                   content="Thursday... two o'clock. Yes.\nDONE: lisinopril, Thursday 2pm")
            return ChatMessage(role=MessageRole.ASSISTANT,
                               content="Hello. I need my... the pressure pills. Lisinopril?")
        return ChatMessage(role=MessageRole.ASSISTANT,
                           content="I can refill your lisinopril. The Thursday slot is Thu 2pm. Does that work?")


def make_model(provider: str = None, model_id: str = None):
    provider = (provider or config.PROVIDER).lower()
    model_id = model_id or config.MODEL_ID
    if provider == "mock":
        return MockModel()
    if provider == "hf":
        from smolagents import InferenceClientModel
        return InferenceClientModel(model_id=model_id, token=config.secret("HF_TOKEN"))
    from smolagents import LiteLLMModel
    key_name = {"anthropic": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY"}[provider]
    key = config.secret(key_name)
    if not key:
        print(f"[clara] {key_name} not set; falling back to the mock model.")
        return MockModel()
    return LiteLLMModel(model_id=model_id, api_key=key)


_model = None


def get_model():
    global _model
    if _model is None:
        _model = make_model()
    return _model


def set_model(model):
    """Swap the model at runtime, e.g. from a notebook: set_model(make_model('mock'))."""
    global _model
    _model = model


def _llm(system: str, user: str) -> str:
    msgs = [ChatMessage(role=MessageRole.SYSTEM, content=[{"type": "text", "text": system}]),
            ChatMessage(role=MessageRole.USER, content=[{"type": "text", "text": user}])]
    return (get_model().generate(msgs).content or "").strip()
