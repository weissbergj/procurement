
# ###########################
# # main.py
# ###########################
import os
import tempfile
import requests
import pdfkit
from fastapi import FastAPI, Request, Body
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from jinja2 import Template
from typing import List, Dict
import ssl
import smtplib
from email.message import EmailMessage
from email.utils import formataddr

###############################################################
# GLOBAL (in-memory) DATA STRUCTURES
###############################################################
# We'll store POs, seller lists, etc. in memory for the session.
ACTIVE_PURCHASES = {}       # keyed by session_id or some token
MOCK_CUSTOM_SELLERS = []    # if the user enters a custom seller list

# A place to store finalized POs (like a "home screen" record)
FINALIZED_POS = []

app = FastAPI(
    title="AI Procurement (Multi-Step Demo)",
    description="A single-page web interface with multiple steps for procurement, PDF/Email finalization.",
    version="1.0.0"
)

###############################################################
# HELPER: A simple HTML template
# We'll serve one big page at GET /, which uses JavaScript to
# call our endpoints for each step of the flow.
###############################################################
INDEX_HTML = r"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8" />
  <title>AI Procurement Multi-Step Demo</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 20px; }
    .hidden { display: none; }
    .step { margin-bottom: 20px; border: 1px solid #ccc; padding: 10px; }
    .step h2 { margin-top: 0; }
    .results-table, .final-po-table { border-collapse: collapse; width: 100%; }
    .results-table td, .results-table th,
    .final-po-table td, .final-po-table th {
      border: 1px solid #ccc; padding: 8px;
    }
    .po-log { margin-top: 20px; border: 1px solid #ccc; padding: 10px; }
    .po-log h3 { margin-top: 0; }
    .po-item { border-bottom: 1px solid #eee; margin-bottom: 6px; }
  </style>
</head>
<body>
  <h1>AI Procurement Multi-Step Demo</h1>
  <div id="home-screen" class="step">
    <h2>Home Screen</h2>
    <button onclick="startFlow()">Start a New Procurement</button>
    <div class="po-log">
      <h3>Finalized POs</h3>
      <div id="poLog"></div>
    </div>
  </div>

  <div id="stepA" class="step hidden">
    <h2>Step A: What do you want to buy (e.g., laptops)?</h2>
    <p>Enter item name and quantity (e.g., "laptop"):</p>
    <input id="stepA_item" type="text" placeholder="Item name" />
    <input id="stepA_qty" type="number" value="1" />
    <button onclick="stepANext()">Next</button>
  </div>

  <div id="stepB" class="step hidden">
    <h2>Step B: Sellers</h2>
    <p>Do you have a custom list of sellers or want to do a mock web search?</p>
    <button onclick="chooseCustomSellers()">Enter custom sellers</button>
    <button onclick="chooseMockSearch()">Mock web search</button>

    <div id="customSellersSection" class="hidden">
      <p>Enter your seller list in JSON format (name, price, stock, email, etc.). Example:</p>
<pre>[
  {"name": "Acme Computers", "item": "Laptop i7 16GB", "price": 1200, "stock": 10, "email": "sales@acme.com"},
  {"name": "Global Tech", "item": "Laptop i7 16GB", "price": 1150, "stock": 5, "email": "sales@globaltech.com"}
]
</pre>
      <textarea id="customSellersInput" rows="6" cols="60"></textarea>
      <br/>
      <button onclick="submitCustomSellers()">Submit Sellers</button>
    </div>
  </div>

  <div id="stepC" class="step hidden">
    <h2>Step C: Preferences</h2>
    <p>What is most important?</p>
    <select id="prefSelect">
      <option value="cost">Cost</option>
      <option value="stock">Inventory</option>
      <option value="delivery">Shipping Speed</option>
    </select>
    <p>Willing to purchase from multiple vendors?</p>
    <label><input type="radio" name="multiVendor" value="no" checked /> No</label>
    <label><input type="radio" name="multiVendor" value="yes" /> Yes</label>
    <br/>
    <button onclick="stepCNext()">Next</button>
  </div>

  <div id="stepD" class="step hidden">
    <h2>Step D: Top Recommendations</h2>
    <p>Based on your item, quantity, preferences, and chosen sellers.</p>
    <div id="recommendations"></div>
    <button onclick="stepDNext()">Next</button>
  </div>

  <div id="stepE" class="step hidden">
    <h2>Step E: Which vendors do you want to finalize a PO with?</h2>
    <p>Select one or more (if you said multi vendor = yes) from the list below.</p>
    <div id="vendorOptions"></div>
    <button onclick="generateSelectedPO()">Generate Purchase Order(s)</button>
  </div>

  <div id="stepF" class="step hidden">
    <h2>Step F: Email or PDF?</h2>
    <p>You can pick how to finalize the PO(s).</p>
    <label><input type="checkbox" id="optionPDF" /> PDF</label>
    <label><input type="checkbox" id="optionEmail" /> Email</label>
    <br/>
    <div id="emailSection" class="hidden">
      <p>Enter your email to receive the PO or to send to vendor:</p>
      <input id="emailRecipient" type="email" placeholder="your@email.com" />
      <p>Edit the email text if you want (optional):</p>
      <textarea id="emailBody" rows="4" cols="60"></textarea>
    </div>
    <button onclick="finalizePO()">Finalize!</button>
    <div id="poResult"></div>
    <div id="poResult"></div>
    <button id="doneBtn" class="hidden" onclick="goHome()">Done</button>
  </div>

  <script>
    // We'll store user input in a global object to keep track across steps
    let procurementData = {
      itemName: "",
      quantity: 1,
      preference: "cost",
      multiVendor: false,
      sellers: [],  // combined custom or mock
      recommended: [], // top results
      selectedPOs: [], // final selection
    };

    // A small function to hide all steps
    function hideAll() {
      document.querySelectorAll('.step').forEach(el => el.classList.add('hidden'));
    }

    function show(id) {
      document.getElementById(id).classList.remove('hidden');
    }

    function refreshPOLog() {
      fetch('/pos')
        .then(r => r.json())
        .then(data => {
          let logDiv = document.getElementById("poLog");
          logDiv.innerHTML = "";
          data.forEach((po, idx) => {
            logDiv.innerHTML += `
              <div class="po-item">
                <strong>PO #${idx+1}</strong> - Vendor: ${po.vendor_name}, Product: ${po.product_name}, 
                Qty: ${po.quantity}, Total: $${po.total_cost}
              </div>
            `;
          });
        })
        .catch(console.error);
    }

    // On page load, show home screen
    window.onload = () => {
      hideAll();
      show("home-screen");
      refreshPOLog();
    };

    function startFlow() {
      hideAll();
      show("stepA");
    }

    // STEP A
    function stepANext() {
      procurementData.itemName = document.getElementById("stepA_item").value || "Laptop i7 16GB";
      procurementData.quantity = parseInt(document.getElementById("stepA_qty").value) || 1;
      hideAll();
      show("stepB");
    }

    // STEP B
    function chooseCustomSellers() {
      document.getElementById("customSellersSection").classList.remove("hidden");
    }
    function chooseMockSearch() {
      // We'll do a "fake store" approach behind the scenes
      // Let them skip custom
      procurementData.sellers = []; // we'll do "mock" on stepC next
      alert("Ok, we'll do a mock web search next step.");
      document.getElementById("customSellersSection").classList.add("hidden");
      hideAll();
      show("stepC");
    }

    function submitCustomSellers() {
      let txt = document.getElementById("customSellersInput").value.trim();
      try {
        let arr = JSON.parse(txt);
        procurementData.sellers = arr;
        alert("Successfully saved custom sellers!");
        hideAll();
        show("stepC");
      } catch(e) {
        alert("Error parsing JSON. Please try again.");
      }
    }

    // STEP C
    function stepCNext() {
      let pref = document.getElementById("prefSelect").value;
      procurementData.preference = pref;
      let multiRadios = document.getElementsByName("multiVendor");
      for (let r of multiRadios) {
        if (r.checked && r.value === "yes") procurementData.multiVendor = true;
        if (r.checked && r.value === "no") procurementData.multiVendor = false;
      }
      // Move on to Step D: "top recommendations"
      doRecommendations();
    }

    function doRecommendations() {
      hideAll();
      show("stepD");
      // If user didn't provide custom sellers, let's do a FakeStore fetch
      // We'll just call /import-fakestore behind the scenes
      if (procurementData.sellers.length === 0) {
        fetch('/import-fakestore')
          .then(r => r.json())
          .then(data => {
            // data might say "Added 20 products..."
            // Then let's do a new endpoint to get the recommended results
            return fetch('/recommend', {
              method: 'POST',
              headers: {'Content-Type': 'application/json'},
              body: JSON.stringify({
                item_name: procurementData.itemName,
                quantity: procurementData.quantity,
                preference: procurementData.preference,
                multi_vendor: procurementData.multiVendor,
                custom_sellers: [] // no custom
              })
            });
          })
          .then(r => r.json())
          .then(res => {
            if (res.options) {
              procurementData.recommended = res.options;
              renderRecommendations();
            } else {
              document.getElementById('recommendations').innerHTML = "No recommendations found?";
            }
          })
          .catch(err => {
            console.error(err);
            document.getElementById('recommendations').innerHTML = "Error fetching recommendations";
          });
      } else {
        // We have custom sellers in procurementData.sellers
        // We'll call /recommend with that
        fetch('/recommend', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({
            item_name: procurementData.itemName,
            quantity: procurementData.quantity,
            preference: procurementData.preference,
            multi_vendor: procurementData.multiVendor,
            custom_sellers: procurementData.sellers
          })
        })
        .then(r => r.json())
        .then(res => {
          if (res.options) {
            procurementData.recommended = res.options;
            renderRecommendations();
          } else {
            document.getElementById('recommendations').innerHTML = "No recommendations found?";
          }
        })
        .catch(err => {
          console.error(err);
          document.getElementById('recommendations').innerHTML = "Error fetching recommendations";
        });
      }
    }

    function renderRecommendations() {
      let recDiv = document.getElementById("recommendations");
      recDiv.innerHTML = "";
      if (procurementData.recommended.length === 0) {
        recDiv.innerHTML = "No matches found for your request.";
        return;
      }
      let html = `<table class="results-table">
      <tr><th>Vendor</th><th>Item</th><th>Price</th><th>Stock</th><th>Total Cost</th></tr>
      `;
      procurementData.recommended.forEach((item, idx) => {
        html += `<tr>
          <td>${item.vendor_name || item.name}</td>
          <td>${item.product_name || item.item}</td>
          <td>$${item.unit_price || item.price}</td>
          <td>${item.stock || "?"}</td>
          <td>$${item.total_cost || "?"}</td>
        </tr>`;
      });
      html += `</table>`;
      recDiv.innerHTML = html;
    }

    function stepDNext() {
      hideAll();
      show("stepE");
      renderVendorOptions();
    }

    // STEP E
    function renderVendorOptions() {
      let container = document.getElementById("vendorOptions");
      container.innerHTML = "";
      if (procurementData.recommended.length === 0) {
        container.innerHTML = "No recommended sellers to finalize.";
        return;
      }
      procurementData.selectedPOs = []; // clear old selections
      let html = "<p>Select the ones you want:</p><ul>";
      procurementData.recommended.forEach((it, idx) => {
        let lbl = `${it.vendor_name || it.name} - ${it.product_name || it.item} - $${it.total_cost || (it.price * procurementData.quantity)}`;
        html += `<li>
          <label>
            <input type="checkbox" id="opt_${idx}" />
            ${lbl}
          </label>
        </li>`;
      });
      html += "</ul>";
      container.innerHTML = html;
    }

    function generateSelectedPO() {
      // For each checked item, we'll create a 'po_data' dict
      procurementData.selectedPOs = [];
      procurementData.recommended.forEach((it, idx) => {
        let cb = document.getElementById(`opt_${idx}`);
        if (cb && cb.checked) {
          let po = {
            vendor_name: it.vendor_name || it.name,
            product_name: it.product_name || it.item,
            sku: it.sku || (`${(it.product_name||it.item).replace(/\s+/g,'-')}--${idx}`),
            quantity: it.quantity || procurementData.quantity,
            unit_price: it.unit_price || it.price,
            total_cost: it.total_cost || ( (it.unit_price||it.price) * (it.quantity || procurementData.quantity))
          };
          procurementData.selectedPOs.push(po);
        }
      });
      if (procurementData.selectedPOs.length === 0) {
        alert("You didn't select anything!");
        return;
      }
      // Move on to step F
      hideAll();
      show("stepF");
    }

    // STEP F
    document.getElementById("optionPDF").addEventListener('change', (ev)=>{
      let isChecked = ev.target.checked;
      if (isChecked) {
        // no immediate action
      }
    });
    document.getElementById("optionEmail").addEventListener('change', (ev)=>{
      let isChecked = ev.target.checked;
      document.getElementById("emailSection").classList.toggle("hidden", !isChecked);
    });

function finalizePO() {
  let doPDF = document.getElementById("optionPDF").checked;
  let doEmail = document.getElementById("optionEmail").checked;
  if (!doPDF && !doEmail) {
    alert("Please choose PDF and/or Email.");
    return;
  }
  let emailRecipient = document.getElementById("emailRecipient").value;
  let customEmailBody = document.getElementById("emailBody").value;

  let poResultDiv = document.getElementById("poResult");
  poResultDiv.innerHTML = "Finalizing POs...<br/>";

  // Hide the "Done" button for now, in case the user re-finalizes
  document.getElementById("doneBtn").classList.add("hidden");

  let requests = [];

  procurementData.selectedPOs.forEach((po) => {
    // If PDF
    if (doPDF) {
      let pdfReq = fetch('/finalize-po', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          po_data: po,
          mode: 'pdf'
        })
      })
      .then(async (r) => {
        if (r.ok) {
          let blob = await r.blob();
          let url = URL.createObjectURL(blob);
          let link = document.createElement("a");
          link.href = url;
          link.download = "purchase_order.pdf";
          link.innerText = `Download PDF for vendor: ${po.vendor_name}`;
          poResultDiv.appendChild(link);
          poResultDiv.appendChild(document.createElement("br"));
        } else {
          let tx = await r.text();
          poResultDiv.innerHTML += "Error generating PDF: " + tx + "<br/>";
        }
      })
      .catch(err => {
        poResultDiv.innerHTML += "Error fetching PDF: " + err + "<br/>";
      });
      requests.push(pdfReq);
    }

    // If Email
    if (doEmail) {
      let emailReq = fetch('/finalize-po', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          po_data: po,
          mode: 'email',
          recipient_email: emailRecipient
        })
      })
      .then(r => r.json())
      .then(res => {
        if (res.mailto_link) {
          // Open the mailto link
          window.location.href = res.mailto_link;
          poResultDiv.innerHTML += `Email link opened for vendor: ${po.vendor_name}<br/>`;
        } else if (res.error) {
          poResultDiv.innerHTML += `Email error: ${res.error}<br/>`;
        }
      })
      .catch(err => {
        poResultDiv.innerHTML += "Error sending email: " + err + "<br/>";
      });
      requests.push(emailReq);
    }

    // Save the PO in /save-po so we can see it on home screen
    let saveReq = fetch('/save-po', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(po)
    }).then(() => {
      // no direct UI feedback, but it's a successful POST
    });
    requests.push(saveReq);
  });

  // Wait for everything to finish
  Promise.all(requests)
    .then(() => {
      // We stay on Step F, show a message + "Done" button
      poResultDiv.innerHTML += "<br/>All operations finished! Click 'Done' to return home.";
      document.getElementById("doneBtn").classList.remove("hidden");
    })
    .catch(err => {
      console.error("some request failed", err);
      poResultDiv.innerHTML += "<br/>Some operations failed. Check console.";
      // Still show "Done" so user can proceed
      document.getElementById("doneBtn").classList.remove("hidden");
    });
    }

    function goHome() {
        hideAll();
        show("home-screen");
        refreshPOLog();
    }
  </script>
