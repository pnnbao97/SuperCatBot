from langchain_core.messages import BaseMessage
from typing import Annotated
from typing_extensions import TypedDict

def limit_messages(existing: list[BaseMessage], new: list[BaseMessage]) -> list[BaseMessage]:
    """Giữ tối đa N messages gần nhất"""
    MAX_MESSAGES = 15
    combined = existing + new
    return combined[-MAX_MESSAGES:]
    
class State(TypedDict):
    messages: Annotated[list[BaseMessage], limit_messages]