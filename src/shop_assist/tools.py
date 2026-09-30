from langchain_core.tools import tool

from shop_assist.rag import get_vectorstore
from langgraph.types import interrupt
from shop_assist.shopify import (
    get_order,
    get_fulfillment,
    cancel_order as shopify_cancel_order,
)

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


@tool
def search_store_policy(query: str) -> str:
    """Search the store's policies for information about returns, refunds, shipping, cancellations, and other store rules."""

    vectorstore = get_vectorstore()

    documents = vectorstore.similarity_search(
        query,
        k=3,
    )

    if not documents:
        return "No relevant store policy information was found."

    return "\n\n".join(
        [
            f"Source: {document.metadata.get('source')}\n"
            f"{document.page_content}"
            for document in documents
        ]
    )


@tool
def cancel_shopify_order(
    order_number: str,
    reason: str = "CUSTOMER",
) -> dict:
    """
    Cancel a Shopify order.

    This action requires human approval before the cancellation is executed.
    """

    order = get_order(order_number)

    if order is None:
        return {
            "success": False,
            "message": f"Order #{order_number.lstrip('#')} was not found.",
        }

    approval = interrupt(
        {
            "action": "cancel_order",
            "order_number": order_number.lstrip("#"),
            "reason": reason,
            "order": order,
            "refund": "Original payment method",
            "restock": True,
            "notify_customer": True,
            "message": (
                f"Approve cancellation of order "
                f"#{order_number.lstrip('#')}?"
            ),
        }
    )

    if approval.get("action") != "approve":
        return {
            "success": False,
            "message": (
                f"Cancellation of order "
                f"#{order_number.lstrip('#')} was not approved."
            ),
        }

    return shopify_cancel_order(
        order_number=order_number,
        reason=reason,
        notify_customer=True,
        restock=True,
    )