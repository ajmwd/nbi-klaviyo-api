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


def _get_headers(api_key: str) -> dict[str, str]:
    """Build the standard Klaviyo API request headers."""
    return {
        "Authorization": f"Klaviyo-API-Key {api_key}",
        "accept": "application/json",
        "revision": KLAVIYO_API_REVISION,
    }


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
    headers = _get_headers(api_key)
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


def create_test_profile(api_key: str, profile_data: dict[str, Any]) -> dict[str, Any] | None:
    """
    Create a new profile in Klaviyo via the POST /profiles/ endpoint.

    Args:
        api_key: Klaviyo private API key for authentication.
        profile_data: Dictionary containing the profile payload (JSON API format).

    Returns:
        Parsed JSON response data on success, or None on error.
    """
    url = f"{KLAVIYO_BASE_URL}/api/profiles/"
    headers = _get_headers(api_key)

    try:
        response = requests.post(
            url,
            headers=headers,
            json=profile_data,
            timeout=30,
        )
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(f"HTTP error occurred: {e}")
        if e.response is not None:
            print(f"Response body: {e.response.text}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return None

    print("Successfully created test profile:")
    data = response.json()
    print(json.dumps(data, indent=2))
    return data


def find_or_create_test_profile(api_key: str) -> str | None:
    """
    Find an existing test profile by email, or create one if none exists.
    Returns a valid profile_id in either case.

    Args:
        api_key: Klaviyo private API key for authentication.

    Returns:
        The profile ID (string) on success, or None if both search and create fail.
    """
    test_email = "test.user.ajmwd@example.com"
    url = f"{KLAVIYO_BASE_URL}/api/profiles/"
    headers = _get_headers(api_key)
    params = {"filter": f'equals(email,"{test_email}")'}

    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(f"HTTP error occurred while searching for profile: {e}")
        if e.response is not None:
            print(f"Response body: {e.response.text}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return None

    data = response.json()
    profiles = data.get("data", [])

    if profiles:
        profile_id = profiles[0].get("id")
        if profile_id:
            return profile_id

    # No profile found; create one
    test_profile = {
        "data": {
            "type": "profile",
            "attributes": {
                "email": test_email,
                "first_name": "Test",
                "last_name": "User",
            },
        }
    }
    create_response = create_test_profile(api_key, test_profile)
    if create_response and "data" in create_response and "id" in create_response["data"]:
        return create_response["data"]["id"]

    return None


def suppress_profile(api_key: str, email: str) -> bool:
    """
    Suppress a profile in Klaviyo via the Bulk Suppress Profiles endpoint.
    Uses POST /api/profile-suppression-bulk-create-jobs per official API docs.
    Suppression prevents the profile from receiving marketing emails (non-destructive).
    If the profile does not exist, Klaviyo creates it and immediately suppresses it.

    Args:
        api_key: Klaviyo private API key for authentication.
        email: The email address of the profile to suppress.

    Returns:
        True on success (202 Accepted), False on error.
    """
    url = f"{KLAVIYO_BASE_URL}/api/profile-suppression-bulk-create-jobs"
    headers = _get_headers(api_key)
    headers["Content-Type"] = "application/vnd.api+json"
    payload = {
        "data": {
            "type": "profile-suppression-bulk-create-job",
            "attributes": {
                "profiles": {
                    "data": [
                        {
                            "type": "profile",
                            "attributes": {
                                "email": email,
                            },
                        },
                    ],
                },
            },
        }
    }

    try:
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(f"HTTP error occurred: {e}")
        if e.response is not None:
            print(f"Response body: {e.response.text}")
        return False
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return False

    # 202 Accepted = async job accepted; suppression will be processed
    print(f"Successfully suppressed profile with email: {email}")
    return True


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

    if args.env == "staging":
        # Ensure test profile exists (handles idempotency; create only if not found)
        find_or_create_test_profile(api_key)
        # Bulk suppress endpoint creates+suppresses if profile missing, or suppresses if exists
        suppress_profile(api_key, "test.user.ajmwd@example.com")
    else:
        get_latest_profiles(api_key)


if __name__ == "__main__":
    main()
