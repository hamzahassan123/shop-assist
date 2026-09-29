from shop_assist.tools import lookup_order


def main():
    result = lookup_order.invoke("1002")
    print(result)


if __name__ == "__main__":
    main()