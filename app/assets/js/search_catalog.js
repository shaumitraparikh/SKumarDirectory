const CommerceCore = window.CatalogCommerce;
const CART_STORAGE_KEY = "skumar-catalog-cart-v1";
const isLocalEnv = (location.hostname === "127.0.0.1" || location.hostname === "localhost") && location.protocol !== "https:";

const billArchive = new CatalogBillArchive.BillArchive({
  window,
  indexedDB: window.indexedDB,
});
let cart = Object.create(null);
let lastOrder = null;
let clientRecords = [];
let visibleBills = new Map();
function normalizeSearchText(value) {
  return String(value || "")
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLocaleLowerCase()
    .trim();
}

function parseNumericPrice(listPrice) {
  if (!listPrice) return null;
  const cleaned = String(listPrice).trim().replace(/,/g, "");
  const num = Number(cleaned);
  return Number.isFinite(num) && num >= 0 ? num : null;
}

const catalogDataElement = document.getElementById("catalogData");
const rawCatalog = catalogDataElement
  ? JSON.parse(catalogDataElement.textContent)
  : [];
const catalogSearchIndex = rawCatalog.map((item, index) => ({
  item,
  originalIndex: index,
  numericPrice: parseNumericPrice(item.list_price),
  searchableText:
    item.search_text ||
    normalizeSearchText(
      [
        item.item_name,
        item.category,
        item.hsn_code,
        item.sr_number,
        item.size,
        item.id_size,
        item.od_size,
        item.lf_size,
      ].join(" "),
    ),
}));

billArchive.restoreDirectory().catch((error) => {
  console.error("Unable to restore the generated-bills folder.", error);
});

let allSavedBills = [];

function formatMonthLabel(monthStr) {
  if (!monthStr) return "Unknown Date";
  try {
    const d = new Date(`${monthStr}-01T00:00:00Z`);
    if (isNaN(d.getTime())) return monthStr;
    return d.toLocaleDateString("en-IN", {
      month: "long",
      year: "numeric",
      timeZone: "UTC",
    });
  } catch (e) {
    return monthStr;
  }
}

function populateMonthFilter(entries) {
  const select = document.getElementById("billMonthFilter");
  if (!select) return;
  const currentVal = select.value;
  const counts = new Map();
  entries.forEach((e) => {
    const m = e.month || "Other";
    counts.set(m, (counts.get(m) || 0) + 1);
  });

  const months = Array.from(counts.keys()).sort().reverse();
  select.replaceChildren();

  const allOpt = document.createElement("option");
  allOpt.value = "all";
  allOpt.textContent = `📅 All Months & Years (${entries.length})`;
  select.appendChild(allOpt);

  months.forEach((m) => {
    const opt = document.createElement("option");
    opt.value = m;
    opt.textContent = `${formatMonthLabel(m)} (${counts.get(m)})`;
    select.appendChild(opt);
  });

  if (months.includes(currentVal)) {
    select.value = currentVal;
  } else {
    select.value = "all";
  }
}

function applySavedBillFilters() {
  const searchInput = document.getElementById("billSearchInput");
  const monthSelect = document.getElementById("billMonthFilter");
  const query = (searchInput?.value || "").trim().toLowerCase();
  const selectedMonth = monthSelect?.value || "all";

  const filtered = allSavedBills.filter((entry) => {
    if (selectedMonth !== "all" && entry.month !== selectedMonth) {
      return false;
    }
    if (query) {
      const haystack = [
        entry.reference,
        entry.buyerName,
        entry.month,
        entry.grandTotal,
        entry.fileName,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      if (!haystack.includes(query)) return false;
    }
    return true;
  });

  const countBadge = document.getElementById("billCountBadge");
  if (countBadge) {
    countBadge.textContent = `${filtered.length} bill${filtered.length === 1 ? "" : "s"}`;
  }

  renderSavedBills(filtered, Boolean(query || selectedMonth !== "all"));
}

function renderSavedBills(entries, isFiltered = false) {
  const list = document.getElementById("billArchiveList");
  if (!list) return;
  list.replaceChildren();
  visibleBills = new Map(entries.map((entry) => [entry.id, entry]));

  if (!entries.length) {
    const empty = document.createElement("div");
    empty.className = "bill-empty-state";
    const icon = document.createElement("span");
    icon.className = "bill-empty-icon";
    icon.textContent = isFiltered ? "🔍" : "📄";
    const strong = document.createElement("strong");
    strong.textContent = isFiltered
      ? "No matching bills found"
      : "No saved bills yet";
    const desc = document.createElement("p");
    desc.textContent = isFiltered
      ? "Try adjusting your search terms or date filter."
      : 'Bills are automatically organized here when you click "Save Proforma Bill" or generate an invoice.';
    empty.append(icon, strong, desc);
    list.appendChild(empty);
    return;
  }

  const byMonth = new Map();
  entries.forEach((entry) => {
    const m = entry.month || "Other";
    if (!byMonth.has(m)) byMonth.set(m, []);
    byMonth.get(m).push(entry);
  });

  let isFirst = true;
  byMonth.forEach((monthEntries, month) => {
    const section = document.createElement("details");
    section.className = "bill-month";
    if (isFirst || isFiltered) {
      section.open = true;
      isFirst = false;
    }

    const summary = document.createElement("summary");
    const titleWrap = document.createElement("div");
    titleWrap.className = "bill-month-title-wrap";
    const icon = document.createElement("span");
    icon.textContent = "📅";
    const name = document.createElement("span");
    name.textContent = formatMonthLabel(month);
    titleWrap.append(icon, name);

    const badge = document.createElement("span");
    badge.className = "bill-month-badge";
    badge.textContent = `${monthEntries.length} bill${monthEntries.length === 1 ? "" : "s"}`;

    summary.append(titleWrap, badge);
    section.appendChild(summary);

    const monthList = document.createElement("div");
    monthList.className = "bill-month-list";

    monthEntries.forEach((entry) => {
      const row = document.createElement("div");
      row.className = "bill-entry";

      const info = document.createElement("div");
      info.className = "bill-entry-info";

      const top = document.createElement("div");
      top.className = "bill-entry-top";

      const refBadge = document.createElement("span");
      refBadge.className = "bill-ref-badge";
      refBadge.textContent = entry.reference;

      const buyer = document.createElement("span");
      buyer.className = "bill-buyer-name";
      buyer.textContent = entry.buyerName || "Cash customer";
      buyer.title = entry.buyerName || "Cash customer";

      top.append(refBadge, buyer);

      const meta = document.createElement("div");
      meta.className = "bill-entry-meta";

      const dateSpan = document.createElement("span");
      dateSpan.className = "bill-meta-date";
      dateSpan.textContent = `📅 ${entry.billDate || entry.savedAt?.slice(0, 10) || entry.month}`;
      meta.appendChild(dateSpan);

      if (entry.grandTotal) {
        const totalSpan = document.createElement("span");
        totalSpan.className = "bill-meta-amount";
        totalSpan.textContent = `₹${entry.grandTotal}`;
        meta.appendChild(totalSpan);
      }

      const storageSpan = document.createElement("span");
      storageSpan.className = "bill-meta-storage";
      storageSpan.textContent =
        entry.storage === "folder"
          ? `📁 generated_bills/${entry.month}/`
          : "💾 Browser archive";
      meta.appendChild(storageSpan);

      info.append(top, meta);

      const btns = document.createElement("div");
      btns.className = "bill-entry-actions";

      const openBtn = document.createElement("button");
      openBtn.className = "bill-btn bill-open-btn";
      openBtn.type = "button";
      openBtn.textContent = "Open ↗";
      openBtn.title = "Open bill in a new tab";
      openBtn.dataset.billId = entry.id;
      openBtn.dataset.action = "open";

      const printBtn = document.createElement("button");
      printBtn.className = "bill-btn bill-print-btn";
      printBtn.type = "button";
      printBtn.textContent = "Print 🖨️";
      printBtn.title = "Open bill in a new tab and print";
      printBtn.dataset.billId = entry.id;
      printBtn.dataset.action = "print";

      btns.append(openBtn, printBtn);
      row.append(info, btns);
      monthList.appendChild(row);
    });

    section.appendChild(monthList);
    list.appendChild(section);
  });
}

async function refreshSavedBills() {
  const status = document.getElementById("billArchiveStatus");
  const chooseBtn = document.getElementById("chooseBillsFolderButton");
  if (status) status.textContent = "Loading saved bills…";
  try {
    const entries = await billArchive.listBills();
    allSavedBills = entries || [];
    populateMonthFilter(allSavedBills);
    applySavedBillFilters();

    if (status) {
      status.textContent = billArchive.directoryHandle
        ? `✓ Connected to ${billArchive.directoryHandle.name}/. Monthly folders synchronized.`
        : "✓ Bills auto-saved & organized by month & year.";
    }
    if (chooseBtn) {
      if (billArchive.directoryHandle) {
        chooseBtn.textContent = `✓ Folder: ${billArchive.directoryHandle.name} (Change)`;
        chooseBtn.classList.add("connected");
      } else {
        chooseBtn.textContent = "📁 Sync Local Folder";
        chooseBtn.classList.remove("connected");
      }
    }
  } catch (error) {
    console.error("Unable to read saved bills.", error);
    if (status)
      status.textContent = error.message || "Could not read saved bills.";
  }
}

document.getElementById("openBillsButton")?.addEventListener("click", () => {
  const dialog = document.getElementById("billArchiveDialog");
  if (!dialog) return;
  if (typeof dialog.showModal === "function") dialog.showModal();
  else dialog.setAttribute("open", "");
  refreshSavedBills();
});

document
  .getElementById("closeBillArchiveButton")
  ?.addEventListener("click", () => {
    const dialog = document.getElementById("billArchiveDialog");
    if (!dialog) return;
    if (typeof dialog.close === "function") dialog.close();
    else dialog.removeAttribute("open");
  });

document.getElementById("billSearchInput")?.addEventListener("input", () => {
  applySavedBillFilters();
});

document.getElementById("billMonthFilter")?.addEventListener("change", () => {
  applySavedBillFilters();
});

document
  .getElementById("chooseBillsFolderButton")
  ?.addEventListener("click", () => {
    const status = document.getElementById("billArchiveStatus");
    if (status)
      status.textContent =
        "Choose the data or generated_bills folder to synchronize.";
    try {
      billArchive
        .selectDirectory()
        .then(() => {
          if (status)
            status.textContent =
              "Folder selected. Monthly folders synchronized.";
          refreshSavedBills();
        })
        .catch((error) => {
          if (error.name === "AbortError") {
            if (status) status.textContent = "Folder selection was cancelled.";
            return;
          }
          console.error("Unable to select folder.", error);
          if (status)
            status.textContent = error.message || "Could not select folder.";
        });
    } catch (error) {
      console.error("Unable to select folder.", error);
      if (status)
        status.textContent =
          error.message || "Folder selection is unavailable.";
    }
  });

document
  .getElementById("billArchiveList")
  ?.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-bill-id]");
    if (!button) return;
    const action = button.dataset.action;
    const entry = visibleBills.get(button.dataset.billId);
    if (!entry) return;

    if (action === "open") {
      billArchive.openBill(entry, false);
    } else if (action === "print") {
      billArchive.openBill(entry, true);
    }
  });