</body>
</html>
"""

###############################################################
# PDF + Email Utility
###############################################################
HTML_PO_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
 <meta charset="utf-8" />
 <style>
  body { font-family: Arial, sans-serif; margin: 20px; }
  h1 { text-align: center; }
  table { width: 100%; border: 1px solid #ccc; border-collapse: collapse; margin-top: 20px; }
  td, th { border: 1px solid #ccc; padding: 8px; }
 </style>
</head>
<body>
  <h1>Purchase Order</h1>
  <p><strong>Vendor:</strong> {{ vendor_name }}</p>
  <p><strong>SKU:</strong> {{ sku }}</p>
  <p><strong>Product:</strong> {{ product_name }}</p>
  <p><strong>Quantity:</strong> {{ quantity }}</p>
  <p><strong>Unit Price:</strong> ${{ unit_price }}</p>
  <p><strong>Total Cost:</strong> ${{ total_cost }}</p>
  <hr/>
  <p>Generated by AI Procurement Demo</p>
</body>
</html>
"""

def generate_po_pdf(po_data: Dict) -> bytes:
    from jinja2 import Template
    template = Template(HTML_PO_TEMPLATE)
    html = template.render(**po_data)
    pdf_bytes = pdfkit.from_string(html, False)
    return pdf_bytes

