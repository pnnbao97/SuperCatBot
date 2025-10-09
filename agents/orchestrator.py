import json
from typing import Annotated
from typing_extensions import TypedDict

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_tavily import TavilySearch
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import InMemorySaver
from datetime import datetime
from agents.memory import State
from agents.chatbot import chatbot_node

from config.config import get_settings
import logging

settings = get_settings()
current_date = datetime.now().strftime("%d/%m/%Y")
logger = logging.getLogger(__name__)


memory = InMemorySaver()

# ==========================
# ORCHESTRATOR NODE
# ==========================
async def orchestrator_node(state: State):
    pass

# ==========================
# GRAPH SETUP
# ==========================
graph_builder = StateGraph(State)

graph_builder.add_node("orchestrator", chatbot_node)

# Set entry point và kết thúc
graph_builder.set_entry_point("orchestrator")
graph_builder.add_edge("orchestrator", END)

# Compile
graph = graph_builder.compile(checkpointer=memory)

# ==========================
# ORCHESTRATION AGENT
# ==========================
class OrchestratorAgent:
    """Agent điều phối đơn giản hóa - tất cả trong 1 node"""

    def __init__(self, thread_id: str = "1"):
        self.graph = graph
        self.config = {"configurable": {"thread_id": thread_id}}

    async def generate_answer(self, message: str) -> str:
        """Generate answer từ user message"""
        try:
            state = {
                "messages": [HumanMessage(content=message)]
            }
            
            result = await self.graph.ainvoke(state, self.config)
            
            # Lấy AIMessage cuối cùng
            messages = result.get("messages", [])
            if not messages:
                return "❌ Không có response"
            
            for msg in reversed(messages):
                if isinstance(msg, AIMessage):
                    return msg.content
            
            return "❌ Không tìm thấy response từ agent"
            
        except Exception as e:
            logger.error(f"❌ Chi tiết lỗi: {e}")
            import traceback
            traceback.print_exc()
            return f"❌ Lỗi agent: {e}"