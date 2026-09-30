from langgraph.types import Command

from shop_assist.db import get_checkpointer
from shop_assist.graph import build_graph


def main():
    conversation_id = "hitl-test-001"

    config = {
        "configurable": {
            "thread_id": conversation_id
        }
    }

    with get_checkpointer() as checkpointer:
        graph = build_graph(checkpointer)

        # Step 1: customer requests cancellation
        result = graph.invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": "I want to cancel order #1004."
                    }
                ]
            },
            config,
        )

        if "__interrupt__" in result:
            interrupt_data = result["__interrupt__"][0].value

            print("\n--- HUMAN APPROVAL REQUIRED ---")
            print(f"Order: #{interrupt_data['order_number']}")
            print(f"Reason: {interrupt_data['reason']}")
            print(f"Refund: {interrupt_data['refund']}")
            print(f"Restock: {interrupt_data['restock']}")
            print(f"Notify customer: {interrupt_data['notify_customer']}")

            approval = input("\nApprove cancellation? (yes/no): ").strip().lower()

            if approval == "yes":
                result = graph.invoke(
                    Command(
                        resume={
                            "action": "approve"
                        }
                    ),
                    config,
                )

                print("\n--- FINAL RESPONSE ---")
                print(result["messages"][-1].content)

            else:
                result = graph.invoke(
                    Command(
                        resume={
                            "action": "reject"
                        }
                    ),
                    config,
                )

                print("\n--- FINAL RESPONSE ---")
                print(result["messages"][-1].content)


if __name__ == "__main__":
    main()