def send_po_email(po_data: Dict, recipient_email: str):
    body = f"""Purchase Order:
Vendor: {po_data['vendor_name']}
Product: {po_data['product_name']}
Quantity: {po_data['quantity']}
Unit Price: ${po_data['unit_price']}
Total Cost: ${po_data['total_cost']}

Generated by AI Procurement Demo
"""
    msg = EmailMessage()
    msg["Subject"] = "Your Purchase Order"
    msg["From"] = formataddr(("AI Procurement Bot", "noreply@example.com"))
    msg["To"] = recipient_email
    msg.set_content(body)

    # NOTE: For real usage, configure your SMTP properly
    # This is just a mock or example
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    sender_email = "noreply@example.com"
    sender_password = "YOUR_APP_PASSWORD"

    context = ssl.create_default_context()
    # HACK
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    # END HACK
    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.ehlo()
        server.starttls(context=context)
        server.ehlo()
        server.login(sender_email, sender_password)
        server.send_message(msg)


###############################################################
# Vendor Data + Searching / Recommending
###############################################################
# We'll store "FakeStore" items or custom sellers in memory for a session
VENDORS = []  # we can store dicts like { name, item, price, stock, ... }

@app.post("/recommend")
def recommend_step(payload: dict = Body(...)):
    """
    Called after we have item_name, quantity, preference, multi_vendor, etc.
    Also possibly custom_sellers or empty (which means we did the FakeStore).
    We'll unify them into a single list, do a naive match, and return top options.
    """
    item_name = payload.get("item_name", "Laptop")
    quantity = int(payload.get("quantity", 1))
    preference = payload.get("preference", "cost")
    multi_vendor = payload.get("multi_vendor", False)
    custom_sellers = payload.get("custom_sellers", [])

    # If custom_sellers is not empty, use that
    # else we rely on the global VENDORS if we assume the user called /import-fakestore
    if custom_sellers:
        merged = custom_sellers
    else:
        merged = VENDORS  # from FakeStore

    # match logic
    results = []
    for seller in merged:
        # We'll do a simple substring match
        item_str = seller.get("item") or seller.get("product_name") or ""
        if item_name.lower() in item_str.lower():
            # check stock
            st = seller.get("stock", 0)
            if st >= quantity:
                # compute total cost
                pr = seller.get("price", 9999)
                tot = pr * quantity
                results.append({
                    "vendor_name": seller.get("name", "NoName"),
                    "product_name": item_str,
                    "sku": seller.get("sku", ""),
                    "price": pr,
                    "stock": st,
                    "quantity": quantity,
                    "unit_price": pr,
                    "total_cost": tot
                })
    # sort by cost for now ignoring preference
    results.sort(key=lambda x: x["total_cost"])
    # We just return them in ascending cost
    return {"options": results}

