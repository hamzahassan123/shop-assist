import os

import requests
from dotenv import load_dotenv


load_dotenv()


SHOP = os.environ["SHOPIFY_SHOP"]
CLIENT_ID = os.environ["SHOPIFY_CLIENT_ID"]
CLIENT_SECRET = os.environ["SHOPIFY_CLIENT_SECRET"]


def get_access_token() -> str:
    url = f"https://{SHOP}.myshopify.com/admin/oauth/access_token"

    response = requests.post(
        url,
        data={
            "grant_type": "client_credentials",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
        },
        timeout=30,
    )

    response.raise_for_status()

    data = response.json()

    return data["access_token"]


def shopify_graphql(query: str, variables: dict | None = None) -> dict:
    access_token = get_access_token()

    url = f"https://{SHOP}.myshopify.com/admin/api/2026-07/graphql.json"

    response = requests.post(
        url,
        headers={
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": access_token,
        },
        json={
            "query": query,
            "variables": variables or {},
        },
        timeout=30,
    )

    response.raise_for_status()

    return response.json()

def get_orders(first: int = 10) -> dict:
    query = """
    query GetOrders($first: Int!) {
        orders(first: $first) {
            edges {
                node {
                    id
                    name
                    createdAt
                    displayFinancialStatus
                    displayFulfillmentStatus
                }
            }
        }
    }
    """

    return shopify_graphql(
        query,
        variables={"first": first},
    )

def get_order(order_number: str) -> dict | None:
    query = """
    query GetOrder($query: String!) {
        orders(first: 1, query: $query) {
            edges {
                node {
                    id
                    name
                    createdAt
                    displayFinancialStatus
                    displayFulfillmentStatus

                    customer {
                        id
                    }

                    lineItems(first: 20) {
                        edges {
                            node {
                                name
                                quantity
                            }
                        }
                    }

                    fulfillments {
                        status
                        trackingInfo {
                            company
                            number
                            url
                        }
                    }
                }
            }
        }
    }
    """

    result = shopify_graphql(
        query,
        variables={
            "query": f"name:#{order_number.lstrip('#')}"
        },
    )

    edges = result["data"]["orders"]["edges"]

    if not edges:
        return None

    order = edges[0]["node"]

    return {
        "id": order["id"],
        "order_number": order["name"],
        "created_at": order["createdAt"],
        "financial_status": order["displayFinancialStatus"],
        "fulfillment_status": order["displayFulfillmentStatus"],
        "customer_id": order["customer"]["id"] if order["customer"] else None,
        "items": [
            {
                "name": item["node"]["name"],
                "quantity": item["node"]["quantity"],
            }
            for item in order["lineItems"]["edges"]
        ],
        "fulfillments": [
            {
                "status": fulfillment["status"],
                "tracking": fulfillment["trackingInfo"],
            }
            for fulfillment in order["fulfillments"]
        ],
    }



def get_fulfillment(order_number: str) -> dict | None:
    query = """
    query GetOrderFulfillment($query: String!) {
        orders(first: 1, query: $query) {
            edges {
                node {
                    name
                    displayFulfillmentStatus

                    fulfillments {
                        status
                        trackingInfo {
                            company
                            number
                            url
                        }
                    }
                }
            }
        }
    }
    """

    result = shopify_graphql(
        query,
        variables={
            "query": f"name:#{order_number.lstrip('#')}"
        },
    )

    edges = result["data"]["orders"]["edges"]

    if not edges:
        return None

    order = edges[0]["node"]

    return {
        "order_number": order["name"],
        "fulfillment_status": order["displayFulfillmentStatus"],
        "fulfillments": [
            {
                "status": fulfillment["status"],
                "tracking": fulfillment["trackingInfo"],
            }
            for fulfillment in order["fulfillments"]
        ],
    }