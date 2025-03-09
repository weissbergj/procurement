# # procurement/vendor_data.py

# LOCAL_DB = [
#     {
#         "id": 1,
#         "name": "Acme Computers",
#         "products": [
#             {
#                 "sku": "laptop-i7-16gb", 
#                 "name": "Laptop i7 16GB", 
#                 "price": 1200, 
#                 "stock": 50,
#                 "delivery_days": 5
#             },
#             {
#                 "sku": "desktop-i5-8gb", 
#                 "name": "Desktop i5 8GB", 
#                 "price": 900, 
#                 "stock": 30,
#                 "delivery_days": 3
#             }
#         ]
#     },
#     {
#         "id": 2,
#         "name": "Global Tech",
#         "products": [
#             {
#                 "sku": "laptop-i7-16gb", 
#                 "name": "Laptop i7 16GB", 
#                 "price": 1150, 
#                 "stock": 10,
#                 "delivery_days": 2
#             },
#             {
#                 "sku": "monitor-4k", 
#                 "name": "4K Monitor", 
#                 "price": 300, 
#                 "stock": 100,
#                 "delivery_days": 7
#             }
#         ]
#     }
# ]

# VENDORS = []
# FINALIZED_POS = []

# def flatten_local_db():
#     """
#     Convert each vendor in LOCAL_DB into flat dicts in VENDORS,
#     matching the 'name/item/price/stock/sku' approach used for FakeStore.
#     """
#     for vendor_dict in LOCAL_DB:
#         for prod in vendor_dict["products"]:
#             VENDORS.append({
#                 "name": vendor_dict["name"],       # e.g. "Acme Computers"
#                 "item": prod["name"],              # e.g. "Laptop i7 16GB"
#                 "price": prod["price"],
#                 "stock": prod["stock"],
#                 "sku": prod["sku"],
#                 "delivery_days": prod.get("delivery_days", 7)
#             })

# procurement/vendor_data.py

VENDORS = []
FINALIZED_POS = []