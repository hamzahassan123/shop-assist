from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage

import shop_assist.graph as graph_module


class FakeStreamingModel(BaseChatModel):
    @property
    def _llm_type(self):
        return "fake"

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        return ChatResult(
            generations=[ChatGeneration(message=AIMessage(content="Hello there"))]
        )

    def _stream(self, messages, stop=None, run_manager=None, **kwargs):
        yield ChatGenerationChunk(message=AIMessageChunk(content="Hello "))
        yield ChatGenerationChunk(message=AIMessageChunk(content="there"))


def test_graph_streams_tokens_with_sync_checkpointer(monkeypatch):
    monkeypatch.setattr(graph_module, "llm_with_tools", FakeStreamingModel())
    graph = graph_module.build_graph(MemorySaver())

    events = graph.stream(
        {"messages": [HumanMessage(content="Hi")]},
        {"configurable": {"thread_id": "sync-stream-test"}},
        stream_mode=["messages", "updates"],
        version="v2",
    )

    tokens = [
        event["data"][0].content
        for event in events
        if event["type"] == "messages"
        and event["data"][1].get("langgraph_node") == "agent"
        and event["data"][0].content
    ]

    assert "".join(tokens) == "Hello there"
