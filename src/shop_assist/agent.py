from langchain_google_genai import ChatGoogleGenerativeAI
from langhchain.agents import create_agent

from shop_assist.tools import lookup_order


llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0,
)

agent = create_agent(
    model=llm,
    tools=[lookup_order],
    system_prompt="""
You are a Shopify customer support assistant.

You help customers with questions about their orders.

When a customer asks about a specific order:
1. Identify the order number.
2. Use the lookup_order tool to retrieve the real Shopify order.
3. Base your answer on the returned data.
4. Never invent order information.
5. Clearly explain the order's financial and fulfillment status.
6. If the order cannot be found, say so clearly.

Keep responses concise and customer-friendly.
""",
)