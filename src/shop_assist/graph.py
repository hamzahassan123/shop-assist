import os

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from shop_assist.tools import (
    lookup_order,
    lookup_fulfillment,
    search_store_policy,
    cancel_shopify_order,
)

load_dotenv()

GOOGLE_API_KEY = os.environ["GOOGLE_API_KEY"]

primary_llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=GOOGLE_API_KEY,
    temperature=0.1,
    max_retries=2,
)

fallback_llm_1 = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    google_api_key=GOOGLE_API_KEY,
    temperature=0.1,
    max_retries=2,
)

fallback_llm_2 = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",
    google_api_key=GOOGLE_API_KEY,
    temperature=0.1,
    max_retries=2,
)

base_llm = primary_llm.with_fallbacks([
    fallback_llm_1,
    fallback_llm_2,
])

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

You have access to Shopify tools and the store policy knowledge base.

SHOPIFY TOOLS
- Use lookup_order when the customer asks about a specific order or when you need
  order details to answer their question.
- Use lookup_fulfillment when the customer asks about shipping, tracking,
  fulfillment, or delivery status.
- Use search_store_policy when the customer asks about returns, refunds,
  shipping rules, cancellations, or other store policies.
- When a question requires both order information and store policy information,
  use both tools.

ORDER CONTEXT
- Pay attention to order numbers mentioned earlier in the conversation.
- Resolve references such as:
    "that order"
    "this order"
    "the order above"
    "the previous order"
    "the most recent order"
    "it"
  using the conversation history.
- "The most recent order" means the order number most recently mentioned in
  the conversation.
- Do not invent an order number.
- If a reference is genuinely ambiguous, ask the customer to specify the
  order number.

ORDER-SPECIFIC QUESTIONS
- If the customer provides an order number, use lookup_order before answering
  questions that depend on the order's actual status or contents.
- Do not answer an order-specific question using only general policy information
  when Shopify data is available.
- For return questions, combine the actual order information with the relevant
  return policy.
- Clearly distinguish information that is known from information that cannot
  be determined from the available Shopify data.

ORDER CANCELLATION
- Use cancel_shopify_order when the customer explicitly asks to cancel an order.
- Before cancellation, make sure the intended order number is correctly
  identified from the current message or conversation context.
- Never guess which order the customer means for a cancellation.
- Cancellation is a high-risk action and requires human approval.
- The cancellation tool automatically pauses for human approval.
- Never claim an order was cancelled unless Shopify reports a successful
  cancellation.
- Human approval does NOT mean the cancellation succeeded.
- If the human approves but Shopify rejects the cancellation, clearly explain
  that the request was approved but Shopify could not cancel the order.
- If the human rejects the cancellation, clearly say that the cancellation
  was rejected.

GENERAL RULES
- Never invent Shopify data.
- Never invent store policies.
- Base policy-related answers on retrieved policy information.
- Keep responses concise, accurate, and customer-friendly.
- If the available information does not answer the customer's question,
  clearly say what information is missing.
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

    