@app.get("/pos")
def get_finalized_pos():
    return FINALIZED_POS

@app.post("/save-po")
def save_po(po_data: dict):
    # Save the PO to our global log
    FINALIZED_POS.append(po_data)
    return {"status": "saved"}

###############################################################
# Fake Store
###############################################################
FAKESTORE_URL = "https://fakestoreapi.com/products"

@app.get("/import-fakestore")
def import_fakestore(category: str = None):
    """
    If category is given, we do /products/category/<cat>
    else /products
    Then store them in VENDORS
    """
    global VENDORS
    if category:
        url = f"{FAKESTORE_URL}/category/{category}"
    else:
        url = FAKESTORE_URL
    try:
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            return {"error": f"FakeStore returned {r.status_code}"}
        data = r.json()
        # transform data into a standard { name, item, price, stock } form
        # We'll assume stock=50
        for p in data:
            VENDORS.append({
                "name": "FakeStore Vendor",
                "item": p["title"],
                "price": p["price"],
                "stock": 50,
                "sku": f"fakestore-{p['id']}",
                "email": "sales@fakestore.com"  # mock
            })
        return {"message": f"Added {len(data)} products from Fake Store API to 'FakeStore Vendor'."}
    except Exception as e:
        return {"error": str(e)}

###############################################################
# Serve the single-page UI
###############################################################
@app.get("/", response_class=HTMLResponse)
def index():
    return INDEX_HTML

