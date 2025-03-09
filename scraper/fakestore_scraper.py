# # scraper/fakestore_scraper.py

# import requests

# FAKESTORE_BASE_URL = "https://fakestoreapi.com"

# def fetch_fakestore_products() -> list:
#     url = f"{FAKESTORE_BASE_URL}/products"
#     resp = requests.get(url, timeout=10)
#     resp.raise_for_status()
#     return resp.json()

# def fetch_fakestore_category(cat: str) -> list:
#     url = f"{FAKESTORE_BASE_URL}/products/category/{cat}"
#     resp = requests.get(url, timeout=10)
#     if resp.status_code == 200:
#         return resp.json()
#     return []

# scraper/fakestore_scraper.py

import requests

FAKESTORE_URL = "https://fakestoreapi.com/products"

def import_fakestore_data(category=None):
    if category:
        url = f"{FAKESTORE_URL}/category/{category}"
    else:
        url = FAKESTORE_URL

    r = requests.get(url, timeout=10)
    if r.status_code != 200:
        raise RuntimeError(f"FakeStore returned {r.status_code}")
    return r.json()
