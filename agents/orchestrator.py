from pydantic import BaseModel, Field
from typing import Literal, TypedDict, Annotated
from operator import add

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import InMemorySaver
from agents.chatbot import chatbot_node
from agents.video_agent import video_agent_node
from agents.memory import State
from agents.models import main_llm

import logging

logger = logging.getLogger(__name__)

# ==========================
# AGENT MAPPING
# ==========================
agent_nodes = {
    "chatbot": chatbot_node,
    "video_agent": video_agent_node
}

# ==========================
# ROUTING SCHEMA
# ==========================
class RouteSchema(BaseModel):
    next: Literal["chatbot", "video_agent"]
    instructions: str = Field(
        description="Hướng dẫn cụ thể cho agent tiếp theo"
    )

memory = InMemorySaver()
main_llm_with_routing = main_llm.with_structured_output(RouteSchema)

# ==========================
# ORCHESTRATOR NODE
# ==========================
async def orchestrator_node(state: State):
    """Nhạc trưởng điều phối"""
    
    messages = state["messages"]
    
    # Kiểm tra xem có agent nào vừa trả lời không
    last_message = messages[-1] if messages else None
    has_agent_response = (
        isinstance(last_message, AIMessage) and 
        len(messages) > 1  # Có cả user message
    )
    
    system_prompt = SystemMessage(
        content=(
            f"Bạn là supervisor điều phối team agents.\n\n"
            f"Agents có sẵn: {list(agent_nodes.keys())}\n\n"
            f"Chức năng:\n"
            f"- chatbot: Chat thông thường, hỏi đáp chung, tư vấn\n"
            f"- video_agent: Phân tích video, xử lý video\n\n"
            f"Trả về:\n"
            f"- next: tên agent\n"
            f"- instructions: hướng dẫn cụ thể cho agent"
        )
    )
    
    response = await main_llm_with_routing.ainvoke([system_prompt] + messages)
    
    logger.info(f"🎯 Orchestrator decision: {response.next}")
    logger.info(f"📝 Instructions: {response.instructions}")
    
    return {
        "next_agent": response.next,
        "agent_instructions": response.instructions
    }


# ==========================
# ROUTING FUNCTION
# ==========================
def route_to_agent(state: State) -> str:
    """Conditional routing dựa trên orchestrator decision"""
    next_agent = state.get("next_agent", "chatbot")
    logger.info(f"➡️  Routing to: {next_agent}")
    return next_agent


# ==========================
# GRAPH SETUP
# ==========================
graph_builder = StateGraph(State)

# Add orchestrator
graph_builder.add_node("orchestrator", orchestrator_node)

# Add agents và edge quay về orchestrator
for agent_name, node_func in agent_nodes.items():
    graph_builder.add_node(agent_name, node_func)
    # graph_builder.add_edge(agent_name, "orchestrator")

# Entry point
graph_builder.set_entry_point("orchestrator")

# Conditional routing từ orchestrator
graph_builder.add_conditional_edges(
    "orchestrator",
    route_to_agent,
    {
        "chatbot": "chatbot",
        "video_agent": "video_agent",
    }
)

# Compile với memory
graph = graph_builder.compile(checkpointer=memory)


# ==========================
# ORCHESTRATION AGENT
# ==========================
class OrchestratorAgent:
    """Main orchestrator agent để interact với graph"""

    def __init__(self, thread_id: str):
        self.graph = graph
        self.config = {"configurable": {"thread_id": thread_id}}

    async def generate_answer(self, message: str) -> str:
        """Generate answer từ user message"""
        try:
            # Initial state
            initial_state = {
                "messages": [HumanMessage(content=message)]
            }
            
            # Invoke graph
            result = await self.graph.ainvoke(initial_state, self.config)
            
            # Extract final response
            messages = result.get("messages", [])
            if not messages:
                return "❌ Không có response từ agent"
            
            # Tìm AIMessage cuối cùng (response từ agent)
            for msg in reversed(messages):
                if isinstance(msg, AIMessage):
                    return msg.content
            
            return "❌ Không tìm thấy AI response"
            
        except Exception as e:
            logger.error(f"❌ Lỗi orchestrator: {e}", exc_info=True)
            return f"❌ Đã xảy ra lỗi: {str(e)}"
    
    async def stream_answer(self, message: str):
        """Stream answer với progress updates"""
        try:
            initial_state = {
                "messages": [HumanMessage(content=message)]
            }
            
            async for event in self.graph.astream(initial_state, self.config):
                logger.info(f"📦 Event: {event}")
                yield event
                
        except Exception as e:
            logger.error(f"❌ Lỗi stream: {e}", exc_info=True)
            yield {"error": str(e)}