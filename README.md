# Telegram AI Chatbot (Rafflestag)

This project is a Telegram chatbot that uses:
- python-telegram-bot for Telegram messaging
- LangChain + Groq for LLM responses
- Custom tools to fetch product and price data from your API

## Project Structure

- agent.py: LLM setup, system prompt, and tool-calling agent
- bot.py: Telegram bot handlers and polling loop
- tools/product_details_tools.py: Product and price tool functions
- utils/memory.py: Per-user conversation memory
- debug_tools.py: Interactive step-by-step tool debugger
- requirements.txt: Python dependencies

## Prerequisites

- Windows PowerShell (recommended)
- Python 3.14 (currently used in this workspace)
- A Telegram bot token from BotFather
- A valid Groq API key
- Your product API running and reachable

## 1) Setup Virtual Environment

From project root:

    python -m venv venv
    .\venv\Scripts\Activate.ps1

If execution policy blocks activation:

    Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
    .\venv\Scripts\Activate.ps1

## 2) Install Dependencies

    .\venv\Scripts\python -m pip install --upgrade pip
    .\venv\Scripts\python -m pip install -r requirements.txt

## 3) Configure Environment Variables

Create a .env file in project root with values like:

    TELEGRAM_BOT_TOKEN=your_telegram_bot_token
    GROQ_API_KEY=your_groq_api_key
    WEBSITE_API_URL=http://127.0.0.1:8000
    WEBSITE_API_KEY=your_website_api_key
    BUSINESS_NAME=Rafflestag
    BUSINESS_DESCRIPTION=Rafflestag is an online platform for customizable products.

Important:
- Keep .env private (already ignored by .gitignore)
- Ensure WEBSITE_API_URL points to your running backend

## 4) Run the Telegram Bot

    .\venv\Scripts\python bot.py

Expected log when successful:
- Bot is running
- Application started
- getUpdates returns HTTP 200

## 5) Manual Tool Debugging (Interactive)

Use the interactive debugger to test tools step by step:

    .\venv\Scripts\python debug_tools.py

Menu options let you test:
- get_product_details
- get_price_details
- both in sequence

The debugger prints:
- Raw API request/response details
- Parsed JSON
- Tool wrapper output
- Any exception traceback

## Common Issues and Fixes

1. Telegram 409 Conflict
Cause: More than one bot process is running with the same token.
Fix:
- Stop all duplicate bot.py processes
- Run only one instance

2. Bot exits immediately
Check:
- TELEGRAM_BOT_TOKEN is set in .env
- .env is in project root
- You are running with the venv interpreter

3. Tool says API issue
Check:
- WEBSITE_API_URL is correct
- Backend API is running
- Use debug_tools.py to inspect raw API payload

4. Product tool works but price is empty
Usually backend data issue for selected style/size/qty.
Use debug_tools.py and test multiple style/size/qty combinations.

## Recommended Run Commands

Bot:

    .\venv\Scripts\python bot.py

Interactive tool debugger:

    .\venv\Scripts\python debug_tools.py

Quick import check:

    .\venv\Scripts\python -c "from agent import get_agent_response; print('Agent import OK')"

## Notes

- Logging is currently set to DEBUG in bot.py for troubleshooting.
- If logs are too noisy, change log level in bot.py to INFO.
- Restart the bot after code changes so updates are loaded.
