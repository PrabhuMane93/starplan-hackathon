import json
import os

VENDOR_MAP_FILE = "vendor_details.json"


def load_vendor_map() -> dict:
    """Load the vendor map from file, return empty dict if file missing."""
    if not os.path.exists(VENDOR_MAP_FILE):
        return {}
    with open(VENDOR_MAP_FILE, "r") as f:
        return json.load(f)


def save_vendor_map(data: dict):
    """Save vendor map to the JSON file."""
    with open(VENDOR_MAP_FILE, "w") as f:
        json.dump(data, f, indent=4)


def add_vendor(property_address: str, vendor_email: str):
    """
    Add or update vendor email for a property.
    """
    vendor_map = load_vendor_map()
    vendor_map[property_address] = vendor_email
    save_vendor_map(vendor_map)


def get_vendor(property_address: str) -> str | None:
    """
    Retrieve vendor email for a property, or None if not found.
    """
    vendor_map = load_vendor_map()
    return vendor_map.get(property_address)
