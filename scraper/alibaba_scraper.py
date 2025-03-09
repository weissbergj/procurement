# Not used; merely an example

# import requests
# from bs4 import BeautifulSoup
# import re
# from urllib.parse import quote

# # A simple user agent string (pretending to be Chrome on Windows).
# HEADERS = {
#     "User-Agent": (
#         "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
#         "AppleWebKit/537.36 (KHTML, like Gecko) "
#         "Chrome/104.0.5112.102 Safari/537.36"
#     )
# }


# def scrape_alibaba_product(product_url: str) -> dict:
#     """
#     Attempts to scrape a single Alibaba product detail page for title & price.
#     There's no universal format; Alibaba heavily uses JS, so this may fail if
#     the page doesn't render static HTML for price or if you're blocked.
    
#     Returns a dict, e.g. {"title": "...", "price": "..."} or None on failure.
#     """
#     try:
#         resp = requests.get(product_url, headers=HEADERS, timeout=10)
#         if resp.status_code != 200:
#             print(f"Error: Status {resp.status_code} for {product_url}")
#             return None

#         soup = BeautifulSoup(resp.text, "html.parser")

#         # Attempt 1: A possible product title in <h1> or <h2> with certain classes
#         title_selectors = [
#             "h1.mod-detail-title",
#             "h1.product-title",
#             "h1.product-name",
#             "h1.title",
#             "h2.mod-detail-title",
#         ]
#         title = "N/A"
#         for sel in title_selectors:
#             title_el = soup.select_one(sel)
#             if title_el and title_el.get_text(strip=True):
#                 title = title_el.get_text(strip=True)
#                 break

#         # Attempt to find price. Might appear in spans or divs with "price", "value", etc.
#         price_selectors = [
#             "span.mod-detail-priceprice",
#             "span.product-price-value",
#             "span#J-priceID",
#             "div.price",
#             "span.value",
#         ]
#         price_text = "N/A"
#         for sel in price_selectors:
#             price_el = soup.select_one(sel)
#             if price_el and price_el.get_text(strip=True):
#                 price_text = price_el.get_text(strip=True)
#                 break

#         return {
#             "title": title,
#             "price": price_text
#         }
#     except Exception as e:
#         print(f"Exception scraping {product_url}: {e}")
#         return None


# def scrape_alibaba_search(search_query: str, max_results: int = 5) -> list:
#     """
#     Scrapes a small set of search results for 'search_query' on Alibaba,
#     attempting to extract product titles, links, and partial price info.
#     Returns a list of dicts, e.g.:
#     [
#       {"title": "...", "link": "...", "price": "..."},
#       ...
#     ]

#     Highly likely to break or be blocked if used often or if Alibaba changes structure.
#     """
#     base_search_url = "https://www.alibaba.com/trade/search"
#     params = {
#         "SearchText": search_query
#     }
#     product_list = []

#     try:
#         resp = requests.get(base_search_url, params=params, headers=HEADERS, timeout=10)
#         if resp.status_code != 200:
#             print(f"Error: Status {resp.status_code} for search page.")
#             return product_list

#         soup = BeautifulSoup(resp.text, "html.parser")

#         # Alibaba sometimes uses "J-offer-wrapper" or "organic-list-item" or similar
#         # We try multiple class patterns to see if we can catch the product blocks
#         # We'll combine them in a single regex
#         # We'll look for <div> or <div class="list-item"> or "offer-list-wrapper"
#         result_items = soup.find_all(
#             "div",
#             class_=re.compile("(J-offer-wrapper|list-item|organic-gallery-offer|offer-list-wrapper|list-no-v2)")
#         )

#         for item in result_items:
#             # Attempt to find a link to the product
#             # Often there's a link with class "elements-title-normal"
#             # or "organic-gallery-title" or "offer-list-wrapper__link"
#             link_el = None

#             link_selectors = [
#                 "a.elements-title-normal",
#                 "a.organic-gallery-title",
#                 "a.list-no-v2__item-title",
#                 "a.offer-list-wrapper__link",
#                 "h2.title > a"
#             ]
#             for sel in link_selectors:
#                 candidate = item.select_one(sel)
#                 if candidate and candidate.has_attr("href"):
#                     link_el = candidate
#                     break

#             if not link_el:
#                 continue

#             link_href = link_el["href"]
#             if link_href.startswith("//"):
#                 link_href = "https:" + link_href  # fix protocol if needed

#             title_text = link_el.get_text(strip=True)

#             # Attempt price
#             # Some pages show a price in <p class="elements-offer-price-normal">
#             # or "span.elements-offer-price-normal__price"
#             # or "span.price" or "p.organic-gallery-offer__price"
#             price_text = "N/A"

#             price_selectors = [
#                 "p.elements-offer-price-normal",
#                 "span.elements-offer-price-normal__price",
#                 "span.price",
#                 "span.organic-gallery-offer__price",
#                 "p.organic-gallery-offer__price"
#             ]
#             for psel in price_selectors:
#                 price_el = item.select_one(psel)
#                 if price_el and price_el.get_text(strip=True):
#                     price_text = price_el.get_text(strip=True)
#                     break

#             # Build a small dict
#             if title_text and link_href:
#                 product_list.append({
#                     "title": title_text,
#                     "link": link_href,
#                     "price": price_text
#                 })

#             if len(product_list) >= max_results:
#                 break

#     except Exception as e:
#         print(f"Exception scraping search for '{search_query}': {e}")

#     return product_list


# if __name__ == "__main__":
#     # DEMO 1: Scrape a specific Alibaba product page (URL may or may not work)
#     product_url = "https://www.alibaba.com/product-detail/Hot-sale-laptop_1600461082629.html"  # Example placeholder
#     info = scrape_alibaba_product(product_url)
#     print("Single Product Scrape:", info)

#     # DEMO 2: Scrape search results for "laptop"
#     print("\nSearch Results for 'laptop':")
#     results = scrape_alibaba_search("laptop", max_results=5)
#     for r in results:
#         print(r)
