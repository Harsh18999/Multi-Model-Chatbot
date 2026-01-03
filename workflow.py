from langgraph.graph import StateGraph, START, END
from langchain.chat_models import init_chat_model
from langchain.tools import tool
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.graph.message import add_messages
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from typing import TypedDict, Annotated
import dotenv
from langchain_community.tools import DuckDuckGoSearchResults

# load .env variables
dotenv.load_dotenv()

# define tools
@tool
def webSearch(query: Annotated[str, "Input of perform web search"]):
    """
    Perform ddg web search based on user query and get list of responses
    :param query: modified query based on user query
    :return: list of web search results
    """
    search = DuckDuckGoSearchResults(output_format="list")
    results = search.invoke(query)
    return  results

#define chat model
chat_model = init_chat_model(model="gemini-2.0-flash", model_provider="google-genai").bind_tools([webSearch])

# define state class
class State(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


# define nodes
def chat(state: State):
    response = chat_model.invoke(state["messages"])
    return {"messages":response}

# define tool node
tools = [webSearch]
tool_node = ToolNode(tools)

# define worklflow
builder = StateGraph(State)

# add nodes
builder.add_node("chat_node", chat)
builder.add_node("tools", tool_node)

# add edges
builder.add_edge(START,"chat_node")
builder.add_conditional_edges("chat_node", tools_condition)
builder.add_edge("tools", "chat_node")

