from types import SimpleNamespace


def text_response(text: str, stop_reason: str = "end_turn"):
    return SimpleNamespace(
        stop_reason=stop_reason,
        content=[SimpleNamespace(type="text", text=text)],
    )


def tool_response(tool_id: str, name: str, tool_input: dict):
    return SimpleNamespace(
        stop_reason="tool_use",
        content=[
            SimpleNamespace(
                type="tool_use",
                id=tool_id,
                name=name,
                input=tool_input,
            )
        ],
    )


def tool_schema(name: str) -> dict:
    return {
        "name": name,
        "description": f"{name} test tool",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    }


class FakeAdapter:
    def __init__(self, responses=()):
        self.responses = list(responses)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self.responses.pop(0)

    def create_streaming(self, **kwargs):
        self.calls.append(kwargs)
        return self.responses.pop(0)


class FakeSDKClient:
    def __init__(self):
        self.messages = SimpleNamespace(create=None, stream=None)
