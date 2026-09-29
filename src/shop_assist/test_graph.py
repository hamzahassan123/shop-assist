from shop_assist.graph import graph


def main():
    result = graph.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": "Where is my order #1002?"
                }
            ]
        }
    )

    print(result["messages"][-1].content)


if __name__ == "__main__":
    main()