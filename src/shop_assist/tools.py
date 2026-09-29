from langchain_core.tools import tool

from shop_assist.shopify import get_fulfillment, get_order


@tool
def lookup_order(order_number: str) -> dict:
    """Look up a Shopify order by its order number."""

    order = get_order(order_number)

    if order is None:
        return {
            "found": False,
            "message": f"Order #{order_number.lstrip('#')} was not found.",
        }

    return {
        "found": True,
        "order": order,
    }


@tool
def lookup_fulfillment(order_number: str) -> dict:
    """Look up the fulfillment and tracking information for a Shopify order."""

    fulfillment = get_fulfillment(order_number)

    if fulfillment is None:
        return {
            "found": False,
            "message": f"Order #{order_number.lstrip('#')} was not found.",
        }

    return {
        "found": True,
        "fulfillment": fulfillment,
    }