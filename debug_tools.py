#!/usr/bin/env python3
"""
Interactive debug tool for manual testing of product and price tools.
Input parameters, see step-by-step debug output, and inspect results.
"""

import json
import sys
from typing import Any

import requests
from dotenv import load_dotenv

from tools.product_details_tools import (
    API_BASE_URL,
    get_price_details,
    get_product_details,
    _get_product_details,
    _get_price_details,
)


def print_section(title: str, char: str = "=") -> None:
    """Print a section header."""
    print(f"\n{char * 60}")
    print(f"  {title}")
    print(f"{char * 60}\n")


def print_debug(label: str, value: Any, indent: int = 0) -> None:
    """Print debug output with optional indentation."""
    prefix = "  " * indent + "→ "
    if isinstance(value, (dict, list)):
        print(f"{prefix}{label}:")
        print(json.dumps(value, indent=2, ensure_ascii=False))
    else:
        print(f"{prefix}{label}: {value}")


def test_product_details(slug: str, origin: str = "3") -> dict | None:
    """Test get_product_details tool with debug output."""
    print_section("PRODUCT DETAILS TEST", "=")
    print(f"Input Parameters:")
    print(f"  slug: {slug}")
    print(f"  origin: {origin}")

    # Step 1: Raw API call
    print_section("STEP 1: Raw API Call", "-")
    api_url = f"{API_BASE_URL}/api/public/get-product/{slug}"
    print_debug("URL", api_url)
    print_debug("Headers", {"Accept": "application/json", "origin": origin})

    try:
        response = requests.get(
            api_url,
            headers={"Accept": "application/json", "origin": origin},
            timeout=20,
        )
    except Exception as exc:
        print(f"[ERROR] Request failed: {exc}")
        return None

    print_debug("Status Code", response.status_code)
    print_debug("Response Headers", dict(response.headers))

    # Step 2: Parse JSON
    print_section("STEP 2: Parse Response Body", "-")
    try:
        response_json = response.json()
        print_debug("Parsed JSON", response_json)
    except Exception as exc:
        print(f"[ERROR] Failed to parse JSON: {exc}")
        print_debug("Raw Text", response.text)
        return None

    # Step 3: Extract data
    print_section("STEP 3: Extract Data Field", "-")
    success = response_json.get("success")
    message = response_json.get("message")
    data = response_json.get("data", {})

    print_debug("success", success)
    print_debug("message", message)
    print_debug("data type", type(data).__name__)
    if isinstance(data, dict):
        print_debug("data keys", list(data.keys()))
        print_debug("product name", data.get("name"))
        print_debug("product slug", data.get("slug"))
        print_debug("category", data.get("category"))

    # Step 4: Call tool
    print_section("STEP 4: Call Tool Wrapper", "-")
    try:
        tool_output = get_product_details.invoke({"slug": slug})
        print_debug("Tool Output Type", type(tool_output).__name__)
        print_debug("Tool Output Length", len(tool_output) if isinstance(tool_output, str) else "N/A")
        print(f"\n{tool_output}\n")
    except Exception as exc:
        print(f"[ERROR] Tool failed: {exc}")
        import traceback
        traceback.print_exc()
        return None

    return response_json.get("data")


