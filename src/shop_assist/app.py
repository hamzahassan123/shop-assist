import os
import logging
import uuid
from datetime import datetime, timedelta, timezone

import extra_streamlit_components as stx
import httpx
import psycopg
import requests
import streamlit as st
from dotenv import load_dotenv
from google.genai.errors import APIError as GoogleGenAIAPIError
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.types import Command

from shop_assist.db import get_checkpointer, get_conversations
from shop_assist.graph import build_graph
from shop_assist.logging_config import (
    configure_logging,
    conversation_id_context,
)
from shop_assist.security import sanitize_pii
from shop_assist.utils import content_to_text


load_dotenv()
configure_logging()
logger = logging.getLogger(__name__)

STOREFRONT_URL = os.getenv(
    "SHOPIFY_STOREFRONT_URL",
    "https://cogent-uffhonio.myshopify.com/",
)
STOREFRONT_PASSWORD = os.getenv("SHOPIFY_STOREFRONT_PASSWORD")

st.set_page_config(
    page_title="ShopAssist",
    page_icon="🛍️",
    layout="centered",
)


@st.cache_resource
def get_graph():
    return build_graph(get_checkpointer())


def new_conversation_id(user_session_id: str) -> str:
    return f"{user_session_id}:{uuid.uuid4().hex[:12]}"


def load_conversation(config):
    """Load the latest conversation state from PostgreSQL."""
    state = get_graph().get_state(config)
    if state.values:
        return state.values.get("messages", [])
    return []


def load_messages_for_ui(config):
    messages = []
    for message in load_conversation(config):
        if isinstance(message, HumanMessage):
            role = "user"
        elif isinstance(message, AIMessage):
            role = "assistant"
        else:
            continue

        text = content_to_text(message.content)
        if text:
            messages.append({"role": role, "content": text})
    return messages


def _tool_status(tool_name: str, completed: bool = False) -> str:
    labels = {
        "lookup_order": "🔍 Looking up order",
        "lookup_fulfillment": "🚚 Checking fulfillment",
        "search_store_policy": "📚 Searching policies",
        "cancel_shopify_order": "🛑 Processing cancellation",
    }
    label = labels.get(tool_name, "Using support tool")
    return f"{label} complete..." if completed else f"{label}..."


def stream_graph(input_data, config, status):
    """Stream model tokens through the graph's synchronous checkpointer."""
    graph = get_graph()
    graph_output = {}

    def graph_chunks():
        for event in graph.stream(
            input_data,
            config=config,
            stream_mode=["messages", "updates"],
            version="v2",
        ):
            if event["type"] == "messages":
                chunk, metadata = event["data"]
                if metadata.get("langgraph_node") == "agent":
                    text = content_to_text(getattr(chunk, "content", ""))
                    if text:
                        yield text
            elif event["type"] == "updates":
                for node, update in event["data"].items():
                    if node == "__interrupt__":
                        graph_output["__interrupt__"] = update
                    elif node == "agent":
                        messages = update.get("messages", [])
                        if messages:
                            for tool_call in getattr(messages[-1], "tool_calls", []):
                                status.update(
                                    label=_tool_status(tool_call["name"])
                                )
                    elif node == "tools":
                        for tool_message in update.get("messages", []):
                            status.update(
                                label=_tool_status(
                                    tool_message.name,
                                    completed=True,
                                )
                            )

    streamed_text = st.write_stream(graph_chunks())
    return streamed_text, graph_output


def get_pending_interrupt(graph_output, state):
    interrupts = graph_output.get("__interrupt__", ())
    if interrupts:
        first_interrupt = interrupts[0]
        return getattr(first_interrupt, "value", first_interrupt)

    for task in state.tasks:
        if task.interrupts:
            return task.interrupts[0].value
    return None


def get_latest_assistant_text(state, streamed_text: str) -> str:
    if streamed_text:
        return streamed_text

    messages = state.values.get("messages", [])
    if messages:
        return content_to_text(messages[-1].content)
    return ""


def show_processing_error(action: str, message: str, error: Exception, status) -> None:
    logger.exception("%s: %s", action, error)
    status.update(label="Request failed", state="error", expanded=False)
    st.error(message)


# The cookie is a browser-session namespace, not an authentication credential.
cookie_manager = stx.CookieManager(key="shop-assist-session-cookie")
cookie_value = cookie_manager.get("user_session_id")
if "user_session_id" not in st.session_state:
    try:
        user_session_id = uuid.UUID(str(cookie_value)).hex
    except (ValueError, AttributeError):
        user_session_id = uuid.uuid4().hex
        cookie_manager.set(
            "user_session_id",
            user_session_id,
            expires_at=datetime.now(timezone.utc) + timedelta(days=365),
        )
    st.session_state.user_session_id = user_session_id

user_session_id = st.session_state.user_session_id
thread_prefix = f"{user_session_id}:"

if "conversation_id" not in st.session_state:
    conversation_id = st.query_params.get("conversation_id")
    if not conversation_id or not conversation_id.startswith(thread_prefix):
        conversation_id = new_conversation_id(user_session_id)
    st.session_state.conversation_id = conversation_id
    st.query_params["conversation_id"] = conversation_id

conversation_id = st.session_state.conversation_id
conversation_id_context.set(conversation_id)
config = {"configurable": {"thread_id": conversation_id}}

if "messages" not in st.session_state:
    st.session_state.messages = load_messages_for_ui(config)

if "pending_interrupt" not in st.session_state:
    state = get_graph().get_state(config)
    st.session_state.pending_interrupt = get_pending_interrupt({}, state)