function extractCustomersFromSavedBills(bills) {
  if (!bills || !Array.isArray(bills)) return [];
  const extracted = [];
  bills.forEach((bill) => {
    const html = bill.html;
    if (!html) return;
    const billedToMatch = html.match(/Billed To[^<]*<\/h4>([\s\S]*?)<\/div>/i);
    if (!billedToMatch) return;
    const box = billedToMatch[1];

    const nameMatch =
      box.match(/id=["']pBuyerName["'][^>]*>([^<]+)</) ||
      box.match(/<strong[^>]*>([^<]+)<\/strong>/);
    const buyerName = nameMatch ? nameMatch[1].trim() : "";
    if (!buyerName || buyerName.toLowerCase() === "cash customer") return;

    let phone = "";
    const phoneMatch =
      box.match(/📞\s*([0-9\s+-]+)/) ||
      box.match(/(?:Mob|Phone|Tel|WhatsApp)[:\s]+([0-9\s+-]+)/i) ||
      box.match(/\b([6-9]\d{9})\b/);
    if (phoneMatch) phone = phoneMatch[1].replace(/\D/g, "").slice(-10);

    let gstin = "";
    const gstinMatch = box.match(/GSTIN:\s*([0-9A-Z]{15})/i);
    if (gstinMatch) gstin = gstinMatch[1].toUpperCase();

    let address = "";
    const lines = box
      .split(/<br\s*\/?>|<\/?span>/i)
      .map((l) => l.replace(/<[^>]+>/g, "").trim())
      .filter(Boolean);
    const addrLine = lines.find(
      (l) =>
        !l.includes(buyerName) &&
        !l.includes("📞") &&
        !l.includes("GSTIN:") &&
        l.length > 5,
    );
    if (addrLine) address = addrLine;

    let state = "";
    const stateMatch = html.match(
      /Supply Place:\s*([A-Za-z\s]+?)(?:\s*\(|$|<)/i,
    );
    if (stateMatch) state = stateMatch[1].trim();

    extracted.push({
      name: buyerName,
      business_name: buyerName,
      phone,
      gstin,
      address,
      state: state || "Maharashtra",
    });
  });
  return extracted;
}

const DEFAULT_DEMO_CUSTOMERS = [
  {
    name: "General Supply Corporation",
    business_name: "General Supply Corporation",
    phone: "9869905779",
    gstin: "27ACJPP2955J1Z4",
    address: "3rd Central Building, Grd. Floor, Kalbadevi, Mumbai - 400002",
    state: "Maharashtra",
    pincode: "400002",
  },
  {
    name: "Asha Shah",
    business_name: "Ace Electricals",
    phone: "9820011223",
    email: "asha@example.in",
    address: "12, Market Road, Mumbai",
    state: "Maharashtra",
    pincode: "400002",
    gstin: "27AAACE1234A1Z1",
  },
  {
    name: "Shaumitra Parikh",
    business_name: "S. Kumar & Bros",
    phone: "9821361314",
    gstin: "27AAGPP1621C1Z5",
    address: "38, Bapu Khote Street, Pydhonie, Mumbai - 400003",
    state: "Maharashtra",
    pincode: "400003",
  },
];

function mergeCustomers(lists) {
  const map = new Map();
  lists.forEach((list) => {
    if (!Array.isArray(list)) return;
    list.forEach((c) => {
      if (!c || (!c.name && !c.business_name && !c.gstin)) return;
      const normBiz = (c.business_name || c.name || "").trim().toLowerCase();
      const normGstin = (c.gstin || "").trim().toUpperCase();
      const key = normGstin ? `${normGstin}_${normBiz}` : normBiz;
      if (key) {
        if (map.has(key)) {
          map.set(key, Object.assign({}, map.get(key), c));
        } else {
          map.set(key, Object.assign({}, c));
        }
      }
    });
  });
  return Array.from(map.values());
}

function filterCustomersCore(customers, query, limit) {
  if (!Array.isArray(customers)) return [];
  const max = typeof limit === "number" ? limit : 50;
  const trimmed = (query || "").trim();
  if (!trimmed) return customers.slice(0, max);
  const lower = trimmed.toLowerCase();
  const digitsOnly = trimmed.replace(/\D/g, "");

  return customers
    .filter((c) => {
      if (!c) return false;
      const nameMatch =
        (c.name && c.name.toLowerCase().includes(lower)) ||
        (c.business_name && c.business_name.toLowerCase().includes(lower));
      if (nameMatch) return true;

      const gstinMatch = c.gstin && c.gstin.toLowerCase().includes(lower);
      if (gstinMatch) return true;

      const addrMatch =
        (c.address && c.address.toLowerCase().includes(lower)) ||
        (c.state && c.state.toLowerCase().includes(lower));
      if (addrMatch) return true;

      if (digitsOnly.length >= 3 && c.phone) {
        const cDigits = String(c.phone).replace(/\D/g, "");
        if (cDigits.includes(digitsOnly)) return true;
      }

      return false;
    })
    .slice(0, max);
}

if (window.ClientDirectory && typeof window.ClientDirectory === "object") {
  window.ClientDirectory.filterCustomers = filterCustomersCore;
}

let activeCustomerIdx = -1;

function renderCustomerSearchResults(results) {
  const container = document.getElementById("customerSearchResults");
  if (!container) return;
  container.replaceChildren();
  activeCustomerIdx = -1;

  if (!results || results.length === 0) {
    const empty = document.createElement("div");
    empty.className = "customer-search-empty";
    empty.textContent =
      'No matching saved customer found. Enter details below & click "💾 Save / Update" to store them.';
    container.appendChild(empty);
    container.style.display = "block";
    return;
  }

  results.forEach((customer, idx) => {
    const item = document.createElement("div");
    item.className = "customer-search-item";
    item.setAttribute("role", "option");
    item.dataset.index = idx;

    const title = document.createElement("div");
    title.className = "customer-search-item-title";
    title.textContent = customer.business_name || customer.name || "Customer";
    if (
      customer.name &&
      customer.business_name &&
      customer.name.toLowerCase() !== customer.business_name.toLowerCase()
    ) {
      title.textContent += ` (${customer.name})`;
    }

    const meta = document.createElement("div");
    meta.className = "customer-search-item-meta";

    if (customer.phone) {
      const phoneSpan = document.createElement("span");
      phoneSpan.textContent = `📞 ${customer.phone}`;
      meta.appendChild(phoneSpan);
    }
    if (customer.gstin) {
      const gstinSpan = document.createElement("span");
      gstinSpan.textContent = `📑 ${customer.gstin}`;
      meta.appendChild(gstinSpan);
    }
    if (customer.state || customer.address) {
      const locSpan = document.createElement("span");
      locSpan.textContent = `📍 ${customer.state || customer.address.slice(0, 25)}`;
      meta.appendChild(locSpan);
    }

    item.append(title, meta);
    const handleSelect = (e) => {
      if (e) e.preventDefault();
      applySelectedCustomer(customer);
      const lookup = document.getElementById("customerLookup");
      if (lookup) {
        lookup.value =
          window.ClientDirectory && ClientDirectory.displayLabel
            ? ClientDirectory.displayLabel(customer)
            : customer.business_name || customer.name;
      }
      hideCustomerDropdown();
    };

    item.addEventListener("mousedown", handleSelect);
    item.addEventListener("click", handleSelect);

    container.appendChild(item);
  });

  container.style.display = "block";
}

function hideCustomerDropdown() {
  const container = document.getElementById("customerSearchResults");
  if (container) container.style.display = "none";
  activeCustomerIdx = -1;
}

function applySelectedCustomer(customer) {
  document.getElementById("manualBuyerForm").style.display = "grid";
  const manualBtn = document.getElementById("enterManualBtn"); if(manualBtn) manualBtn.style.display = "none";


  if (!customer) return;
  document.getElementById("buyerName").value =
    customer.business_name || customer.name || "";
  document.getElementById("buyerPhone").value = customer.phone || "";
  document.getElementById("buyerEmail").value = customer.email || "";
  document.getElementById("buyerAddress").value = customer.address || "";
  const stateInput = document.getElementById("buyerState");
  if (stateInput) {
    const matchingState = Array.from(stateInput.options).find(
      (option) =>
        option.value.toLocaleLowerCase() ===
        (customer.state || "").toLocaleLowerCase(),
    );
    stateInput.value = matchingState ? matchingState.value : "";
  }
  document.getElementById("buyerPincode").value = customer.pincode || "";
  document.getElementById("buyerGstin").value = customer.gstin || "";
  const buyerDetails = document.getElementById("buyerDetails");
  if (buyerDetails) buyerDetails.open = true;

  const statusEl = document.getElementById("clientDirectoryStatus");
  if (statusEl) {
    statusEl.innerHTML = `<span style="color:#16a34a; font-weight:600;">✓ Auto-filled details for "${customer.business_name || customer.name}". You can review or edit below.</span>`;
  }
}

function setupClientData(records) {
  if (!records || !Array.isArray(records)) records = [];
  clientRecords = records;
  if (window.ClientDirectory) {
    window.ClientDirectory.clients = records;
    window.ClientDirectory.filterCustomers = filterCustomersCore;
  }
  const statusEl = document.getElementById("clientDirectoryStatus");
  if (statusEl) {
    statusEl.textContent = records.length
      ? `${records.length} saved customer${records.length === 1 ? "" : "s"} ready to search & auto-fill.`
      : "Search by name, phone, or GSTIN to auto-fill, or enter details below.";
  }
}

let localSavedClients = [];
try {
  const raw = localStorage.getItem("saved_client_records");
  if (raw) localSavedClients = JSON.parse(raw);
} catch (e) {}

const billExtractedClients = extractCustomersFromSavedBills(
  window.INJECTED_SAVED_BILLS || [],
);
const initialClients = mergeCustomers([
  window.INJECTED_CLIENT_DATA || [],
  localSavedClients,
  billExtractedClients,
  DEFAULT_DEMO_CUSTOMERS,
]);
setupClientData(initialClients);

// Auto-fetch local client_data.csv if served over HTTP/localhost
if (typeof fetch === "function" && location.protocol.startsWith("http")) {
  fetch("data/client_data.csv")
    .then((res) => (res.ok ? res.text() : Promise.reject()))
    .then((csvText) => {
      if (window.ClientDirectory && csvText) {
        const fetchedClients = ClientDirectory.parseCsv(csvText);
        if (fetchedClients && fetchedClients.length) {
          const combined = mergeCustomers([fetchedClients, clientRecords]);
          setupClientData(combined);
          try {
            localStorage.setItem(
              "saved_client_records",
              JSON.stringify(combined),
            );
          } catch (e) {}
        }
      }
    })
    .catch(() => {});
}

document.getElementById("saveClientButton")?.addEventListener("click", () => {
  const newClient = {
    name: (document.getElementById("buyerName").value || "").trim(),
    business_name: (document.getElementById("buyerName").value || "").trim(),
    phone: (document.getElementById("buyerPhone").value || "").trim(),
    email: (document.getElementById("buyerEmail").value || "").trim(),
    address: (document.getElementById("buyerAddress").value || "").trim(),
    state: (document.getElementById("buyerState").value || "").trim(),
    pincode: (document.getElementById("buyerPincode").value || "").trim(),
    gstin: (document.getElementById("buyerGstin").value || "").trim(),
  };
  if (!newClient.name && !newClient.gstin) {
    alert("Please enter a name or GSTIN to save the customer.");
    return;
  }

  const statusEl = document.getElementById("clientDirectoryStatus");
  const existingIdx = clientRecords.findIndex(
    (c) =>
      (newClient.name &&
        c.name &&
        c.name.trim().toLowerCase() === newClient.name.toLowerCase()) ||
      (newClient.gstin &&
        c.gstin &&
        c.gstin.trim().toUpperCase() === newClient.gstin.toUpperCase()),
  );
  if (existingIdx >= 0) {
    clientRecords[existingIdx] = Object.assign(
      {},
      clientRecords[existingIdx],
      newClient,
    );
  } else {
    clientRecords.unshift(newClient);
  }
  try {
    localStorage.setItem("saved_client_records", JSON.stringify(clientRecords));
  } catch (e) {}
  setupClientData(clientRecords);
  if (statusEl) {
    statusEl.innerHTML = `<span style="color:#16a34a; font-weight:600;">✓ Customer "${newClient.name || newClient.gstin}" saved & ready to auto-fill.</span>`;
  }
});

const lookupInput = document.getElementById("customerLookup");
if (lookupInput) {
  lookupInput.addEventListener("focus", () => {
    const val = lookupInput.value.trim();
    const matches = filterCustomersCore(clientRecords, val);
    renderCustomerSearchResults(matches);
  });

  lookupInput.addEventListener("input", (event) => {
    const val = event.target.value.trim();
    const matches = filterCustomersCore(clientRecords, val);
    renderCustomerSearchResults(matches);

    const selectedCustomer =
      window.ClientDirectory && ClientDirectory.findCustomer
        ? ClientDirectory.findCustomer(clientRecords, val)
        : null;
    if (selectedCustomer) {
      applySelectedCustomer(selectedCustomer);
    }
  });

  lookupInput.addEventListener("keydown", (e) => {
    const container = document.getElementById("customerSearchResults");
    if (!container || container.style.display === "none") return;
    const items = container.querySelectorAll(".customer-search-item");
    if (!items.length) return;

    if (e.key === "ArrowDown") {
      e.preventDefault();
      activeCustomerIdx = Math.min(items.length - 1, activeCustomerIdx + 1);
      items.forEach((it, i) =>
        it.classList.toggle("active", i === activeCustomerIdx),
      );
      if (items[activeCustomerIdx])
        items[activeCustomerIdx].scrollIntoView({ block: "nearest" });
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      activeCustomerIdx = Math.max(0, activeCustomerIdx - 1);
      items.forEach((it, i) =>
        it.classList.toggle("active", i === activeCustomerIdx),
      );
      if (items[activeCustomerIdx])
        items[activeCustomerIdx].scrollIntoView({ block: "nearest" });
    } else if (e.key === "Enter") {
      e.preventDefault();
      const target =
        activeCustomerIdx >= 0 ? items[activeCustomerIdx] : items[0];
      if (target) {
        target.dispatchEvent(
          new MouseEvent("mousedown", { bubbles: true, cancelable: true }),
        );
      }
    } else if (e.key === "Escape") {
      hideCustomerDropdown();
    }
  });
}

function hideCartProductSearchDropdown() {
  const dd = document.getElementById("cartProductSearchResults");
  if (dd) dd.style.display = "none";
}

function initCartProductSearch() {
  const input = document.getElementById("cartProductSearch");
  const dropdown = document.getElementById("cartProductSearchResults");
  if (!input || !dropdown) return;

  let activeProductIdx = -1;

  function renderProductResults(matches) {
    dropdown.replaceChildren();
    activeProductIdx = -1;

    if (!matches || matches.length === 0) {
      const empty = document.createElement("div");
      empty.className = "customer-search-empty";
      empty.textContent = "No matching catalog products found.";
      dropdown.appendChild(empty);
      dropdown.style.display = "block";
      return;
    }

    matches.forEach((entry, idx) => {
      const item = entry.item;
      const row = document.createElement("div");
      row.className = "cart-product-search-item";
      row.dataset.index = idx;

      if (item.display_image_path) {
        const img = document.createElement("img");
        img.src = item.display_image_path;
        img.className = "cart-product-search-thumb";
        img.alt = item.item_name;
        row.appendChild(img);
      }

      const info = document.createElement("div");
      info.className = "cart-product-search-info";

      const name = document.createElement("div");
      name.className = "cart-product-search-name";
      name.textContent = item.item_name;

      const meta = document.createElement("div");
      meta.className = "cart-product-search-meta";
      meta.innerHTML =
        `<span>Sr: ${item.sr_number}</span>` +
        (item.hsn_code ? `<span>HSN: ${item.hsn_code}</span>` : "") +
        (item.unit ? `<span>Unit: ${item.unit}</span>` : "") +
        (item.list_price
          ? `<span class="cart-product-search-price">₹${item.list_price}</span>`
          : '<span class="cart-product-search-price">Quote only</span>');

      info.append(name, meta);
      row.appendChild(info);

      const addBtn = document.createElement("button");
      addBtn.type = "button";
      addBtn.className = "cart-product-quick-add";
      addBtn.textContent = "+ Add";
      addBtn.title = `Add ${item.item_name} to cart`;
      addBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        addToCart(String(item.sr_number));
        input.value = "";
        dropdown.style.display = "none";
        showToast(`Added ${item.item_name} to cart`);
      });

      row.appendChild(addBtn);

      row.addEventListener("click", () => {
        addToCart(String(item.sr_number));
        input.value = "";
        dropdown.style.display = "none";
        showToast(`Added ${item.item_name} to cart`);
      });

      dropdown.appendChild(row);
    });

    dropdown.style.display = "block";
  }

  input.addEventListener("input", () => {
    const raw = input.value.trim();
    const query = normalizeSearchText(raw);
    if (!query) {
      dropdown.style.display = "none";
      return;
    }
    const matches = [];
    for (let i = 0; i < catalogSearchIndex.length; i++) {
      const entry = catalogSearchIndex[i];
      const text = entry.searchableText;
      let score = 0;
      if (text.includes(query)) {
        score = 1.0;
        if (
          entry.item.item_name &&
          entry.item.item_name.toLowerCase().includes(query)
        ) {
          score = 1.5;
        }
      } else {
        score = fuzzyScore(text, query);
      }
      if (score >= 0.45) {
        matches.push({ entry, score });
      }
    }
    matches.sort((a, b) => b.score - a.score);
    renderProductResults(matches.slice(0, 10).map((m) => m.entry));
  });

  input.addEventListener("keydown", (e) => {
    if (dropdown.style.display === "none") return;
    const items = dropdown.querySelectorAll(".cart-product-search-item");
    if (!items.length) return;

    if (e.key === "ArrowDown") {
      e.preventDefault();
      activeProductIdx = Math.min(items.length - 1, activeProductIdx + 1);
      items.forEach((it, i) =>
        it.classList.toggle("active", i === activeProductIdx),
      );
      if (items[activeProductIdx])
        items[activeProductIdx].scrollIntoView({ block: "nearest" });
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      activeProductIdx = Math.max(0, activeProductIdx - 1);
      items.forEach((it, i) =>
        it.classList.toggle("active", i === activeProductIdx),
      );
      if (items[activeProductIdx])
        items[activeProductIdx].scrollIntoView({ block: "nearest" });
    } else if (e.key === "Enter") {
      e.preventDefault();
      const target = activeProductIdx >= 0 ? items[activeProductIdx] : items[0];
      if (target) {
        target.querySelector(".cart-product-quick-add")?.click();
      }
    } else if (e.key === "Escape") {
      dropdown.style.display = "none";
    }
  });
}

document.addEventListener("click", (event) => {
  if (!event.target.closest(".customer-lookup-box")) {
    hideCustomerDropdown();
  }
  if (!event.target.closest(".cart-product-search-wrap")) {
    hideCartProductSearchDropdown();
  }
});

function toggleCart(forceOpen) {
  const drawer = document.getElementById("cartDropdown");
  const isOpen = drawer.classList.contains("open");
  const shouldOpen = typeof forceOpen === "boolean" ? forceOpen : !isOpen;
  drawer.classList.toggle("open", shouldOpen);
  document.getElementById("cartBackdrop").classList.toggle("open", shouldOpen);
  drawer.setAttribute("aria-hidden", String(!shouldOpen));
  document
    .querySelector(".cart-toggle-btn")
    .setAttribute("aria-expanded", String(shouldOpen));
  document.body.style.overflow = shouldOpen ? "hidden" : "";
  if (shouldOpen) {
    document.querySelector(".close-cart").focus();
  } else {
    document.querySelector(".cart-toggle-btn").focus();
  }
}

document.addEventListener("keydown", (event) => {
  if (
    event.key === "Escape" &&
    document.getElementById("cartDropdown").classList.contains("open")
  ) {
    toggleCart(false);
  }
});

function showToast(msg) {
  const t = document.getElementById("toast");
  t.innerText = msg;
  t.className = "show";
  setTimeout(() => {
    t.className = t.className.replace("show", "");
  }, 2000);
}

function createCard(item) {
  const card = document.createElement("div");
  card.className = "card";
  card.dataset.srNumber = item.sr_number;
  card.title = "Click anywhere to view image & full item details";

  card.addEventListener("click", (event) => {
    if (
      event.target.closest(".add-controls, button, input, a, select, textarea")
    ) {
      return;
    }
    openLightbox(item.sr_number);
  });

  const imgContainer = document.createElement("div");
  imgContainer.className = "card-img-container";
  if (item.display_image_path) {
    const img = document.createElement("img");
    img.src = item.display_image_path;
    img.className =
      "card-img" +
      (item.image_is_representative ? " representative-image" : "");
    img.alt = item.image_is_representative
      ? "Representative image for " + item.category
      : item.item_name;
    img.loading = "lazy";
    img.decoding = "async";

    img.style.cursor = "zoom-in";
    img.onclick = (e) => {
      e.stopPropagation();
      openLightbox(item.sr_number);
    };
    imgContainer.appendChild(img);
  } else {
    const noImg = document.createElement("div");
    noImg.style.cssText = "color:#aaa; font-size:10px; font-style:italic;";
    noImg.textContent = "No Image";
    imgContainer.appendChild(noImg);
  }
  card.appendChild(imgContainer);

  const content = document.createElement("div");
  content.className = "card-content";
  const title = document.createElement("p");
  title.className = "card-title";
  title.id = "name-" + item.sr_number;
  title.textContent = item.item_name;
  content.appendChild(title);

  const meta1 = document.createElement("p");
  meta1.className = "card-meta";
  meta1.innerHTML = `Sr: ${item.sr_number} | HSN: <span class="hsn-val">${item.hsn_code || ""}</span>`;
  content.appendChild(meta1);

  if (
    item.size &&
    !item.item_name.toLowerCase().includes(item.size.toLowerCase())
  ) {
    const metaSize = document.createElement("p");
    metaSize.className = "card-meta";
    metaSize.innerHTML = `Size: <span class="size-val">${item.size}</span>`;
    content.appendChild(metaSize);
  }

  if (item.id_size || item.od_size || item.lf_size) {
    const metaSizes = document.createElement("p");
    metaSizes.className = "card-meta";
    const parts = [];
    if (item.id_size)
      parts.push(`ID Size: <span class="id-size-val">${item.id_size}</span>`);
    if (item.od_size)
      parts.push(`OD Size: <span class="od-size-val">${item.od_size}</span>`);
    if (item.lf_size)
      parts.push(`L/F Size: <span class="lf-size-val">${item.lf_size}</span>`);
    metaSizes.innerHTML = parts.join(" · ");
    content.appendChild(metaSizes);
  }

  const metaUnit = document.createElement("p");
  metaUnit.className = "card-meta";
  const unitParts = [];
  if (item.unit)
    unitParts.push(`Unit: <span class="unit-val">${item.unit}</span>`);
  if (item.packing)
    unitParts.push(`Pack: <span class="packing-val">${item.packing}</span>`);
  if (unitParts.length) {
    metaUnit.innerHTML = unitParts.join(" · ");
    content.appendChild(metaUnit);
  }

  const price = document.createElement("p");
  if (item.list_price) {
    price.className = "card-price";
    price.innerHTML = `₹<span id="price-${item.sr_number}">${item.list_price}</span>`;
  } else {
    price.className = "card-price quote-price";
    price.innerHTML = `Price on request<span id="price-${item.sr_number}" hidden></span>`;
  }
  content.appendChild(price);
  card.appendChild(content);

  const controls = document.createElement("div");
  controls.className = "add-controls";
  const qtyInput = document.createElement("input");
  qtyInput.type = "number";
  qtyInput.id = "qty-" + item.sr_number;
  qtyInput.className = "qty-input";
  qtyInput.value = "1";
  qtyInput.min = "1";
  qtyInput.max = "9999";
  qtyInput.step = "1";
  qtyInput.setAttribute("aria-label", `Quantity for ${item.item_name}`);

  const addBtn = document.createElement("button");
  addBtn.className = "add-btn";
  addBtn.textContent = item.list_price ? "Add" : "Add to quote";
  addBtn.onclick = () => addToCart(String(item.sr_number));

  controls.appendChild(qtyInput);
  controls.appendChild(addBtn);
  card.appendChild(controls);

  return card;
}

function characterOverlap(a, b) {
  if (a.length < 2 || b.length < 2) return 0;
  let matches = 0;
  const bChars = new Set(b.split(""));
  for (const c of a) if (bChars.has(c)) matches++;
  const ratio = matches / Math.max(a.length, b.length);
  return ratio > 0.6 ? ratio * 0.8 : 0;
}

function fuzzyScore(text, query) {
  if (!query) return 1;
  if (!text) return 0;
  if (text.includes(query)) return 1;

  const tokens = query.split(/\s+/).filter(Boolean);
  if (!tokens.length) return 1;

  let totalScore = 0;
  const words = text.split(/\s+/);

  for (const token of tokens) {
    if (text.includes(token)) {
      totalScore += 1;
      continue;
    }
    let bestWordScore = 0;
    for (const word of words) {
      if (word.startsWith(token) || token.startsWith(word)) {
        bestWordScore = Math.max(bestWordScore, 0.9);
      } else {
        const overlap = characterOverlap(token, word);
        bestWordScore = Math.max(bestWordScore, overlap);
      }
    }
    if (bestWordScore < 0.4) return 0;
    totalScore += bestWordScore;
  }
  return totalScore / tokens.length;
}

function initCategoryPicker() {
  const wrap = document.getElementById("categoryPickerWrap");
  const btn = document.getElementById("categoryPickerBtn");
  const label = document.getElementById("categoryPickerLabel");
  const panel = document.getElementById("categoryDropdownPanel");
  const searchInput = document.getElementById("categorySearchInput");
  const list = document.getElementById("categoryOptionsList");
  const nativeSelect = document.getElementById("categoryFilter");

  if (!wrap || !btn || !panel || !list) return;

  function closePanel() {
    panel.hidden = true;
    btn.setAttribute("aria-expanded", "false");
    if (searchInput) searchInput.value = "";
    filterCategoryOptions("");
  }

  function openPanel() {
    panel.hidden = false;
    btn.setAttribute("aria-expanded", "true");
    if (searchInput) {
      searchInput.value = "";
      filterCategoryOptions("");
      setTimeout(() => searchInput.focus(), 60);
    }
  }

  btn.addEventListener("click", (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (panel.hidden) {
      openPanel();
    } else {
      closePanel();
    }
  });

  panel.addEventListener("click", (e) => {
    e.stopPropagation();
  });

  document.addEventListener("click", (e) => {
    if (!wrap.contains(e.target)) {
      closePanel();
    }
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !panel.hidden) {
      closePanel();
      btn.focus();
    }
  });

  function filterCategoryOptions(query) {
    const q = normalizeSearchText(query);
    const items = list.querySelectorAll(".category-opt-item");
    items.forEach((el) => {
      const cat = el.dataset.category || "";
      const nameEl = el.querySelector(".opt-name");
      const name = nameEl ? nameEl.textContent : cat;
      const fullText = normalizeSearchText(cat + " " + name);
      const isMatch = !q || fullText.includes(q);
      el.style.display = isMatch ? "flex" : "none";
    });
  }

  if (searchInput) {
    searchInput.addEventListener("input", (e) => {
      filterCategoryOptions(e.target.value);
    });
    searchInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        const firstVisible = Array.from(
          list.querySelectorAll(".category-opt-item"),
        ).find((el) => el.style.display !== "none");
        if (firstVisible) {
          firstVisible.click();
          e.preventDefault();
        }
      }
    });
  }

  list.addEventListener("click", (e) => {
    const itemBtn = e.target.closest(".category-opt-item");
    if (!itemBtn) return;
    const catVal = itemBtn.dataset.category || "";
    selectCategory(catVal);
    closePanel();
  });

  window.selectCategory = function (catVal) {
    if (nativeSelect) nativeSelect.value = catVal;
    const items = list.querySelectorAll(".category-opt-item");
    let selectedName = "All Categories";
    items.forEach((el) => {
      const isMatch = (el.dataset.category || "") === catVal;
      el.classList.toggle("active", isMatch);
      el.setAttribute("aria-selected", isMatch ? "true" : "false");
      if (isMatch) {
        const nameEl = el.querySelector(".opt-name");
        if (nameEl) selectedName = nameEl.textContent;
      }
    });
    if (label) label.textContent = selectedName;
    filterCatalog();
  };

  if (nativeSelect) {
    nativeSelect.addEventListener("change", () => {
      selectCategory(nativeSelect.value);
    });
  }
}

