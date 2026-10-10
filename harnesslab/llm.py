"""Model access. Everything returns {"content": str, "tool_calls": [{"name","arguments"}]}."""


class OllamaLLM:
    def __init__(self, model: str):
        import ollama  # imported here so selfcheck works without it
        self.ollama = ollama
        self.model = model

    def chat(self, messages, tools=None):
        r = self.ollama.chat(
            model=self.model, messages=messages, tools=tools or None,
            options={"temperature": 0.2, "num_ctx": 8192},
        )
        m = r.message
        calls = [
            {"name": c.function.name, "arguments": dict(c.function.arguments)}
            for c in (m.tool_calls or [])
        ]
        return {"content": m.content or "", "tool_calls": calls}
