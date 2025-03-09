# AI Procurement System

A **multi-step** AI-assisted procurement demo using **FastAPI**. Users can:
- Enter or mock-search vendor data (via a built-in Fake Store API).
- Get recommended products based on cost, inventory, or shipping speed.
- Generate a **Purchase Order** (PDF or email link).
- Return to the Home screen and see newly finalized POs.

## Architecture at a Glance

    .
    ├── main.py                   # FastAPI app (serves HTML & defines endpoints)
    ├── requirements.txt          # Python dependencies
    ├── templates/
    │   └── index.html            # Single-page UI (HTML+JS) for multi-step flow
    ├── po_order/
    │   └── po_generation.py      # PDF generation w/ wkhtmltopdf, optional email logic
    ├── procurement/
    │   ├── vendor_data.py        # In-memory data (VENDORS, FINALIZED_POS)
    │   └── logic.py              # Additional logic (optional)
    ├── scraper/
    │   ├── aggregator.py         # merges custom/global vendor data
    │   ├── fakestore_scraper.py  # calls the FakeStore API
    │   └── alibaba_scraper.py    # (optional) example for Alibaba
    └── openai_client.py          # (optional) LLM-based parsing (e.g. Mistral)

**Key Components**  
- **`templates/index.html`**: Single-page **front-end** UI (Steps A–F).  
- **`main.py`**: FastAPI entrypoint, routes like `/recommend`, `/finalize-po`, `/save-po`.  
- **`po_order/po_generation.py`**: Creates a PDF with **pdfkit**; optionally handles SMTP email.  
- **`scraper/fakestore_scraper.py`**: Fetches mock products from [FakeStore API](https://fakestoreapi.com/).  
- **`procurement/vendor_data.py`**: In-memory lists for `VENDORS` and `FINALIZED_POS`.

---

## Prerequisites

1. **Python 3.8+**  
2. **wkhtmltopdf** for PDF generation  
   - macOS: [wkhtmltopdf.org](https://wkhtmltopdf.org/)  
   - Ubuntu/Debian: `sudo apt-get install wkhtmltopdf`  
   - Windows: official installer from [wkhtmltopdf.org](https://wkhtmltopdf.org/)

## Installation

1. **Install** Python dependencies:

        pip install -r requirements.txt

2. **Verify** `wkhtmltopdf` in PATH:

        wkhtmltopdf --version

   If it’s missing, add it to PATH or specify its path in code.

---

## Running

1. **Start** the FastAPI server:

        uvicorn main:app --reload

2. Open <http://127.0.0.1:8000> in your browser.  
   - You’ll see the multi-step UI (Steps A–F).

---

## Usage Flow

1. **Step A**: Enter item name & quantity.  
2. **Step B**: Choose custom JSON sellers or “Mock web search.”  
3. **Step C**: Pick preference (cost, stock, or delivery).  
4. **Step D**: View recommended products.  
5. **Step E**: Select vendors to finalize.  
6. **Step F**: Generate **PDF** (download link) or **Email** (`mailto:`). Then click **“Done”** to return home.

---

## FastAPI Docs

For interactive docs, visit:

    http://127.0.0.1:8000/docs#

Try routes like `/import-fakestore`, `/recommend`, `/finalize-po`.

---

## Optional: LLM Parsing

- Add a route (e.g. `/procure-chat`) that calls `openai_client.py` or Mistral to parse freeform text.  
- Converts user requests (“Need 20 i5 laptops”) into item_name + quantity.

---

## Future Directions

- **Persistent DB**: Instead of in-memory, store vendors/POs in a real database.  
- **Scalability**: Containerize with Docker, deploy behind a load balancer.  
- **Discord Bot**: Provide the same logic on a Discord channel.  
- **ERP Integration**: Connect to a real e-commerce or ERP system for actual procurement.

---