function initCatalogCacheAndPrefs() {
  const currentVersion = document.body.dataset.catalogVersion || "v1";
  const storedVersion = localStorage.getItem("skumar_catalog_version");

  if (storedVersion && storedVersion !== currentVersion) {
    console.log(
      `[Cache] Catalog update detected: ${storedVersion} -> ${currentVersion}. Refreshing cache.`,
    );
    localStorage.removeItem("skumar_sort_pref");
    if ("caches" in window) {
      caches.keys().then((names) => {
        names.forEach((name) => {
          if (
            name.startsWith("skumar-catalog-") &&
            !name.includes(currentVersion)
          ) {
            caches.delete(name);
          }
        });
      });
    }
  }
  localStorage.setItem("skumar_catalog_version", currentVersion);

  const sortSelect = document.getElementById("sortBy");
  if (sortSelect) {
    const savedSort = localStorage.getItem("skumar_sort_pref");
    if (
      savedSort &&
      ["default", "price-asc", "price-desc", "name-asc"].includes(savedSort)
    ) {
      sortSelect.value = savedSort;
    }
    sortSelect.addEventListener("change", () => {
      localStorage.setItem("skumar_sort_pref", sortSelect.value);
    });
  }
}

let currentMatchingEntries = [];
let renderBatchIndex = 0;
const BATCH_SIZE = 48;
let gridObserver = null;

