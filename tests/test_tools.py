from unittest.mock import patch

from shop_assist.tools import lookup_fulfillment, lookup_order


def test_lookup_order_returns_shopify_order():
    order = {"order_number": "#1001", "financial_status": "PAID"}
    with patch("shop_assist.tools.get_order", return_value=order) as get_order:
        result = lookup_order.invoke({"order_number": "#1001"})

    get_order.assert_called_once_with("#1001")
    assert result == {"found": True, "order": order}


def test_lookup_order_reports_missing_order():
    with patch("shop_assist.tools.get_order", return_value=None):
        result = lookup_order.invoke({"order_number": "#1001"})

    assert result == {
        "found": False,
        "message": "Order #1001 was not found.",
    }


def test_lookup_fulfillment_returns_tracking_information():
    fulfillment = {"order_number": "#1001", "fulfillment_status": "FULFILLED"}
    with patch(
        "shop_assist.tools.get_fulfillment",
        return_value=fulfillment,
    ) as get_fulfillment:
        result = lookup_fulfillment.invoke({"order_number": "#1001"})

    get_fulfillment.assert_called_once_with("#1001")
    assert result == {"found": True, "fulfillment": fulfillment}


def test_lookup_fulfillment_reports_missing_order():
    with patch("shop_assist.tools.get_fulfillment", return_value=None):
        result = lookup_fulfillment.invoke({"order_number": "#1001"})

    assert result == {
        "found": False,
        "message": "Order #1001 was not found.",
    }
