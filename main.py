#!/usr/bin/env python3
"""
NBI Klaviyo API Integration
Connects to and interacts with the Klaviyo API for the NBI project.
Supports dual-environment strategy: read-only production and full-access staging.
"""

import argparse
import json
import os
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()

KLAVIYO_BASE_URL = "https://a.klaviyo.com"
KLAVIYO_API_REVISION = "2024-10-15"


def get_latest_profiles(api_key: str, limit: int = 5) -> dict[str, Any] | None:
    """
    Fetch the latest profiles from the Klaviyo API, sorted by creation date (newest first).

    Args:
        api_key: Klaviyo private API key for authentication.
        limit: Maximum number of profiles to retrieve (default: 5).

    Returns:
        Parsed JSON response data on success, or None on error.
    """
    url = f"{KLAVIYO_BASE_URL}/api/profiles/"
    headers = {
        "Authorization": f"Klaviyo-API-Key {api_key}",
        "accept": "application/json",
        "revision": KLAVIYO_API_REVISION,
    }
    params = {
        "sort": "-created",
        "page[size]": limit,
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(f"HTTP error occurred: {e}")
        if hasattr(e.response, "text") and e.response is not None:
            print(f"Response body: {e.response.text}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return None

    print("Successfully connected and retrieved data.")
    data = response.json()
    print(json.dumps(data, indent=2))
    return data


def main() -> None:
    """Entry point for the Klaviyo API integration."""
    parser = argparse.ArgumentParser(
        description="NBI Klaviyo API Integration - dual-environment support"
    )
    parser.add_argument(
        "--env",
        choices=["prod", "staging"],
        default="prod",
        help="Target environment: prod (read-only) or staging (full access)",
    )
    args = parser.parse_args()

    # Dynamic API key selection based on environment
    if args.env == "staging":
        api_key = os.environ.get("KLAVIYO_API_KEY_STAGING_FULL")
        print("Targeting: STAGING environment (Full Access)")
    else:
        api_key = os.environ.get("KLAVIYO_API_KEY_PROD_READ")
        print("Targeting: PRODUCTION environment (Read-Only)")

    if not api_key:
        print(
            f"KLAVIYO_API_KEY_{'STAGING_FULL' if args.env == 'staging' else 'PROD_READ'} "
            "environment variable is not set."
        )
        print("Set it in .env or export it before running.")
        return

    get_latest_profiles(api_key)


if __name__ == "__main__":
    main()