function filterCatalog() {
  const grid = document.getElementById("catalogGrid");
  if (!grid) return;

  const searchInputEl = document.getElementById("searchInput");
  const input = normalizeSearchText(searchInputEl ? searchInputEl.value : "");
  const categoryFilter = document.getElementById("categoryFilter");
  const selectedCategory = categoryFilter ? categoryFilter.value : "";
  const sortBySelect = document.getElementById("sortBy");
  const sortBy = sortBySelect ? sortBySelect.value : "default";

  // URL Sync
  const url = new URL(window.location);
  if (input) url.searchParams.set("q", input); else url.searchParams.delete("q");
  if (selectedCategory) url.searchParams.set("category", selectedCategory); else url.searchParams.delete("category");
  window.history.replaceState({}, "", url);

  let matchCount = 0;
  matchingEntries = []; // We use a local variable matchingEntries

  catalogSearchIndex.forEach((entry) => {
    const matchesCategory = !selectedCategory || entry.item.category === selectedCategory;
    if (!matchesCategory) {
      entry.score = 0;
      if(entry.card) entry.card.style.display = "none";
      return;
    }

    if (input) {
      entry.score = fuzzyScore(entry.searchableText, input);
    } else {
      entry.score = 1;
    }

    if (entry.score >= 0.4) {
      matchCount++;
      matchingEntries.push(entry);
    } else {
      if(entry.card) entry.card.style.display = "none";
    }
  });

  if (sortBy === "price-asc") {
    matchingEntries.sort((a, b) => {
      if (a.numericPrice === null && b.numericPrice === null) return a.originalIndex - b.originalIndex;
      if (a.numericPrice === null) return 1;
      if (b.numericPrice === null) return -1;
      if (a.numericPrice !== b.numericPrice) return a.numericPrice - b.numericPrice;
      return a.originalIndex - b.originalIndex;
    });
  } else if (sortBy === "price-desc") {
    matchingEntries.sort((a, b) => {
      if (a.numericPrice === null && b.numericPrice === null) return a.originalIndex - b.originalIndex;
      if (a.numericPrice === null) return 1;
      if (b.numericPrice === null) return -1;
      if (a.numericPrice !== b.numericPrice) return b.numericPrice - a.numericPrice;
      return a.originalIndex - b.originalIndex;
    });
  } else if (sortBy === "name-asc") {
    matchingEntries.sort((a, b) => (a.item.item_name || "").localeCompare(b.item.item_name || ""));
  } else {
    if (input) {
      matchingEntries.sort((a, b) => b.score - a.score);
    } else {
      matchingEntries.sort((a, b) => a.originalIndex - b.originalIndex);
    }
  }

  const countIndicator = document.getElementById("searchResultCount");
  if (countIndicator) {
    let sortLabel = "";
    if (sortBy === "price-asc") sortLabel = " · Sorted: Price Low to High";
    else if (sortBy === "price-desc") sortLabel = " · Sorted: Price High to Low";
    else if (sortBy === "name-asc") sortLabel = " · Sorted: Name A to Z";

    let catLabel = selectedCategory ? ` in "${selectedCategory}"` : "";
    
    if (matchCount === 0) {
      countIndicator.textContent = "No items match your criteria.";
    } else {
      countIndicator.textContent = `Showing ${matchCount} of ${catalogSearchIndex.length} items${catLabel}${sortLabel}`;
    }
  }

  // DOM Virtualization logic
  currentMatchingEntries = matchingEntries;
  renderBatchIndex = 0;
  
  // Detach all existing cards efficiently instead of empty loop
  grid.replaceChildren();

  if (matchCount === 0) {
    const emptyState = document.createElement("div");
    emptyState.className = "catalog-empty-state";
    emptyState.innerHTML = `
      <h2 style="font-size: 20px; margin-bottom: 15px;">No items match your criteria.</h2>
      <p style="color: #64748b; margin-bottom: 20px;">Try adjusting your search or filter.</p>
      <button class="mode-toggle-btn mode-toggle-customer" onclick="resetAllFilters()" style="display:inline-flex;">Browse All Inventory</button>
    `;
    grid.appendChild(emptyState);
    return;
  }

  renderNextBatch();
  setupGridObserver();
}

