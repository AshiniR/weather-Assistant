from langgraph.graph import StateGraph, START, END
from langchain_core.messages import SystemMessage
from langgraph.prebuilt import ToolNode, tools_condition

from tools.tools import get_current_weather, get_forecast, clothing_suggestion, weather_alerts
from models.agentState import AgentState
from core.config import llm, SYSTEM_PROMPT


# Register all tools
tools = [get_current_weather, get_forecast, clothing_suggestion, weather_alerts]

model = llm.bind_tools(tools)

def chatbot(state: AgentState) -> dict:
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + list(state["messages"])
    response = model.invoke(messages)
    updated_messages = list(state["messages"]) + [response]
    return {"messages": updated_messages}

graph_builder = StateGraph(AgentState)

graph_builder.add_node("chatbot", chatbot)

tool_node = ToolNode(tools=tools)
graph_builder.add_node("tools", tool_node)

graph_builder.add_conditional_edges(
    "chatbot",
    tools_condition,
)
graph_builder.add_edge("tools", "chatbot")
graph_builder.add_edge(START, "chatbot")
graph_builder.add_edge("chatbot", END)
graph = graph_builder.compile()