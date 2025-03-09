# # scraper/aggregator.py

# import random
# import re
# from procurement.vendor_data import vendors

# def add_fakestore_products(fakestore_products: list) -> dict:
#     """
#     Merges the Fake Store API product data into the in-memory vendor list
#     under a 'FakeStore Vendor'.
#     """
#     if not fakestore_products:
#         return {"message": "No products found from Fake Store API."}

#     fakestore_vendor = next((v for v in vendors if v["name"] == "FakeStore Vendor"), None)
#     if not fakestore_vendor:
#         new_id = max((v["id"] for v in vendors), default=0) + 1
#         fakestore_vendor = {
#             "id": new_id,
#             "name": "FakeStore Vendor",
#             "products": []
#         }
#         vendors.append(fakestore_vendor)

#     added_count = 0
#     for p in fakestore_products:
#         title = p.get("title", "Unknown")
#         price = p.get("price", 9999.0)
#         base_sku = re.sub(r'[^a-z0-9]+', '-', title.lower())[:12]
#         sku = f"{base_sku}-{random.randint(100,999)}"
#         stock = 50  # arbitrary

#         fakestore_vendor["products"].append({
#             "sku": sku,
#             "name": title,
#             "price": float(price),
#             "stock": stock,
#             # we can add a mock delivery_days
#             "delivery_days": random.randint(2, 10)
#         })
#         added_count += 1

#     return {
#         "message": f"Added {added_count} products from Fake Store API to 'FakeStore Vendor'.",
#         "vendor_id": fakestore_vendor["id"]
#     }

# def add_alibaba_products(custom_vendors: list):
#     """
#     Merges any user-provided vendors into the global list.
#     If a vendor with the same name already exists, just skip or merge them.
#     """
#     if not custom_vendors:
#         return
    
#     for v in custom_vendors:
#         existing = next((x for x in vendors if x["name"] == v["name"]), None)
#         if not existing:
#             # assign an ID
#             new_id = max((vend["id"] for vend in vendors), default=0) + 1
#             v["id"] = new_id
#             # ensure each product has minimum fields
#             for p in v["products"]:
#                 if "delivery_days" not in p:
#                     p["delivery_days"] = 5  # random default
#                 if "stock" not in p:
#                     p["stock"] = 20
#             vendors.append(v)
#         else:
#             # merge products (simple approach)
#             for p in v["products"]:
#                 if "delivery_days" not in p:
#                     p["delivery_days"] = 5
#                 if "stock" not in p:
#                     p["stock"] = 20
#                 existing["products"].append(p)


# scraper/aggregator.py

def recommend_items(item_name, quantity, preference, multi_vendor, custom_sellers, global_vendors):
    """
    This replicates the code from your /recommend endpoint:
    merges custom sellers if present, otherwise uses global vendors,
    does substring match, stock check, sorts by total_cost, returns list.
    """
    if custom_sellers:
        merged = custom_sellers
    else:
        merged = global_vendors

    results = []
    for seller in merged:
        product_str = seller.get("item","")
        if item_name.lower() in product_str.lower():
            st = seller.get("stock", 0)
            if st >= quantity:
                price = seller.get("price", 9999)
                total = price * quantity
                results.append({
                    "vendor_name": seller.get("name","NoName"),
                    "product_name": product_str,
                    "sku": seller.get("sku",""),
                    "price": price,
                    "stock": st,
                    "quantity": quantity,
                    "unit_price": price,
                    "total_cost": total
                })
    results.sort(key=lambda x: x["total_cost"])
    return results
