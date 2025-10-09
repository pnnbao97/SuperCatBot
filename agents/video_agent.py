from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from agents.memory import State
from agents.models import main_llm
from tools.video_tools import video_tools

import logging

logger = logging.getLogger(__name__)

# ✅ Bind tools vào LLM
video_llm = main_llm.bind_tools(video_tools)


async def video_agent_node(state: State):
    """Agent xử lý video - tải, tách đoạn, lấy thông tin"""
    
    user_messages = [m for m in state["messages"] if isinstance(m, HumanMessage)]
    instructions = state.get("agent_instructions", "")
    
    if not user_messages:
        return {"messages": [AIMessage(content="❌ Không có câu hỏi về video")]}
    
    user_query = user_messages[-1].content
    recent_messages = state["messages"][-5:]  # Lấy 5 messages gần nhất
    
    logger.info(f"🎬 [VIDEO AGENT] Query: '{user_query}'")
    logger.info(f"📋 Instructions: '{instructions}'")
    
    # System prompt cho video agent
    system_prompt = SystemMessage(
        content=(
            f"Mày là SuperCat, con mèo cam thông thái, chuyên xử lý video.\n\n"
            f"Nhiệm vụ: {instructions}\n\n"
            f"Các công cụ có sẵn:\n"
            f"1. download_video: Tải video/audio từ YouTube, Facebook, TikTok, Instagram, Reddit, X, Vimeo, Dailymotion\n"
            f"2. get_video_info: Lấy thông tin về video\n\n"
            f"Hướng dẫn sử dụng:\n"
            f"- Nếu user muốn tải video → dùng download_video với audio_only=False\n"
            f"- Nếu user muốn tải audio → dùng download_video với audio_only=True\n"
            f"- Nếu user muốn tách đoạn → thêm start_time và end_time\n"
            f"- Nếu user hỏi thông tin video → dùng get_video_info\n\n"
            f"Format thời gian: MM:SS (vd: 1:30), HH:MM:SS (vd: 1:30:45), hoặc số giây (vd: 90)\n\n"
            f"Hãy phân tích yêu cầu và gọi tool phù hợp!"
        )
    )
    
    # Gọi LLM với tools
    response = await video_llm.ainvoke([system_prompt] + recent_messages)
    
    # Kiểm tra xem có tool calls không
    if not response.tool_calls:
        # Không có tool call → trả lời thông thường
        logger.info("💬 No tool calls, returning direct response")
        return {"messages": [response]}
    
    # Có tool calls → xử lý từng tool
    logger.info(f"🔧 Tool calls: {len(response.tool_calls)}")
    
    messages_to_add = [response]  # Thêm AI message với tool calls
    
    # Execute tools
    for tool_call in response.tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        tool_id = tool_call["id"]
        
        logger.info(f"⚙️ Executing tool: {tool_name} with args: {tool_args}")
        
        # Tìm tool function
        tool_func = None
        for tool in video_tools:
            if tool.name == tool_name:
                tool_func = tool
                break
        
        if not tool_func:
            result = f"❌ Tool '{tool_name}' không tồn tại"
        else:
            try:
                # Gọi tool
                result = await tool_func.ainvoke(tool_args)
                logger.info(f"✅ Tool result: {result[:100]}...")
            except Exception as e:
                result = f"❌ Lỗi khi thực thi tool: {str(e)}"
                logger.error(f"❌ Tool execution error: {e}")
        
        # Thêm tool message
        messages_to_add.append(
            ToolMessage(
                content=str(result),
                tool_call_id=tool_id
            )
        )
    
    # Gọi LLM lần nữa để tổng hợp kết quả
    final_response = await video_llm.ainvoke([system_prompt] + recent_messages + messages_to_add)
    messages_to_add.append(final_response)
    
    logger.info(f"✅ [VIDEO AGENT] Completed with {len(messages_to_add)} messages")
    
    return {"messages": messages_to_add}