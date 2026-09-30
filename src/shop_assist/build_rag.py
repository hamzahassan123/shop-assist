from shop_assist.rag import build_vectorstore


def main():
    vectorstore = build_vectorstore()

    print("Vector store created successfully.")

    results = vectorstore.similarity_search(
        "How long do customers have to return an item?",
        k=2,
    )

    for document in results:
        print("\n---")
        print(document.page_content)
        print("Source:", document.metadata.get("source"))


if __name__ == "__main__":
    main()