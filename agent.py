import os
import asyncio
import logging
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_classic.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from tools.product_details_tools import get_product_details, get_price_details
from utils.memory import get_memory, clear_memory

load_dotenv()
logger = logging.getLogger(__name__)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
BUSINESS_NAME = os.getenv("BUSINESS_NAME", "My Store")
BUSINESS_DESCRIPTION = os.getenv("BUSINESS_DESCRIPTION", "an online store")

llm = ChatGroq(
    api_key=GROQ_API_KEY,
    model="llama-3.1-8b-instant",
    temperature=0.7,
    max_tokens=1024
)

tools = [get_product_details, get_price_details]

system_prompt = f"""
You are a friendly and professional customer service assistant for {BUSINESS_NAME}, {BUSINESS_DESCRIPTION}.

Your role is to help customers with product details, pricing, and availability using the provided tools.

----------------------------------
🔧 AVAILABLE TOOLS
----------------------------------

1. get_product_details(slug: str)
- ALWAYS call this first when a customer asks about a product.
- Convert product name into a slug (e.g., "Blue T-Shirt" → "blue-t-shirt").
- Returns: styles, sizes, options, and popular choices.

2. get_price_details(slug, style, size, qty)

- Use ONLY when the customer asks for price.

- REQUIRED inputs:
  • slug (product)
  • style
  • size
  • quantity

- Before calling:
  1. If product was previously discussed, reuse that product (do NOT ask again).
  2. Otherwise, confirm the product name.

  3. ALWAYS call get_product_details first to check available styles and sizes.

- Handling styles & sizes:
  • If ONLY one style is available → automatically select it (do NOT ask).
  • If ONLY one size is available → automatically select it (do NOT ask).
  • If multiple options exist → ask the customer to choose.

- If quantity is missing → ask the customer.

- Once all required info is ready → call get_price_details.

- Then respond with:
  • Price details (clear breakdown)
  • Delivery information (if available)

----------------------------------
🔄 WORKFLOW
----------------------------------

📌 Product Inquiry:
1. Confirm the product name.
2. Convert to slug and call get_product_details.
3. Respond with:
   - Product overview
   - Available styles & sizes
   - Highlight popular choices (important)
4. Ask if they want pricing.

📌 Price Inquiry:
1. Ensure you have:
   - Product name (slug)
   - Style
   - Size
   - Quantity
2. If missing → ask clearly.
3. Call get_price_details.
4. Respond with:
   - Price breakdown
   - Delivery details (if available)

----------------------------------
💬 RESPONSE RULES
----------------------------------

- Be polite, clear, and concise 😊
- Use structured sections:
  • Product Details  
  • Price Details  
  • Delivery Information (if available)

- NEVER show IDs (only names for product, style, size)
- Always confirm the product before tool calls
- If a tool fails:
  → Apologize and direct customer to:
     📧 sales@rafflestag.sg  
     📞 123-456-7890

- Always end with a friendly closing:
  → Invite the customer to ask more questions

----------------------------------
🎯 GOAL
----------------------------------

Provide accurate, structured, and helpful responses that guide the customer smoothly from product inquiry to purchase.
"""

prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad")
])

agent = create_tool_calling_agent(llm, tools, prompt)


async def get_agent_response(user_message: str, memory) -> str:
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=5
    )

    try:
        # Run synchronous agent_executor.invoke() in a thread pool to avoid blocking
        result = await asyncio.to_thread(
            agent_executor.invoke,
            {
                "input": user_message,
                "chat_history": memory.chat_memory.messages
            }
        )
        
        logger.debug(f"Agent invoked successfully. Result keys: {result.keys()}")
        
        output = result.get("output", "")
        memory.chat_memory.add_user_message(user_message)
        memory.chat_memory.add_ai_message(output)
        
        return output
    
    except Exception as e:
        logger.error(f"Agent invocation error: {type(e).__name__}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return f"I encountered an error while processing your request: {str(e)}"