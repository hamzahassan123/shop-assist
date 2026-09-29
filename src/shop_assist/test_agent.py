from shop_assist.agent import agent


def main():
    result = agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": "What's happening with order #1002?"
                }
            ]
        }
    )

    print(result["messages"][-1].content)


if __name__ == "__main__":
    main()