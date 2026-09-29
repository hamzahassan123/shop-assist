from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from shop_assist.tools import lookup_order, lookup_fulfillment


llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0.1,
)

tools = [lookup_order, lookup_fulfillment]

llm_with_tools = llm.bind_tools(tools)


def call_model(state: MessagesState):
    response = llm_with_tools.invoke(
        [
            {
                "role": "system",
                "content": """
You are a Shopify customer support assistant.

When a customer asks about a specific order:
- Identify the order number.
- Use lookup_order to retrieve the real order.
- Base your answer only on the returned Shopify data.
- Never invent order information.
- Clearly explain financial and fulfillment status.
- If the order does not exist, say so clearly.
- Keep responses concise and customer-friendly.
""",
            },
            *state["messages"],
        ]
    )

    return {"messages": [response]}


def build_graph(checkpointer):
    builder = StateGraph(MessagesState)

    builder.add_node("agent", call_model)
    builder.add_node("tools", ToolNode(tools))

    builder.set_entry_point("agent")

    builder.add_conditional_edges(
        "agent",
        tools_condition,
    )

    builder.add_edge("tools", "agent")

    return builder.compile(checkpointer=checkpointer)