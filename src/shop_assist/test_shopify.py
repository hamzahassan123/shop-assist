from shop_assist.shopify import get_order


def main():
    order = get_order("1002")
    print(order)


if __name__ == "__main__":
    main()