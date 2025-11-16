"""Minimal chainlit stub for tests."""

class Action:
    def __init__(self, name: str, value: str):
        self.name = name
        self.value = value

class Message:
    def __init__(self, content: str, elements=None, actions=None):
        self.content = content
        self.elements = elements or []
        self.actions = actions or []

    async def send(self) -> None:
        return None

class Iframe:
    def __init__(self, path: str, display: str = "inline", height: int = 500):
        self.path = path
        self.display = display
        self.height = height

class Text:
    def __init__(self, name: str, content: str):
        self.name = name
        self.content = content

class Button:
    def __init__(self, name: str, content: str):
        self.name = name
        self.content = content

class Plotly:
    def __init__(self, name: str, figure: dict, display: str = "inline"):
        self.name = name
        self.figure = figure
        self.display = display

class Image:
    def __init__(self, name: str, path: str, display: str = "inline"):
        self.name = name
        self.path = path
        self.display = display

class File:
    def __init__(self, name: str, path: str):
        self.name = name
        self.path = path


def action_callback(name=None):  # type: ignore[return-value]
    def decorator(func):
        return func

    return decorator

def tool(name=None, **kwargs):  # type: ignore[return-value]
    def decorator(func):
        return func

    return decorator

def on_chat_start(func=None):
    if callable(func):
        return func
    def decorator(f):
        return f
    return decorator

def on_settings_update(func=None):
    if callable(func):
        return func
    def decorator(f):
        return f
    return decorator

async def on_message(*_, **__):
    pass

def step(type=None, name=None):
    def decorator(func):
        return func
    return decorator
