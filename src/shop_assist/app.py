import uuid
import logging

import streamlit as st
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.types import Command

from shop_assist.db import (
    get_checkpointer,
    get_conversations,
)
from shop_assist.graph import build_graph
from shop_assist.logging_config import configure_logging


configure_logging()

logger = logging.getLogger(__name__)


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="ShopAssist",
    page_icon="🛍️",
    layout="centered",
)


# =========================================================
# HELPERS
# =========================================================

def content_to_text(content) -> str:
    """
    Convert LangChain/Gemini message content into plain text.

    Gemini can return content as either:

        "plain text"

    or:

        [
            {"type": "text", "text": "plain text"}
        ]
    """

    if isinstance(content, str):
        return content

    if isinstance(content, list):
        text_parts = []

        for block in content:

            if isinstance(block, str):
                text_parts.append(block)

            elif isinstance(block, dict):

                if block.get("type") == "text":
                    text = block.get("text")

                    if text:
                        text_parts.append(text)

        return "\n".join(text_parts)

    return str(content)


def run_graph(input_data, config):
    try:
        with get_checkpointer() as checkpointer:
            graph = build_graph(checkpointer)
            return graph.invoke(input_data, config)

    except Exception:
        logger.exception("Graph execution failed")
        raise


def load_conversation(config):
    """
    Load the latest conversation state from PostgreSQL.
    """

    with get_checkpointer() as checkpointer:

        graph = build_graph(checkpointer)

        state = graph.get_state(config)

        if state.values:
            return state.values.get(
                "messages",
                []
            )

    return []


def new_conversation_id():
    return f"conversation-{uuid.uuid4().hex[:12]}"


def load_messages_for_ui(config):

    persisted_messages = load_conversation(config)

    messages = []

    for message in persisted_messages:

        if isinstance(message, HumanMessage):

            text = content_to_text(message.content)

            if text:
                messages.append(
                    {
                        "role": "user",
                        "content": text,
                    }
                )

        elif isinstance(message, AIMessage):

            text = content_to_text(message.content)

            if text:
                messages.append(
                    {
                        "role": "assistant",
                        "content": text,
                    }
                )

    return messages


# =========================================================
# CONVERSATION INITIALIZATION
# =========================================================

if "conversation_id" not in st.session_state:

    conversation_id = st.query_params.get(
        "conversation_id"
    )

    if not conversation_id:
        conversation_id = new_conversation_id()

        st.query_params["conversation_id"] = (
            conversation_id
        )

    st.session_state.conversation_id = conversation_id


conversation_id = st.session_state.conversation_id

config = {
    "configurable": {
        "thread_id": conversation_id
    }
}


# =========================================================
# LOAD CURRENT CONVERSATION
# =========================================================

if "messages" not in st.session_state:

    st.session_state.messages = (
        load_messages_for_ui(config)
    )


if "pending_interrupt" not in st.session_state:

    st.session_state.pending_interrupt = None


# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:

    st.title("🛍️ ShopAssist")

    if st.button(
        "＋ New conversation",
        use_container_width=True,
    ):

        conversation_id = new_conversation_id()

        st.session_state.conversation_id = (
            conversation_id
        )

        st.session_state.messages = []

        st.session_state.pending_interrupt = None

        st.query_params["conversation_id"] = (
            conversation_id
        )

        st.rerun()

    st.divider()

    st.subheader("Saved conversations")

    conversations = get_conversations()

    current_thread_found = False

    for conversation in conversations:

        thread_id = conversation["thread_id"]

        title = conversation["title"]

        if thread_id == conversation_id:
            current_thread_found = True

        # Keep sidebar titles short.
        display_title = title

        if len(display_title) > 42:
            display_title = display_title[:42] + "..."

        is_current = thread_id == conversation_id

        button_label = (
            f"● {display_title}"
            if is_current
            else display_title
        )

        if st.button(
            button_label,
            key=f"conversation-{thread_id}",
            use_container_width=True,
        ):

            st.session_state.conversation_id = (
                thread_id
            )

            st.session_state.messages = (
                load_messages_for_ui(
                    {
                        "configurable": {
                            "thread_id": thread_id
                        }
                    }
                )
            )

            st.session_state.pending_interrupt = None

            st.query_params["conversation_id"] = (
                thread_id
            )

            st.rerun()

    if not conversations:

        st.caption(
            "No saved conversations yet."
        )

    st.divider()

    st.caption(
        f"Conversation ID: {conversation_id}"
    )


