# procurement/logic.py

from typing import List, Dict, Optional
from difflib import SequenceMatcher
from procurement.vendor_data import VENDORS as vendors

def fuzzy_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def find_best_fuzzy_match(item_name: str) -> Optional[str]:
    """
    Given a user-provided item_name, find the best fuzzy match among
    all known product names in the vendor data.
    """
    best_match = None
    best_score = 0.0
    
    all_products = set()
    for vendor in vendors:
        for product in vendor["products"]:
            all_products.add(product["name"])
    
    for product_name in all_products:
        score = fuzzy_similarity(item_name, product_name)
        if score > best_score:
            best_score = score
            best_match = product_name
    
    if best_score < 0.5:
        return None
    return best_match


def search_vendors_exact(item_name: str, quantity: int) -> List[Dict]:
    """
    item_name is a substring of the product's 'item' or 'sku'.
    product['stock'] >= quantity.
    """
    matches = []
    item_name_lower = item_name.lower()

    for product in vendors:  # each entry is already flattened
        # e.g. product = {"name": "Acme Computers", "item": "Laptop i7 16GB", "price": 1200, "stock": 50, "sku": "laptop-i7-16gb"}
        if (item_name_lower in product["item"].lower() or
            item_name_lower in product["sku"].lower()):
            if product["stock"] >= quantity:
                matches.append({
                    "vendor_name": product["name"],      # e.g. "Acme Computers"
                    "product_name": product["item"],     # e.g. "Laptop i7 16GB"
                    "sku": product["sku"],
                    "price": product["price"],
                    "stock": product["stock"],
                    "delivery_days": product.get("delivery_days", 7)
                })
    return matches


def compare_quotes_advanced(matches: List[Dict], quantity: int, preference: str, raw_value=False) -> Dict:
    """
    Sort the matches according to the preference:
       - "cost" => price * quantity ascending
       - "inventory" => stock descending
       - "delivery" => delivery_days ascending
    If raw_value=True, returns the numeric sorting value only (for use in a custom sort).
    Otherwise returns the best match dict.
    """
    if not matches:
        if raw_value:
            return float('inf')
        return {}

    def sort_key(m):
        if preference == "cost":
            return m["price"] * quantity
        elif preference == "inventory":
            return -m["stock"]  # higher stock first
        elif preference == "delivery":
            return m["delivery_days"]
        else:
            # default cost
            return m["price"] * quantity

    sorted_list = sorted(matches, key=sort_key)
    if raw_value:
        # return the first match's key for custom usage
        return sort_key(sorted_list[0])
    return sorted_list[0]


def search_multi_vendor(matches: List[Dict], item_name: str, quantity: int) -> Dict:
    """
    Attempt to fulfill the quantity from multiple vendors if single-vendor stock is insufficient
    or user specifically wants multi.
    This is a naive approach: sort by cost, then fill from cheapest onward.
    """
    # If there's any single vendor with enough stock, also let them do that route.
    # But this function specifically tries to combine multiple.
    # We'll do a simple approach: sort by price ascending, then fill the total qty needed.
    if not matches:
        return {}

    sorted_matches = sorted(matches, key=lambda m: m["price"])
    qty_left = quantity
    picked = []
    allocations = {}  # vendor_id -> qty

    combined_cost = 0.0
    for m in sorted_matches:
        if qty_left <= 0:
            break
        can_take = min(qty_left, m["stock"])
        if can_take > 0:
            picked.append(m)
            allocations[m["vendor_id"]] = can_take
            combined_cost += m["price"] * can_take
            qty_left -= can_take

    # If we didn't fill the entire requested quantity, fail
    if qty_left > 0:
        return {}

    # Return a special "multi_vendors" object
    return {
        "multi_vendors": picked,
        "combined_cost": combined_cost,
        "allocations": allocations
    }


def generate_po(match_or_combo: Dict, quantity: int) -> Dict:
    """
    If match_or_combo is a single vendor's match:
      Return a normal PO dict.
    If it's a multi-vendor dictionary, we actually produce multiple POs in the front end.
    Here we'll handle only the single vendor case for simplicity.
    """
    # if not match_or_combo or "vendor_id" not in match_or_combo:
    #     return {}
    
    total_cost = match_or_combo["price"] * quantity
    po = {
        "vendor_id": match_or_combo["vendor_id"],
        "vendor_name": match_or_combo["vendor_name"],
        "sku": match_or_combo["sku"],
        "product_name": match_or_combo["product_name"],
        "quantity": quantity,
        "unit_price": match_or_combo["price"],
        "total_cost": total_cost
    }
    return po