def test_price_details(slug: str, style: str, size: str, qty: int, origin: str = "3") -> None:
    """Test get_price_details tool with debug output."""
    print_section("PRICE DETAILS TEST", "=")
    print(f"Input Parameters:")
    print(f"  slug: {slug}")
    print(f"  style: {style}")
    print(f"  size: {size}")
    print(f"  qty: {qty}")
    print(f"  origin: {origin}")

    # Step 1: Build URL
    print_section("STEP 1: Build Request", "-")
    api_url = f"{API_BASE_URL}/api/public/get-product-price/{slug}"
    params = {"style": style, "size": size, "qty": qty}
    print_debug("Base URL", api_url)
    print_debug("Query Parameters", params)
    print_debug("Headers", {"Accept": "application/json", "origin": origin})

    # Step 2: Raw API call
    print_section("STEP 2: Raw API Call", "-")
    try:
        response = requests.get(
            api_url,
            params=params,
            headers={"Accept": "application/json", "origin": origin},
            timeout=20,
        )
    except Exception as exc:
        print(f"[ERROR] Request failed: {exc}")
        return

    print_debug("Status Code", response.status_code)
    print_debug("Full URL", response.url)
    print_debug("Response Headers", dict(response.headers))

    # Step 3: Parse JSON
    print_section("STEP 3: Parse Response Body", "-")
    try:
        response_json = response.json()
        print_debug("Parsed JSON Keys", list(response_json.keys()) if isinstance(response_json, dict) else "N/A")
    except Exception as exc:
        print(f"[ERROR] Failed to parse JSON: {exc}")
        print_debug("Raw Text", response.text)
        return

    # Step 4: Inspect data field
    print_section("STEP 4: Inspect Data Field", "-")
    success = response_json.get("success")
    message = response_json.get("message")
    data = response_json.get("data", [])

    print_debug("success", success)
    print_debug("message", message)
    print_debug("data type", type(data).__name__)
    print_debug("data length", len(data) if isinstance(data, (list, dict)) else "N/A")

    if isinstance(data, list):
        print_debug("data (first 3 items)", data[:3] if len(data) > 3 else data)
        if data:
            print(f"\nData preview:\n{json.dumps(data[:1], indent=2)}\n")
    else:
        print_debug("data", data)

    # Step 5: Call tool
    print_section("STEP 5: Call Tool Wrapper", "-")
    try:
        tool_output = get_price_details.invoke({"slug": slug, "style": style, "size": size, "qty": qty})
        print_debug("Tool Output Type", type(tool_output).__name__)
        print_debug("Tool Output Length", len(tool_output) if isinstance(tool_output, str) else "N/A")
        print(f"\n{tool_output}\n")
    except Exception as exc:
        print(f"[ERROR] Tool failed: {exc}")
        import traceback
        traceback.print_exc()


def interactive_menu() -> None:
    """Run interactive debug menu."""
    load_dotenv()

    while True:
        print_section("DEBUG TOOL MENU", "=")
        print("1. Test get_product_details")
        print("2. Test get_price_details")
        print("3. Test both (requires valid style/size)")
        print("4. Exit")
        print()

        choice = input("Enter choice (1-4): ").strip()

        if choice == "1":
            slug = input("Enter product slug (e.g., lanyard): ").strip()
            if slug:
                product_data = test_product_details(slug)
                if product_data:
                    print_section("Extracted Product Data", "-")
                    print_debug("Product Name", product_data.get("name"))
                    print_debug("Product Slug", product_data.get("slug"))
        elif choice == "2":
            slug = input("Enter product slug: ").strip()
            style = input("Enter style: ").strip()
            size = input("Enter size: ").strip()
            qty_str = input("Enter quantity (default 100): ").strip()
            qty = int(qty_str) if qty_str.isdigit() else 100

            if slug and style and size:
                test_price_details(slug, style, size, qty)

        elif choice == "3":
            slug = input("Enter product slug: ").strip()
            if slug:
                product_data = test_product_details(slug)
                if product_data:
                    print_section("Now Testing Price Details", "-")
                    style = input("Enter style: ").strip()
                    size = input("Enter size: ").strip()
                    qty_str = input("Enter quantity (default 100): ").strip()
                    qty = int(qty_str) if qty_str.isdigit() else 100

                    if style and size:
                        test_price_details(slug, style, size, qty)

        elif choice == "4":
            print("Exiting...")
            break
        else:
            print("Invalid choice. Try again.")

        another = input("\nRun another test? (y/n): ").strip().lower()
        if another != "y":
            break


if __name__ == "__main__":
    try:
        interactive_menu()
    except KeyboardInterrupt:
        print("\n\nExiting...")
        sys.exit(0)
