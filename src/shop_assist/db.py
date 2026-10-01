import os

from dotenv import load_dotenv
from langgraph.checkpoint.postgres import PostgresSaver

load_dotenv()

DATABASE_URL = os.environ["DATABASE_URL"]


def get_checkpointer():
    return PostgresSaver.from_conn_string(DATABASE_URL)


def get_conversations(limit: int = 100) -> list[dict]:
    """
    Return saved conversations from PostgreSQL.

    Each conversation is represented by its thread_id and
    the first user message, which is used as the title.
    """

    conversations = {}

    with get_checkpointer() as checkpointer:

        for checkpoint in checkpointer.list(None, limit=limit):

            configurable = checkpoint.config.get(
                "configurable",
                {}
            )

            thread_id = configurable.get("thread_id")

            if not thread_id:
                continue

            # list() returns newest checkpoints first.
            # Therefore the first checkpoint we encounter for
            # a thread is its latest state.
            if thread_id in conversations:
                continue

            messages = checkpoint.checkpoint.get(
                "channel_values",
                {}
            ).get(
                "messages",
                []
            )

            title = "New conversation"

            for message in messages:

                if getattr(message, "type", None) == "human":

                    content = message.content

                    if isinstance(content, str) and content.strip():
                        title = content.strip()
                        break

                    if isinstance(content, list):
                        for block in content:
                            if (
                                isinstance(block, dict)
                                and block.get("type") == "text"
                            ):
                                text = block.get("text", "").strip()

                                if text:
                                    title = text
                                    break

                    if title != "New conversation":
                        break

            conversations[thread_id] = {
                "thread_id": thread_id,
                "title": title,
                "checkpoint_id": checkpoint.checkpoint.get("id"),
            }

    return list(conversations.values())