function resetAllFilters() {
  const searchInputEl = document.getElementById("searchInput");
  if(searchInputEl) searchInputEl.value = "";
  const categoryFilter = document.getElementById("categoryFilter");
  if(categoryFilter) categoryFilter.value = "";
  const sortBySelect = document.getElementById("sortBy");
  if(sortBySelect) sortBySelect.value = "default";
  filterCatalog();
}

function renderNextBatch() {
  const grid = document.getElementById("catalogGrid");
  if (!grid) return;
  const fragment = document.createDocumentFragment();
  const end = Math.min(renderBatchIndex + BATCH_SIZE, currentMatchingEntries.length);
  for (let i = renderBatchIndex; i < end; i++) {
    const entry = currentMatchingEntries[i];
    if (!entry.card) {
      entry.card = createCard(entry.item);
    }
    entry.card.style.display = "flex";
    fragment.appendChild(entry.card);
  }
  grid.appendChild(fragment);
  renderBatchIndex = end;
}

function setupGridObserver() {
  if (gridObserver) return;
  const grid = document.getElementById("catalogGrid");
  if (!grid) return;
  
  const sentinel = document.createElement('div');
  sentinel.id = "gridBottomSentinel";
  sentinel.style.height = "1px";
  grid.parentNode.appendChild(sentinel);

  gridObserver = new IntersectionObserver((entries) => {
    if (entries[0].isIntersecting && renderBatchIndex < currentMatchingEntries.length) {
      renderNextBatch();
    }
  }, { rootMargin: '200px' });
  gridObserver.observe(sentinel);
}
function readProduct(sr_number, qty, discountPct) {
  const row = rawCatalog.find(
    (item) => String(item.sr_number) === String(sr_number),
  );
  if (!row) throw new Error("Product not found: " + sr_number);

  const priceText = row.list_price
    ? String(row.list_price).trim().replace(/,/g, "")
    : "";
  const parsedPrice = priceText ? Number(priceText) : null;

  return {
    sr_number: String(row.sr_number),
    name: row.item_name || "",
    price: parsedPrice,
    qty,
    hsn: row.hsn_code || "",
    size: row.size || "",
    idSize: row.id_size || "",
    odSize: row.od_size || "",
    lfSize: row.lf_size || "",
    unit: row.unit || "",
    packing: row.packing || "",
    discountPct: parsedPrice === null ? 0 : discountPct,
    discountOpen: false,
  };
}

function addToCart(sr_number, explicitQty) {
  const qtyInput = document.getElementById("qty-" + sr_number);
  let qty;
  if (
    typeof explicitQty === "number" &&
    Number.isInteger(explicitQty) &&
    explicitQty > 0
  ) {
    qty = explicitQty;
  } else if (
    qtyInput &&
    Number.isInteger(Number(qtyInput.value)) &&
    Number(qtyInput.value) > 0
  ) {
    qty = Number(qtyInput.value);
  } else {
    qty = 1;
  }
  const existingQty = cart[sr_number] ? cart[sr_number].qty : 0;

  if (
    !Number.isInteger(qty) ||
    qty <= 0 ||
    existingQty + qty > CommerceCore.MAX_QUANTITY
  ) {
    showToast("Enter a whole-number quantity from 1 to 9,999.");
    return;
  }

  if (cart[sr_number]) {
    cart[sr_number].qty += qty;
  } else {
    const item = readProduct(sr_number, qty, 0);
    if (
      item.price !== null &&
      (!Number.isFinite(item.price) || item.price < 0)
    ) {
      showToast(
        "This catalog item has an invalid price. Please contact sales.",
      );
      return;
    }
    cart[sr_number] = item;
  }

  if (qtyInput) {
    qtyInput.value = 1; // reset
  }
  renderCart();
  showToast(
    (cart[sr_number].price === null
      ? "Added quote request for "
      : "Added " + qty + " × ") + cart[sr_number].name,
  );

  // Auto open cart briefly if it's the first item
  if (
    Object.keys(cart).length === 1 &&
    !document.getElementById("cartDropdown").classList.contains("open")
  ) {
    toggleCart();
  }
}

function updateItemQty(sr_number, change) {
  if (!cart[sr_number]) return;
  cart[sr_number].qty += change;
  if (cart[sr_number].qty <= 0) {
    delete cart[sr_number];
  } else if (cart[sr_number].qty > CommerceCore.MAX_QUANTITY) {
    cart[sr_number].qty = CommerceCore.MAX_QUANTITY;
    showToast("Maximum quantity is 9,999 per item.");
  }
  renderCart();
}

function updateItemDiscount(sr_number, value) {
  const discountPct = Number(value);
  if (!Number.isFinite(discountPct) || discountPct < 0 || discountPct > 100) {
    showToast("Item discount must be between 0% and 100%.");
    renderCart();
    return;
  }
  if (!cart[sr_number]) return;
  if (cart[sr_number].price === null) {
    showToast("Discounts can be set after sales confirms the price.");
    return;
  }
  cart[sr_number].discountPct = discountPct;
  renderCart();
}

function roundCurrency(amount) {
  return CommerceCore.roundCurrency(amount);
}

function getLineAmounts(item) {
  return CommerceCore.calculateLineAmounts(item);
}