###############################################################
# The finalize-po endpoint (PDF/Email)
###############################################################
@app.post("/finalize-po")
def finalize_po(payload: dict = Body(...)):
    """
    Expects:
    {
      "po_data": {...},
      "mode": "pdf" or "email",
      "recipient_email": "..."
    }
    """
    po_data = payload.get("po_data")
    mode = payload.get("mode")
    recipient_email = payload.get("recipient_email", "")
    if not po_data or not mode:
        return {"error": "Missing 'po_data' or 'mode' in the request"}

    if mode == "pdf":
        pdf_bytes = generate_po_pdf(po_data)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(pdf_bytes)
            tmp.flush()
            return FileResponse(
                path=tmp.name,
                filename="purchase_order.pdf",
                media_type="application/pdf"
            )
    elif mode == "email":
        if not recipient_email:
            return {"error": "recipient_email is required if mode=email"}

        # Instead of sending email via SMTP, generate a mailto link
        import urllib.parse
        subject = "Purchase Order"
        body = f"""Purchase Order:
Vendor: {po_data['vendor_name']}
Product: {po_data['product_name']}
Quantity: {po_data['quantity']}
Unit Price: ${po_data['unit_price']}
Total Cost: ${po_data['total_cost']}

Generated by AI Procurement Demo
"""
        subject_enc = urllib.parse.quote(subject, safe='')
        body_enc = urllib.parse.quote(body, safe='')

        mailto_link = f"mailto:{recipient_email}?subject={subject_enc}&body={body_enc}"

        return {"mailto_link": mailto_link}

    else:
        return {"error": f"Unknown mode '{mode}'. Use 'pdf' or 'email'."}

