import os

import psycopg
from psycopg.rows import dict_row
import streamlit as st
from dotenv import load_dotenv
from langgraph.checkpoint.postgres import PostgresSaver

from shop_assist.utils import content_to_text

load_dotenv()

DATABASE_URL = os.environ["DATABASE_URL"]


@st.cache_resource
def get_checkpointer():
    connection = psycopg.connect(
        DATABASE_URL,
        autocommit=True,
        prepare_threshold=0,
        row_factory=dict_row,
    )
    checkpointer = PostgresSaver(connection)
    checkpointer.setup()
    return checkpointer


def get_conversations(limit: int = 100, user_session_id: str = "") -> list[dict]:
    """
    Return saved conversations owned by the current browser session.

    Each conversation is represented by its thread_id and
    the first user message, which is used as the title.
    """

    conversations = {}
    thread_prefix = f"{user_session_id}:"
    checkpointer = get_checkpointer()

    for checkpoint in checkpointer.list(None):
        configurable = checkpoint.config.get("configurable", {})
        thread_id = configurable.get("thread_id")

        if not thread_id or not thread_id.startswith(thread_prefix):
            continue

        # list() returns newest checkpoints first, so this is each thread's latest state.
        if thread_id in conversations:
            continue

        messages = checkpoint.checkpoint.get("channel_values", {}).get("messages", [])
        title = "New conversation"

        for message in messages:
            if getattr(message, "type", None) != "human":
                continue

            text = content_to_text(message.content).strip()
            if text:
                title = text
            break

        conversations[thread_id] = {
            "thread_id": thread_id,
            "title": title,
            "checkpoint_id": checkpoint.checkpoint.get("id"),
        }
        if len(conversations) >= limit:
            break

    return list(conversations.values())