function formatAmount(amount) {
  return amount.toLocaleString("en-IN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function formatRate(rate) {
  return formatAmount(rate).replace(/\.?0+$/, "");
}

function getTaxRates() {
  const isEstimate = document.getElementById("isEstimateToggle")?.checked;
  if (isEstimate) return { cgstRate: 0, sgstRate: 0 };

  const cgstInput = document.getElementById("cgstRate");
  const sgstInput = document.getElementById("sgstRate");
  if (!cgstInput.checkValidity() || !sgstInput.checkValidity()) return null;

  return {
    cgstRate: cgstInput.valueAsNumber,
    sgstRate: sgstInput.valueAsNumber,
  };
}

function getTaxBreakdown(subTotal, rates = getTaxRates()) {
  if (!rates) return null;
  const totals = CommerceCore.calculateTotals(
    Object.keys(cart).map((key) => cart[key]),
    rates,
  );
  return {
    ...totals,
    totalAmount: totals.totalTax,
  };
}

function displayTaxBreakdown(tax, subTotal) {
  document.getElementById("cgstAmount").innerText = tax
    ? formatAmount(tax.cgstAmount)
    : "—";
  document.getElementById("sgstAmount").innerText = tax
    ? formatAmount(tax.sgstAmount)
    : "—";
  document.getElementById("totalTaxRate").innerText = tax
    ? formatRate(tax.totalRate)
    : "—";
  document.getElementById("taxAmount").innerText = tax
    ? formatAmount(tax.totalAmount)
    : "—";
  document.getElementById("grandTotal").innerText = tax
    ? formatAmount(tax.estimatedTotal)
    : "—";
  document.getElementById("quoteItemsNote").hidden =
    !tax || !tax.includesUnpricedItems;
}

function saveCart() {
  const snapshot = { version: 1, items: Object.create(null) };
  Object.keys(cart).forEach((sku) => {
    snapshot.items[sku] = {
      qty: cart[sku].qty,
      discountPct: cart[sku].discountPct,
    };
  });
  const rates = getTaxRates();
  if (rates) snapshot.rates = rates;
  try {
    localStorage.setItem(CART_STORAGE_KEY, JSON.stringify(snapshot));
  } catch (error) {
    console.error("Unable to save the catalog cart in this browser.", error);
    showToast("Cart saved for this page only; browser storage is unavailable.");
  }
}

function restoreCart() {
  let raw;
  try {
    raw = localStorage.getItem(CART_STORAGE_KEY);
  } catch (error) {
    console.error("Unable to read the saved catalog cart.", error);
    showToast(
      "Browser storage is unavailable; this cart will not persist after refresh.",
    );
    return;
  }
  if (!raw) return;

  try {
    const validSkus = Object.create(null);
    rawCatalog.forEach((item) => {
      validSkus[String(item.sr_number)] = true;
    });
    const restored = CommerceCore.sanitizeCartSnapshot(
      JSON.parse(raw),
      validSkus,
    );
    Object.keys(restored.items).forEach((sku) => {
      cart[sku] = readProduct(
        sku,
        restored.items[sku].qty,
        restored.items[sku].discountPct,
      );
    });
    document.getElementById("cgstRate").value = restored.rates.cgstRate;
    document.getElementById("sgstRate").value = restored.rates.sgstRate;
    if (restored.discardedItems) {
      showToast(
        "Unavailable or invalid saved items were removed from the cart.",
      );
    }
  } catch (error) {
    console.error("Unable to restore the saved catalog cart.", error);
    try {
      localStorage.removeItem(CART_STORAGE_KEY);
    } catch (storageError) {
      console.error(
        "Unable to clear the invalid saved catalog cart.",
        storageError,
      );
    }
    showToast("The saved cart was invalid and has been cleared.");
  }
}

function renderCart() {
  const cartItemsDiv = document.getElementById("cartItems");
  cartItemsDiv.replaceChildren();
  let itemsSubtotal = 0;
  let discountTotal = 0;
  let subTotal = 0;
  let totalItems = 0;

  const keys = Object.keys(cart);
  document.getElementById("orderSummaryCount").textContent =
    `${keys.length} item${keys.length === 1 ? "" : "s"}`;
  if (keys.length === 0) {
    const emptyState = document.createElement("div");
    emptyState.className = "cart-empty";
    const title = document.createElement("strong");
    title.textContent = "Your cart is empty";
    emptyState.append(
      title,
      document.createTextNode("Add products from the catalog to begin."),
    );
    cartItemsDiv.appendChild(emptyState);
  } else {
    keys.forEach((k) => {
      const item = cart[k];
      const amounts = getLineAmounts(item);
      itemsSubtotal += amounts.gross;
      discountTotal += amounts.discount;
      subTotal += amounts.net;
      totalItems += item.qty;

      const row = document.createElement("div");
      row.className = "cart-item";
      const details = document.createElement("div");
      const title = document.createElement("div");
      title.className = "cart-item-title";
      title.textContent = item.name;
      const meta = document.createElement("div");
      meta.className = "cart-item-meta";
      meta.textContent = [
        item.size && `Size: ${item.size}`,
        item.idSize && `ID Size: ${item.idSize}`,
        item.odSize && `OD Size: ${item.odSize}`,
        item.lfSize && `L/F Size: ${item.lfSize}`,
        item.unit && `Unit: ${item.unit}`,
        item.packing && `Pack: ${item.packing}`,
      ]
        .filter(Boolean)
        .join(" · ");
      let rate = document.createElement("div");
      rate.className = "cart-item-rate";
      if (item.price === null) {
        rate.classList.add("quote-edit-container");
        rate.style.display = "flex";
        rate.style.alignItems = "center";
        rate.style.gap = "8px";
        rate.innerHTML =
          '<label style="font-size: 0.8em; margin-right: 4px;">Quote Rate (\u20B9): </label><input type="number" class="quote-price-input" min="0" step="0.01" placeholder="Enter rate" style="width: 80px; padding: 2px;">';
        const input = rate.querySelector("input");
        if (item.customPrice !== undefined) {
          input.value = item.customPrice;
        }
        input.addEventListener("change", (e) => {
          const val = parseFloat(e.target.value);
          if (!isNaN(val) && val >= 0) {
            item.customPrice = val;
          } else {
            delete item.customPrice;
          }
          saveCart();
          renderCart();
        });
      } else {
        rate.textContent = `Unit price \u2022 \u20B9${formatAmount(item.price)}`;
      }
      const controls = document.createElement("div");
      controls.className = "cart-qty-controls";
      const decrease = document.createElement("button");
      decrease.className = "qty-btn";
      decrease.type = "button";
      decrease.setAttribute("aria-label", `Decrease quantity of ${item.name}`);
      decrease.textContent = "−";
      decrease.addEventListener("click", () => updateItemQty(k, -1));
      const quantity = document.createElement("span");
      quantity.className = "qty-value";
      quantity.textContent = item.qty;
      const increase = document.createElement("button");
      increase.className = "qty-btn";
      increase.type = "button";
      increase.setAttribute("aria-label", `Increase quantity of ${item.name}`);
      increase.textContent = "+";
      increase.addEventListener("click", () => updateItemQty(k, 1));
      controls.append(decrease, quantity, increase);
      details.append(title);
      if (meta.textContent) details.append(meta);
      details.append(rate, controls);
      if (item.price !== null) {
        const discountDetails = document.createElement("details");
        discountDetails.className = "cart-item-discount";
        discountDetails.open = item.discountOpen;
        discountDetails.addEventListener("toggle", () => {
          item.discountOpen = discountDetails.open;
        });
        const discountSummary = document.createElement("summary");
        discountSummary.textContent =
          item.discountPct > 0
            ? `Item discount · ${item.discountPct}%`
            : "Add item discount";
        const discountControls = document.createElement("div");
        discountControls.className = "discount-controls";
        const discountInput = document.createElement("input");
        discountInput.className = "discount-input";
        discountInput.type = "number";
        discountInput.min = "0";
        discountInput.max = "100";
        discountInput.step = "0.01";
        discountInput.value = item.discountPct;
        discountInput.setAttribute(
          "aria-label",
          `Discount percentage for ${item.name}`,
        );
        discountInput.addEventListener("change", () =>
          updateItemDiscount(k, discountInput.value),
        );
        const percentLabel = document.createElement("span");
        percentLabel.textContent = "% off";
        discountControls.append(discountInput, percentLabel);
        discountDetails.append(discountSummary, discountControls);
        details.append(discountDetails);
      } else {
        const quoteNote = document.createElement("div");
        quoteNote.className = "cart-item-rate";
        quoteNote.textContent = "Discount available after price confirmation.";
        details.append(quoteNote);
      }
      const itemTotal = document.createElement("div");
      itemTotal.className = "cart-item-total";
      if (amounts.isQuoted) {
        itemTotal.classList.add("quote-total");
        itemTotal.textContent = "Quote required";
      } else {
        itemTotal.textContent = `₹${formatAmount(amounts.net)}`;
      }
      if (amounts.discount > 0) {
        const discountNote = document.createElement("span");
        discountNote.className = "cart-item-discount-value";
        discountNote.textContent = `−₹${formatAmount(amounts.discount)}`;
        itemTotal.appendChild(discountNote);
      }
      row.append(details, itemTotal);
      cartItemsDiv.appendChild(row);
    });
  }

  itemsSubtotal = roundCurrency(itemsSubtotal);
  discountTotal = roundCurrency(discountTotal);
  subTotal = roundCurrency(subTotal);
  document.getElementById("cartCountBadge").innerText = totalItems;

  const itemsSubtotalEl = document.getElementById("itemsSubtotal");
  if (itemsSubtotalEl) itemsSubtotalEl.innerText = formatAmount(itemsSubtotal);
  const itemsSubtotalSummaryEl = document.getElementById(
    "itemsSubtotalSummary",
  );
  if (itemsSubtotalSummaryEl)
    itemsSubtotalSummaryEl.innerText = formatAmount(itemsSubtotal);
  document.getElementById("discountTotal").innerText =
    formatAmount(discountTotal);
  document.getElementById("subTotal").innerText = formatAmount(subTotal);
  displayTaxBreakdown(getTaxBreakdown(subTotal), subTotal);
  const pob = document.getElementById("placeOrderButton");
  if (pob) pob.disabled = keys.length === 0;
  saveCart();
}

function createOrderReference() {
  const now = new Date();
  const date = [
    now.getFullYear(),
    String(now.getMonth() + 1).padStart(2, "0"),
    String(now.getDate()).padStart(2, "0"),
  ].join("");
  const suffix = Math.floor(Math.random() * 1000000)
    .toString()
    .padStart(6, "0");
  return `SK-${date}-${suffix}`;
}

function readBuyerDetails() {
  return {
    name: document.getElementById("buyerName").value,
    phone: document.getElementById("buyerPhone").value,
    email: document.getElementById("buyerEmail").value,
    address: document.getElementById("buyerAddress").value,
    state: document.getElementById("buyerState").value,
    pincode: document.getElementById("buyerPincode").value,
    gstin: document.getElementById("buyerGstin").value,
    deliveryInstructions:
      (document.getElementById("deliveryInstructions") || {}).value || "",
    transportPreference:
      (document.getElementById("transportPreference") || {}).value || "",
  };
}


function standaloneBillHtml() {
  const stylesheet = Array.from(document.styleSheets).find(
    (sheet) => sheet.href && sheet.href.includes("search_catalog.css"),
  );
  if (!stylesheet)
    throw new Error(
      "The invoice stylesheet is unavailable; the bill was not archived.",
    );

  let css;
  try {
    css = Array.from(stylesheet.cssRules, (rule) => rule.cssText).join("\n");
  } catch (error) {
    throw new Error(
      "The invoice styling could not be embedded for the saved bill.",
    );
  }
  const reference = document.getElementById("pInvNo").innerText.trim();
  const safeTitle = reference.replace(
    /[<>&"']/g,
    (character) =>
      ({
        "<": "&lt;",
        ">": "&gt;",
        "&": "&amp;",
        '"': "&quot;",
        "'": "&#39;",
      })[character],
  );
  const screenStyles = `
            @media screen {
                body { min-height: 100vh; margin: 0; padding: 18px; box-sizing: border-box; background: #f5f7fa; }
                #printBill { display: block !important; position: static; inset: auto; width: min(100%, 1000px); margin: 18px auto; padding: 24px; box-sizing: border-box; background: #fff; box-shadow: 0 8px 28px rgba(15,23,42,.12); }
                #printBill * { box-sizing: border-box; }
                .inv-topline { height: 5px; margin-bottom: 18px; background: #173b57; }
                .inv-header { display: flex; justify-content: space-between; gap: 20px; padding-bottom: 16px; margin-bottom: 18px; border-bottom: 1px solid #cbd5e1; }
                .inv-brand { min-width: 0; }
                .inv-brand h1 { margin: 0 0 5px; color: #173b57; font-size: 24px; }
                .inv-brand p { margin: 3px 0; color: #486581; font-size: 12px; line-height: 1.45; }
                .inv-brand .legal-name { font-size: 11px; font-weight: 700; letter-spacing: .08em; }
                .inv-brand .inv-contact { font-size: 10px; }
                .inv-title { flex: 0 0 auto; min-width: 150px; text-align: right; }
                .inv-title h2 { margin: 0 0 7px; color: #173b57; font-size: 21px; }
                .inv-title span, .inv-fact span:first-child { color: #627d98; }
                .inv-meta { display: grid; grid-template-columns: 1.4fr 1fr; gap: 14px; margin-bottom: 20px; }
                .inv-card { padding: 12px; background: #f4f7fa; border: 1px solid #d9e2ec; border-radius: 4px; }
                .inv-card-label { margin-bottom: 8px; color: #627d98; font-size: 11px; font-weight: 700; text-transform: uppercase; }
                .inv-buyer { margin-bottom: 4px; color: #172b4d; font-weight: 700; }
                .inv-buyer-detail { color: #486581; font-size: 12px; line-height: 1.5; white-space: pre-line; overflow-wrap: anywhere; }
                .inv-facts { display: grid; gap: 9px; }
                .inv-fact { display: flex; justify-content: space-between; gap: 14px; font-size: 12px; }
                table.inv-table, .inv-summary table { width: 100%; border-collapse: collapse; }
                .inv-table th, .inv-table td { padding: 7px 5px; border-bottom: 1px solid #d9e2ec; font-size: 11px; text-align: left; }
                .inv-table th { background: #173b57; color: #fff; }
                .inv-table td.num, .inv-table th.num, .inv-summary td.num { text-align: right; white-space: nowrap; }
                .inv-summary { width: min(360px, 100%); margin: 18px 0 0 auto; }
                .inv-summary td { padding: 7px 8px; border-bottom: 1px solid #e2e8f0; font-size: 12px; }
                .inv-summary .total td { padding-top: 11px; border-top: 2px solid #173b57; color: #173b57; font-size: 15px; font-weight: 700; }
                .inv-notes { margin-top: 24px; padding-top: 12px; border-top: 1px solid #d9e2ec; color: #627d98; font-size: 11px; line-height: 1.5; }
                .inv-signoff { display: flex; justify-content: space-between; align-items: flex-end; gap: 16px; margin-top: 28px; color: #627d98; font-size: 11px; }
                .inv-signature { width: 190px; padding-top: 7px; border-top: 1px solid #829ab1; text-align: center; }
                .inv-footer { margin-top: 16px; color: #829ab1; font-size: 10px; text-align: center; }
            }
            @media screen and (max-width: 600px) {
                body { padding: 8px; }
                #printBill { margin: 0 auto; padding: 12px; overflow-x: auto; }
                .inv-header { flex-direction: column; gap: 12px; }
                .inv-title { text-align: left; }
                .inv-meta { grid-template-columns: 1fr; gap: 8px; }
                .inv-table { min-width: 700px; }
                .inv-signoff { align-items: flex-start; flex-direction: column; }
            }
        `;
  return `<!doctype html>
    <html lang="en">
    <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Proforma invoice ${safeTitle}</title>
    <style>${css.replace(/<\/style/gi, "<\\/style")}</style>
    <style>${screenStyles}</style>
    </head>
    <body>${document.getElementById("printBill").outerHTML}</body>
    </html>`;
}

function archiveCurrentBill(date) {
  const reference = document.getElementById("pInvNo").innerText.trim();
  const html = standaloneBillHtml();
        if (isLocalEnv) {
            const order = CommerceCore.createOrder({
                id: reference,
                createdAt: date.toISOString(),
                buyer: readBuyerDetails(),
                items: cart,
                totals: {
                    subTotal: getSubTotal(),
                    grandTotal: getSubTotal() + Object.values(getTaxBreakdown(getSubTotal())).reduce((a, b) => a + b, 0)
                }
            });
            order.html = html;
            order.isEstimate = document.getElementById("isEstimateToggle")?.checked || false;

            return fetch("/api/bills/add", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(order)
            }).then(r => r.json()).then(res => {
                if (res.success) {
                    return { storage: "server", entry: { fileName: res.added.id + ".html", month: res.added.createdAt.substring(0, 7) } };
                }
                return billArchive.saveBill({ date, reference, html });
            }).catch(() => billArchive.saveBill({ date, reference, html }));
        }


  return billArchive.saveBill({ date, reference, html }).then((result) => {
    if (typeof refreshSavedBills === "function") {
      refreshSavedBills().catch(() => {});
    }
    return result;
  });
}

async function saveBillRequest() {
  if (Object.keys(cart).length === 0) {
    alert("Cart is empty! Please add items before saving a bill.");
    return;
  }
  const taxRates = getTaxRates();
  if (!taxRates) {
    const invalidInput = [
      document.getElementById("cgstRate"),
      document.getElementById("sgstRate"),
    ].find((input) => !input.checkValidity());
    if (invalidInput) invalidInput.reportValidity();
    return;
  }
  const now = new Date();
  const reference = document.getElementById("pInvNo").innerText.trim() || "";

  const order = CommerceCore.createOrder({
    id: reference,
    createdAt: now.toISOString(),
    buyer: readBuyerDetails(),
    items: cart,
    totals: {
      subTotal: getSubTotal(),
      grandTotal:
        getSubTotal() +
        Object.values(getTaxBreakdown(getSubTotal())).reduce(
          (a, b) => a + b,
          0,
        ),
    },
  });

  // Static Pages / offline: prepare proforma and archive with File System Access / download
  generateBill({ printAfter: false });
}

function generateBill(options = {}) {
  const printAfter = options.printAfter !== false;
  if (Object.keys(cart).length === 0) {
    alert("Cart is empty! Please add items before printing a bill.");
    return;
  }

  const taxRates = getTaxRates();
  if (!taxRates) {
    const invalidInput = [
      document.getElementById("cgstRate"),
      document.getElementById("sgstRate"),
    ].find((input) => !input.checkValidity());
    invalidInput.reportValidity();
    return;
  }

  const buyer = readBuyerDetails();
  const bName = buyer.name.trim() || "Cash customer";
  document.getElementById("pBuyerName").innerText = bName;
  document.getElementById("pBuyerContact").innerText = [
    buyer.phone.trim(),
    buyer.email.trim(),
  ]
    .filter(Boolean)
    .join(" · ");
  document.getElementById("pBuyerAddress").innerText = [
    buyer.address.trim(),
    buyer.state,
    buyer.pincode,
  ]
    .filter(Boolean)
    .join(", ");
  document.getElementById("pBuyerGstin").innerText = buyer.gstin.trim()
    ? `Customer GSTIN: ${buyer.gstin.trim().toUpperCase()}`
    : "";

  const now = new Date();
  const dateStr = now.toLocaleDateString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
  document.getElementById("pDate").innerText = dateStr;
  const dateCode = [
    now.getFullYear(),
    String(now.getMonth() + 1).padStart(2, "0"),
    String(now.getDate()).padStart(2, "0"),
  ].join("");
  document.getElementById("pInvNo").innerText =
    `PI-${dateCode}-${String(Math.floor(Math.random() * 1000000)).padStart(6, "0")}`;

  const tbody = document.getElementById("pTableBody");
  tbody.replaceChildren();

  Object.keys(cart).forEach((k, index) => {
    const item = cart[k];
    const amounts = getLineAmounts(item);

    const row = document.createElement("tr");
    const serial = document.createElement("td");
    serial.textContent = index + 1;
    row.appendChild(serial);
    const particulars = document.createElement("td");
    particulars.textContent = item.name;
    const itemName = item.name.toLowerCase();
    const specifications = [];
    if (item.size && !itemName.includes(item.size.toLowerCase()))
      specifications.push(`Size: ${item.size}`);
    if (item.idSize) specifications.push(`ID Size: ${item.idSize}`);
    if (item.odSize) specifications.push(`OD Size: ${item.odSize}`);
    if (item.lfSize) specifications.push(`L/F Size: ${item.lfSize}`);
    if (item.packing && !itemName.includes(item.packing.toLowerCase()))
      specifications.push(`Pack: ${item.packing}`);
    if (specifications.length) {
      const detail = document.createElement("div");
      detail.className = "item-size";
      detail.textContent = specifications.join(" · ");
      particulars.appendChild(detail);
    }
    row.appendChild(particulars);
    const discountDisplay = amounts.isQuoted
      ? "Quote"
      : item.discountPct > 0
        ? `${formatAmount(item.discountPct)}% (₹${formatAmount(amounts.discount)})`
        : "—";
    const rateDisplay = amounts.isQuoted ? "Quote" : formatAmount(item.price);
    const amountDisplay = amounts.isQuoted
      ? "Quote"
      : formatAmount(amounts.net);
    [
      item.hsn || "—",
      item.qty,
      item.unit || "—",
      rateDisplay,
      discountDisplay,
      amountDisplay,
    ].forEach((value, column) => {
      const cell = document.createElement("td");
      cell.textContent = value;
      if ([1, 3, 4, 5].includes(column)) cell.className = "num";
      row.appendChild(cell);
    });
    tbody.appendChild(row);
  });

  const totals = CommerceCore.calculateTotals(
    Object.keys(cart).map((key) => cart[key]),
    taxRates,
  );

  document.getElementById("pItemsSubtotal").innerText = formatAmount(
    totals.itemsSubtotal,
  );
  document.getElementById("pDiscountTotal").innerText = formatAmount(
    totals.discountTotal,
  );
  document.getElementById("pSubTotal").innerText = formatAmount(
    totals.taxableSubtotal,
  );
  document.getElementById("pCgstRate").innerText = formatRate(totals.cgstRate);
  document.getElementById("pCgstAmount").innerText = formatAmount(
    totals.cgstAmount,
  );
  document.getElementById("pSgstRate").innerText = formatRate(totals.sgstRate);
  document.getElementById("pSgstAmount").innerText = formatAmount(
    totals.sgstAmount,
  );
  document.getElementById("pTaxRate").innerText = formatRate(totals.totalRate);
  document.getElementById("pTaxAmount").innerText = formatAmount(
    totals.totalTax,
  );
  document.getElementById("pGrandTotal").innerText = formatAmount(
    totals.estimatedTotal,
  );
  document.getElementById("pQuoteNote").hidden = !totals.includesUnpricedItems;

  const printBill = () => window.print();
  const finishWithoutPrint = () => {
    document.getElementById("printBillBtn").style.display = "block";
  };
  try {
    archiveCurrentBill(now)
      .then((result) => {
        const message =
          result.storage === "folder"
            ? `Saved ${result.entry.fileName} in generated_bills/${result.entry.month}/.`
            : result.storage === "browser"
              ? `Saved ${result.entry.fileName} in this browser and downloaded a copy.`
              : `Downloaded ${result.entry.fileName}; browser storage is unavailable.`;
        document.getElementById("billArchiveStatus").textContent = message;
        showToast(message);
        finishWithoutPrint();
        if (result.entry.archiveWarning) {
          document.getElementById("billArchiveStatus").textContent +=
            ` Archive detail: ${result.entry.archiveWarning}`;
        }
      })
      .catch((error) => {
        if (error.name === "AbortError") {
          document.getElementById("billArchiveStatus").textContent =
            "Bill save: Folder selection cancelled.";
          finishWithoutPrint();
          return;
        }
        console.error("The proforma invoice could not be archived.", error);
        const message = `Bill prepared but not saved: ${error.message || "archive error"}`;
        document.getElementById("billArchiveStatus").textContent = message;
        showToast(message);
        finishWithoutPrint();
      })
      .finally(() => {
        if (printAfter) printBill();
      });
  } catch (error) {
    console.error(
      "The proforma invoice could not be prepared for archiving.",
      error,
    );
    document.getElementById("billArchiveStatus").textContent =
      `Bill prepared but not saved: ${error.message || "archive error"}`;
    finishWithoutPrint();
    if (printAfter) printBill();
  }
}

initCatalogCacheAndPrefs();
initCategoryPicker();
initCartProductSearch();
restoreCart();
renderCart();

// Read initial URL params
const params = new URLSearchParams(window.location.search);
const initialQ = params.get("q");
const initialCat = params.get("category");
if (initialQ) {
  const searchInputEl = document.getElementById("searchInput");
  if (searchInputEl) searchInputEl.value = initialQ;
}
if (initialCat) {
  const categoryFilter = document.getElementById("categoryFilter");
  if (categoryFilter) {
    const hasOption = Array.from(categoryFilter.options).some(opt => opt.value === initialCat);
    if (hasOption) categoryFilter.value = initialCat;
  }
}
filterCatalog();
// Lightbox logic
// Lightbox logic
function setupLightboxListeners() {
  const dialog = document.getElementById("imageLightbox");
  if (!dialog) return;

  dialog.addEventListener("click", (e) => {
    if (e.target === dialog) dialog.close();
  });

  document.getElementById("lightboxQtyMinus")?.addEventListener("click", () => {
    const qtyInput = document.getElementById("lightboxQty");
    if (qtyInput) {
      const val = Math.max(1, (parseInt(qtyInput.value, 10) || 1) - 1);
      qtyInput.value = val;
    }
  });

  document.getElementById("lightboxQtyPlus")?.addEventListener("click", () => {
    const qtyInput = document.getElementById("lightboxQty");
    if (qtyInput) {
      const val = Math.min(9999, (parseInt(qtyInput.value, 10) || 1) + 1);
      qtyInput.value = val;
    }
  });
}
setupLightboxListeners();

function openLightbox(srNumber) {
  const entry = catalogSearchIndex.find((e) => e.item.sr_number === srNumber);
  if (!entry) return;
  const item = entry.item;

  const dialog = document.getElementById("imageLightbox");
  if (!dialog) return;

  // Badges in header
  const catBadge = document.getElementById("lightboxCategory");
  if (catBadge) {
    catBadge.textContent = item.category || "General";
  }
  const srBadge = document.getElementById("lightboxSrNumber");
  if (srBadge) {
    srBadge.textContent = `Sr: ${item.sr_number}`;
  }
  const pageBadge = document.getElementById("lightboxPage");
  if (pageBadge) {
    if (item.page) {
      pageBadge.style.display = "inline-flex";
      pageBadge.textContent = `📖 Page ${item.page}`;
    } else {
      pageBadge.style.display = "none";
    }
  }

  // Image & representative notice
  const imgWrap = document.getElementById("lightboxImgWrap");
  const imgEl = document.getElementById("lightboxImg");
  const repNotice = document.getElementById("lightboxRepNotice");
  if (item.display_image_path) {
    if (imgWrap) imgWrap.style.display = "flex";
    if (imgEl) {
      imgEl.src = item.display_image_path;
      imgEl.alt = item.item_name || "Product image";
    }
    if (repNotice) {
      repNotice.style.display = item.image_is_representative ? "block" : "none";
    }
  } else {
    if (imgWrap) imgWrap.style.display = "none";
  }

  // Title, Price & Unit
  document.getElementById("lightboxTitle").textContent = item.item_name;
  const priceEl = document.getElementById("lightboxPrice");
  const unitEl = document.getElementById("lightboxUnit");
  if (item.list_price) {
    priceEl.textContent = `₹${item.list_price}`;
    unitEl.textContent = item.unit ? `Per ${item.unit}` : "";
  } else {
    priceEl.textContent = "Price on request";
    unitEl.textContent = "Contact sales for pricing";
  }

  // Comprehensive Specifications Table
  const specsBody = document.getElementById("lightboxSpecsBody");
  if (specsBody) {
    specsBody.replaceChildren();

    const rows = [
      { label: "Serial Number", value: item.sr_number },
      { label: "Category", value: item.category },
      { label: "Product Name", value: item.item_name },
      { label: "HSN Code", value: item.hsn_code },
      {
        label: "List Price",
        value: item.list_price ? `₹${item.list_price}` : "Price on request",
      },
      { label: "Unit", value: item.unit },
      { label: "Size", value: item.size },
      { label: "Inner Diameter (ID)", value: item.id_size },
      { label: "Outer Diameter (OD)", value: item.od_size },
      { label: "Length / Flat (L/F)", value: item.lf_size },
      { label: "Packaging", value: item.packing },
      { label: "Catalog Page", value: item.page ? `Page ${item.page}` : "" },
      { label: "Image Reference", value: item.image_ref },
    ];

    rows.forEach((r) => {
      if (r.value && String(r.value).trim()) {
        const tr = document.createElement("tr");
        const th = document.createElement("th");
        th.textContent = r.label;
        const td = document.createElement("td");
        td.textContent = r.value;
        tr.append(th, td);
        specsBody.appendChild(tr);
      }
    });
  }

  // Synchronize Quantity
  const cardQty = document.getElementById("qty-" + srNumber);
  const qtyInput = document.getElementById("lightboxQty");
  if (qtyInput) {
    qtyInput.value = cardQty ? cardQty.value || 1 : 1;
  }

  // Add to Cart Button
  const addBtn = document.getElementById("lightboxAddBtn");
  if (addBtn) {
    addBtn.textContent = item.list_price ? "🛒 Add to Cart" : "📝 Add to Quote";
    addBtn.onclick = () => {
      const qtyVal = parseInt(qtyInput ? qtyInput.value : 1, 10) || 1;
      if (cardQty) {
        cardQty.value = qtyVal;
      }
      addToCart(String(srNumber), qtyVal);
      dialog.close();
    };
  }

  if (typeof dialog.showModal === "function") {
    dialog.showModal();
  } else {
    dialog.setAttribute("open", "");
  }
}

function clearCartAndNewBill() {
  if (Object.keys(cart).length > 0 && !confirm("Are you sure you want to clear the cart and start a new bill?")) {
    return;
  }
  
  cart = {};
  
  const discountInputs = document.querySelectorAll('.cart-item-discount-input');
  discountInputs.forEach(input => input.value = 0);
  
  clearCustomerDetails();
  
  renderCart();
  
  const printBtn = document.getElementById("printBillBtn");
  if (printBtn) {
    printBtn.style.display = "none";
  }
  
  showToast("Cart cleared. Ready for a new bill.");
}
function toggleEstimateMode(checkbox) {
    renderCart();
    
    // Also update UI to indicate it's an estimate
    const title = document.querySelector(".cart-subtitle");
    if(title) {
        title.innerHTML = checkbox.checked ? "<strong>ESTIMATE / CHALLAN MODE</strong> - Taxes disabled" : "Review items, enter customer details, or print a proforma bill";
    }
}
