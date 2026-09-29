import os

from langgraph.checkpoint.postgres import PostgresSaver
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ["DATABASE_URL"]


def get_checkpointer():
    return PostgresSaver.from_conn_string(DATABASE_URL)