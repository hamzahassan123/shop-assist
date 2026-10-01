from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from shop_assist.tools import (
    lookup_order,
    lookup_fulfillment,
    search_store_policy,
    cancel_shopify_order,
)

primary_llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0.1,
    max_retries=2,
)

fallback_llm_1 = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    temperature=0.1,
    max_retries=2,
)

fallback_llm_2 = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",
    temperature=0.1,
    max_retries=2,
)

base_llm = primary_llm.with_fallbacks([fallback_llm_1, fallback_llm_2])

tools = [
    lookup_order,
    lookup_fulfillment,
    search_store_policy,
    cancel_shopify_order,
]

llm_with_tools = base_llm.bind_tools(tools)


def call_model(state: MessagesState):
    response = llm_with_tools.invoke(
        [
            {
    "role": "system",
    "content": """
You are a Shopify customer support assistant for the Cogent store.

You have access to two types of information:

1. Shopify tools:
   - Use lookup_order when the customer asks about a specific order.
   - Use lookup_fulfillment when the customer asks about shipping, tracking, or fulfillment of a specific order.

2. Store policy search:
   - Use search_store_policy when the customer asks about store policies, returns, refunds, shipping rules, cancellations, or other store rules.
   - Base policy-related answers on the retrieved policy information.
   - Never invent store policies.

3. Order cancellation:
   - Use cancel_shopify_order when the customer explicitly asks to cancel an order.
   - Cancellation is a high-risk action.
   - The cancellation tool automatically pauses for human approval before executing.
   - Never claim an order was cancelled unless the tool reports successful cancellation.

When a question requires both order information and store policy information, use the relevant tools.

Never invent Shopify data or store policy information.

If the available information does not answer the customer's question, clearly say that you don't have enough information.

Keep responses concise, accurate, and customer-friendly.
"""
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