with st.sidebar:
    st.title("🛍️ ShopAssist")

    st.link_button("Open Cogent storefront", STOREFRONT_URL, width="stretch")
    if STOREFRONT_PASSWORD:
        st.caption("Storefront password")
        st.code(STOREFRONT_PASSWORD)
    else:
        st.caption("Store password: 123")

    st.divider()

    if st.button("＋ New conversation", width="stretch"):
        conversation_id = new_conversation_id(user_session_id)
        st.session_state.conversation_id = conversation_id
        st.session_state.messages = []
        st.session_state.pending_interrupt = None
        st.query_params["conversation_id"] = conversation_id
        st.rerun()

    st.divider()
    st.subheader("Saved conversations")
    conversations = get_conversations(user_session_id=user_session_id)

    for conversation in conversations:
        thread_id = conversation["thread_id"]
        title = conversation["title"]
        display_title = title[:42] + "..." if len(title) > 42 else title
        label = f"● {display_title}" if thread_id == conversation_id else display_title

        if st.button(
            label,
            key=f"conversation-{thread_id}",
            width="stretch",
        ):
            st.session_state.conversation_id = thread_id
            st.session_state.messages = load_messages_for_ui(
                {"configurable": {"thread_id": thread_id}}
            )
            st.session_state.pending_interrupt = None
            st.query_params["conversation_id"] = thread_id
            st.rerun()

    if not conversations:
        st.caption("No saved conversations yet.")

    st.divider()
    st.caption(f"Conversation ID: {conversation_id}")


st.title("Customer Support")
st.caption("AI customer support for the Cogent Shopify store.")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


if st.session_state.pending_interrupt:
    interrupt_data = st.session_state.pending_interrupt
    order = interrupt_data["order"]

    st.warning("Human approval required")
    st.subheader(f"Cancel order #{interrupt_data['order_number']}")
    financial_col, fulfillment_col = st.columns(2)
    financial_col.metric("Financial status", order["financial_status"])
    fulfillment_col.metric("Fulfillment status", order["fulfillment_status"])
    st.caption(f"Created: {order['created_at']}")
    st.write(
        f"Refund: {interrupt_data['refund']} · "
        f"Restock inventory: {interrupt_data['restock']} · "
        f"Notify customer: {interrupt_data['notify_customer']}"
    )
    st.dataframe(order["items"], hide_index=True, width="stretch")

    approve_col, reject_col = st.columns(2)
    approve = approve_col.button(
        "✅ Approve cancellation",
        width="stretch",
    )
    reject = reject_col.button("❌ Reject", width="stretch")

    if approve or reject:
        action = "approve" if approve else "reject"
        action_label = (
            "Failed to process approved cancellation"
            if approve
            else "Failed to process rejected cancellation"
        )
        friendly_message = (
            "Sorry, the cancellation could not be processed. Please try again."
            if approve
            else "Sorry, we could not process your decision. Please try again."
        )

        with st.chat_message("assistant"):
            with st.status("Processing your decision...", expanded=True) as status:
                try:
                    streamed_text, graph_output = stream_graph(
                        Command(resume={"action": action}),
                        config,
                        status,
                    )
                    state = get_graph().get_state(config)
                    pending_interrupt = get_pending_interrupt(graph_output, state)
                except (
                    requests.RequestException,
                    psycopg.Error,
                    GoogleGenAIAPIError,
                    httpx.RequestError,
                    TimeoutError,
                    ConnectionError,
                ) as error:
                    show_processing_error(
                        action_label,
                        friendly_message,
                        error,
                        status,
                    )
                else:
                    st.session_state.pending_interrupt = pending_interrupt
                    if pending_interrupt is None:
                        response = get_latest_assistant_text(state, streamed_text)
                        if response:
                            if not streamed_text:
                                st.markdown(response)
                            st.session_state.messages.append(
                                {"role": "assistant", "content": response}
                            )
                    status.update(
                        label=(
                            "Approval required"
                            if pending_interrupt
                            else "Decision processed"
                        ),
                        state="complete",
                        expanded=True,
                    )
                    st.rerun()


if not st.session_state.pending_interrupt:
    prompt = st.chat_input(
        "Ask about an order, shipping, returns, refunds..."
    )

    if prompt:
        safe_prompt = sanitize_pii(prompt)
        st.session_state.messages.append(
            {"role": "user", "content": safe_prompt}
        )

        with st.chat_message("user"):
            st.markdown(safe_prompt)

        with st.chat_message("assistant"):
            with st.status("Thinking...", expanded=True) as status:
                try:
                    streamed_text, graph_output = stream_graph(
                        {"messages": [HumanMessage(content=safe_prompt)]},
                        config,
                        status,
                    )
                    state = get_graph().get_state(config)
                    pending_interrupt = get_pending_interrupt(graph_output, state)
                except (
                    requests.RequestException,
                    psycopg.Error,
                    GoogleGenAIAPIError,
                    httpx.RequestError,
                    TimeoutError,
                    ConnectionError,
                ) as error:
                    show_processing_error(
                        "Failed to process customer message",
                        "Sorry, the service is temporarily unavailable. Please try again.",
                        error,
                        status,
                    )
                else:
                    if pending_interrupt is not None:
                        st.session_state.pending_interrupt = pending_interrupt
                        status.update(
                            label="Approval required",
                            state="complete",
                            expanded=False,
                        )
                        st.rerun()

                    response = get_latest_assistant_text(state, streamed_text)
                    if response:
                        if not streamed_text:
                            st.markdown(response)
                        st.session_state.messages.append(
                            {"role": "assistant", "content": response}
                        )
                    status.update(
                        label="Response ready",
                        state="complete",
                        expanded=True,
                    )
