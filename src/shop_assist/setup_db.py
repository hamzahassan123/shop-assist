from shop_assist.db import get_checkpointer


def main():
    get_checkpointer()

    print("PostgreSQL checkpointer setup complete.")


if __name__ == "__main__":
    main()