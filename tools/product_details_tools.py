import os
import logging
from langchain.tools import tool
import requests
import re
import argparse
from html import unescape
from datetime import date, datetime, timedelta

logger = logging.getLogger(__name__)
API_BASE_URL = os.getenv("WEBSITE_API_URL", "http://127.0.0.1:8000")


def _strip_html(value: str | None) -> str:
    if not value:
        return ""
    text = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", unescape(text)).strip()


def _format_size_label(size: dict) -> str:
    name = size.get("name")
    if name:
        return str(name)

    dims = [size.get("dimension_1"), size.get("dimension_2"), size.get("dimension_3")]
    dims = [str(d) for d in dims if d not in (None, "")]
    unit = str(size.get("unit") or "").strip()
    if dims:
        return f"{' x '.join(dims)} {unit}".strip()
    return "N/A"


def _build_prompt_text(api_payload: dict) -> str:
    data = api_payload.get("data", {}) if isinstance(api_payload, dict) else {}
    if not data:
        return "No product data found in API response."

    product_name = data.get("name", "Unknown")
    product_slug = data.get("slug", "")
    popular_style_id = data.get("most_popular_style_id", "")

    category = data.get("category", {}) if isinstance(data.get("category"), dict) else {}
    category_name = category.get("name", "")

    styles = data.get("styles", []) if isinstance(data.get("styles"), list) else []
    popular_style = next((s for s in styles if isinstance(s, dict) and s.get("id") == popular_style_id), None)
    popular_size_id = popular_style.get("most_popular_size", "") if popular_style else ""
    popular_style_name = popular_style.get("name", "") if popular_style else ""
    style_names = [s.get("name") for s in styles if isinstance(s, dict) and s.get("name")]

    product_sizes = []
    if popular_style and isinstance(popular_style.get("sizes"), list):
        product_sizes = popular_style.get("sizes", [])
    popular_size_name = (
        next(
            (
                _format_size_label(s)
                for s in product_sizes
                if isinstance(s, dict) and s.get("id") == popular_size_id
            ),
            "",
        )
        if popular_size_id
        else ""
    )

    style_size_details = []
    for style in styles:
        if not isinstance(style, dict):
            continue
        style_name = style.get("name") or "Unknown Style"
        nested_sizes = style.get("sizes", []) if isinstance(style.get("sizes"), list) else []
        formatted_sizes = []
        for size in nested_sizes:
            if not isinstance(size, dict):
                continue
            size_id = size.get("id", "N/A")
            dimension = size.get("dimension_1")
            unit = size.get("unit") or ""
            if dimension:
                formatted_sizes.append(f"{size_id}:{dimension}{unit}")
            else:
                formatted_sizes.append(str(size_id))
        if formatted_sizes:
            style_size_details.append(f"{style_name} -> {', '.join(formatted_sizes)}")

    holidays = data.get("holidays", []) if isinstance(data.get("holidays"), list) else []
    holiday_names = [
        f"{h.get('name')} ({h.get('date') or h.get('day')})" if (h.get("date") or h.get("day")) else h.get("name")
        for h in holidays
        if isinstance(h, dict) and h.get("name")
    ]

    meta_list = data.get("meta_description", []) if isinstance(data.get("meta_description"), list) else []
    meta_title = ""
    meta_description = ""
    if meta_list and isinstance(meta_list[0], dict):
        meta_title = meta_list[0].get("meta_title", "")
        meta_description = meta_list[0].get("meta_description", "")

    lines = [
        "Product Context for Assistant:",
        f"Product Name: {product_name}",
        f"Slug: {product_slug}",
    ]

    if category_name:
        lines.append(f"Category: {category_name}")
    if meta_title:
        lines.append(f"SEO Title: {meta_title}")
    if meta_description:
        lines.append(f"SEO Description: {meta_description}")
    if style_names:
        lines.append(f"Available Styles: {', '.join(style_names[:10])}")
    if style_size_details:
        lines.append(f"Style Size Details: {' | '.join(style_size_details[:10])}")
    if holiday_names:
        lines.append(f"Holiday Constraints: {', '.join(holiday_names[:10])}")
        lines.append(f"Holiday Details: {', '.join(holiday_names[:20])}")
    if popular_style_id or popular_style_name or popular_size_id:
        lines.append(
            "Popular Details: "
            f"Style ID: {popular_style_id or 'N/A'}, "
            f"Style Name: {popular_style_name or 'N/A'}, "
            f"Popular Size Name: {popular_size_name or 'N/A'}"
        )

    lines.append("Instruction: Use only this product context when answering product price questions.")
    return "\n".join(lines)


