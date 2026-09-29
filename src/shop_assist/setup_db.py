from shop_assist.db import get_checkpointer


def main():
    with get_checkpointer() as checkpointer:
        checkpointer.setup()

    print("PostgreSQL checkpointer setup complete.")


if __name__ == "__main__":
    main()