# =========================================================
# HEADER
# =========================================================

st.title("Customer Support")

st.caption(
    "AI customer support for the Cogent Shopify store."
)


# =========================================================
# DISPLAY CURRENT CONVERSATION
# =========================================================

for message in st.session_state.messages:

    with st.chat_message(message["role"]):

        st.markdown(
            message["content"]
        )


# =========================================================
# HITL APPROVAL
# =========================================================

if st.session_state.pending_interrupt:

    interrupt_data = (
        st.session_state.pending_interrupt
    )

    order = interrupt_data["order"]

    st.warning(
        "Human approval required"
    )

    st.markdown(
        f"""
### Cancel order #{interrupt_data["order_number"]}

**Created:** {order["created_at"]}

**Financial status:** {order["financial_status"]}

**Fulfillment status:** {order["fulfillment_status"]}

**Refund:** {interrupt_data["refund"]}

**Restock inventory:** {interrupt_data["restock"]}

**Notify customer:** {interrupt_data["notify_customer"]}
"""
    )

    st.write("Items:")

    for item in order["items"]:

        st.write(
            f"- {item['name']} × {item['quantity']}"
        )

    col1, col2 = st.columns(2)

    with col1:

        approve = st.button(
            "✅ Approve cancellation",
            use_container_width=True,
        )

    with col2:

        reject = st.button(
            "❌ Reject",
            use_container_width=True,
        )

    # -----------------------------------------------------
    # APPROVE CANCELLATION
    # -----------------------------------------------------

    if approve:

        try:

            with st.spinner(
                "Processing cancellation..."
            ):

                result = run_graph(
                    Command(
                        resume={
                            "action": "approve"
                        }
                    ),
                    config,
                )

        except Exception:

            logger.exception(
                "Failed to process approved cancellation"
            )

            st.error(
                "Sorry, the cancellation could not be "
                "processed. Please try again."
            )

        else:

            st.session_state.pending_interrupt = None

            response = content_to_text(
                result["messages"][-1].content
            )

            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": response,
                }
            )

            st.rerun()

    # -----------------------------------------------------
    # REJECT CANCELLATION
    # -----------------------------------------------------

    if reject:

        try:

            with st.spinner(
                "Rejecting cancellation..."
            ):

                result = run_graph(
                    Command(
                        resume={
                            "action": "reject"
                        }
                    ),
                    config,
                )

        except Exception:

            logger.exception(
                "Failed to process rejected cancellation"
            )

            st.error(
                "Sorry, we could not process your "
                "cancellation decision. Please try again."
            )

        else:

            st.session_state.pending_interrupt = None

            response = content_to_text(
                result["messages"][-1].content
            )

            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": response,
                }
            )

            st.rerun()


# =========================================================
# CHAT INPUT
# =========================================================

if not st.session_state.pending_interrupt:

    prompt = st.chat_input(
        "Ask about an order, shipping, returns, refunds..."
    )

    if prompt:

        st.session_state.messages.append(
            {
                "role": "user",
                "content": prompt,
            }
        )

        with st.chat_message("user"):

            st.markdown(prompt)

        with st.chat_message("assistant"):

            try:

                with st.spinner("Thinking..."):

                    result = run_graph(
                        {
                            "messages": [
                                HumanMessage(
                                    content=prompt
                                )
                            ]
                        },
                        config,
                    )

            except Exception:

                logger.exception(
                    "Failed to process customer message"
                )

                st.error(
                    "Sorry, something went wrong while "
                    "processing your request. Please try again."
                )

            else:

                # -----------------------------------------
                # HITL interrupt
                # -----------------------------------------

                if "__interrupt__" in result:

                    interrupt_data = (
                        result[
                            "__interrupt__"
                        ][0].value
                    )

                    st.session_state.pending_interrupt = (
                        interrupt_data
                    )

                    st.rerun()

                # -----------------------------------------
                # Normal response
                # -----------------------------------------

                else:

                    response = content_to_text(
                        result[
                            "messages"
                        ][-1].content
                    )

                    st.markdown(response)

                    st.session_state.messages.append(
                        {
                            "role": "assistant",
                            "content": response,
                        }
                    )