def _get_product_details(slug: str, origin: str | None = None) -> str:
    """
    Fetch product details using the Api endpoint and return a formatted string suitable for LLM prompt context. The origin parameter is included in the request headers to provide additional context to the API, which can be useful for logging or analytics purposes.
    """
    logger.debug(f"_get_product_details called: slug={slug}, origin={origin}")
    
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/public/get-product/{slug}",
            headers={
                "Accept": "application/json",
                "origin": str(origin) if origin is not None else "",
            },
            timeout=10
        )
        logger.debug(f"API response status: {response.status_code}")

        if response.status_code == 200:
            try:
                product_details = response.json()
                logger.debug(f"JSON parsed successfully")
                result = _build_prompt_text(product_details)
                logger.debug(f"Prompt built, length: {len(result)}")
                return result
            except ValueError as e:
                logger.error(f"JSON parse error: {e}")
                return response.text
        else:
            error_msg = f"Request failed with status code {response.status_code}: {response.text[:200]}"
            logger.error(error_msg)
            return error_msg
    
    except Exception as e:
        logger.error(f"Exception in _get_product_details: {type(e).__name__}: {e}", exc_info=True)
        raise


@tool("get_product_details")
def get_product_details(slug: str) -> str:
    """Fetch product details and return LLM-ready prompt context for the given product slug."""
    return _get_product_details(slug=slug, origin="3")


#--------------------------------------------------------------------------
# This is a separate tool to allow for potential future differences in how 
#price details are fetched or formatted, while currently reusing the same underlying logic.

def _build_price_prompt_text(api_payload: dict) -> str:
    data = api_payload.get("data") if isinstance(api_payload, dict) else api_payload
    if not isinstance(data, list) or not data:
        return "No price data found in API response."

    lines = ["Price Context for Assistant:"]

    for style in data:
        if not isinstance(style, dict):
            continue

        style_id = style.get("id", "N/A")
        style_name = style.get("name", "Unknown Style")
        popular_size_id = style.get("most_popular_size")
        status = "Active" if style.get("status") == 1 else "Inactive"

        lines.append(f"Style: {style_name} (ID: {style_id}, Status: {status})")
        if popular_size_id is not None:
            lines.append(f"Popular Size ID: {popular_size_id}")

        sizes = style.get("sizes", []) if isinstance(style.get("sizes"), list) else []
        if not sizes:
            lines.append("Sizes: None")
            continue

        for size in sizes:
            if not isinstance(size, dict):
                continue

            size_id = size.get("id", "N/A")
            size_label = _format_size_label(size)
            size_status = "Active" if size.get("status") == 1 else "Inactive"
            shape = size.get("shape") or "N/A"

            lines.append(f"  Size: {size_label} (ID: {size_id}, Shape: {shape}, Status: {size_status})")

            prices = size.get("prices", []) if isinstance(size.get("prices"), list) else []
            if not prices:
                lines.append("    Prices: None")
                continue

            for price in prices:
                if not isinstance(price, dict):
                    continue

                start_qty = price.get("start_qty", "N/A")
                end_qty = price.get("end_qty", "N/A")
                amount = price.get("price", "N/A")
                price_status = "Active" if price.get("status") == 1 else "Inactive"

                lines.append(
                    f"    Price Tier: Qty {start_qty} - {end_qty}, Price {amount}, Status: {price_status}"
                )

                deliveries = price.get("deliveries", []) if isinstance(price.get("deliveries"), list) else []
                delivery_parts = []
                for delivery in deliveries:
                    if not isinstance(delivery, dict):
                        continue
                    delivery_name = delivery.get("name", "N/A")
                    days = delivery.get("no_of_days", "N/A")
                    extra_charge = delivery.get("extra_charge", "N/A")
                    delivery_parts.append(f"{delivery_name}: {days} days, extra {extra_charge}")

                if delivery_parts:
                    lines.append(f"    Deliveries: {' | '.join(delivery_parts)}")

    lines.append("Instruction: Use only this price context when answering product price questions.")
    return "\n".join(lines)


def _get_price_details(slug: str, style: str, size: str, qty: int, origin: str | None = None) -> str:
    """
    Fetch price details using the Api endpoint and return a formatted string suitable for LLM prompt context. The origin parameter is included in the request headers to provide additional context to the API, which can be useful for logging or analytics purposes.
    """
    logger.debug(f"_get_price_details called: slug={slug}, style={style}, size={size}, qty={qty}, origin={origin}")
    
    try:
        url = f"{API_BASE_URL}/api/public/get-product-price/{slug}?style={style}&size={size}&qty={qty}"
        logger.debug(f"Calling API: {url}")
        
        response = requests.get(
            url,
            headers={
                "Accept": "application/json",
                "origin": str(origin) if origin is not None else "",
            },
            timeout=10
        )
        logger.debug(f"API response status: {response.status_code}")

        if response.status_code == 200:
            try:
                price_details = response.json()
                logger.debug(f"JSON parsed successfully")
                result = _build_price_prompt_text(price_details)
                logger.debug(f"Price prompt built, length: {len(result)}")
                return result
            except ValueError as e:
                logger.error(f"JSON parse error: {e}")
                return response.text
        else:
            error_msg = f"Request failed with status code {response.status_code}: {response.text[:200]}"
            logger.error(error_msg)
            return error_msg
    
    except Exception as e:
        logger.error(f"Exception in _get_price_details: {type(e).__name__}: {e}", exc_info=True)
        raise


@tool("get_price_details")
def get_price_details(slug: str, style: str, size: str, qty: int) -> str:
    """Fetch product price details and return LLM-ready prompt context for the given product, style, size, and quantity."""
    return _get_price_details(slug=slug, style=style, size=size, qty=qty, origin="3")



