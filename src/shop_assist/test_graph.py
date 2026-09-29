from shop_assist.db import get_checkpointer
from shop_assist.graph import build_graph


def main():
    conversation_id = "demo-conversation-002"

    config = {
        "configurable": {
            "thread_id": conversation_id
        }
    }

    with get_checkpointer() as checkpointer:
        graph = build_graph(checkpointer)

        result = graph.invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": "what is the status of order #1003?",
                    }
                ]
            },
            config,
        )

        print(result["messages"][-1].content)


if __name__ == "__main__":
    main()