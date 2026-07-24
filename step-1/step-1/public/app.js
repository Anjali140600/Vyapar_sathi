const API = "";

const form = document.getElementById("txForm");
const formMessage = document.getElementById("formMessage");
const submitBtn = document.getElementById("submitBtn");
const txBody = document.getElementById("txBody");
const refreshBtn = document.getElementById("refreshBtn");
const dbStatus = document.getElementById("dbStatus");
const typeReceived = document.getElementById("transactionTypeReceived");
const typeSpent = document.getElementById("transactionTypeSpent");
const receivedBlock = document.getElementById("receivedBlock");
const spentBlock = document.getElementById("spentBlock");

function formatMoney(n) {
  if (n === null || n === undefined) return "—";
  const num = Number(n);
  if (Number.isNaN(num)) return "—";
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 2,
  }).format(num);
}

function formatQty(n) {
  if (n === null || n === undefined) return "—";
  const num = Number(n);
  if (Number.isNaN(num)) return "—";
  return new Intl.NumberFormat("en-IN", { maximumFractionDigits: 3 }).format(num);
}

function formatDate(iso) {
  if (!iso) return "—";
  const s = String(iso);
  // API may return "YYYY-MM-DD" or a full ISO string from MySQL/JSON — parse both
  const d = new Date(s.length === 10 ? `${s}T00:00:00` : s);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleDateString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

function fillSelect(selectEl, items) {
  selectEl.innerHTML = "";
  for (const t of items) {
    const opt = document.createElement("option");
    opt.value = t.value;
    opt.textContent = t.label;
    selectEl.appendChild(opt);
  }
}

function updateDirectionUI() {
  const dir = form.querySelector('input[name="money_direction"]:checked')?.value;
  const isReceived = dir === "received";

  receivedBlock.classList.toggle("is-hidden", !isReceived);
  receivedBlock.setAttribute("aria-hidden", String(!isReceived));
  typeReceived.disabled = !isReceived;
  typeReceived.tabIndex = isReceived ? 0 : -1;

  spentBlock.classList.toggle("is-hidden", isReceived);
  spentBlock.setAttribute("aria-hidden", String(isReceived));
  typeSpent.disabled = isReceived;
  typeSpent.tabIndex = isReceived ? -1 : 0;
}

function getSelectedTransactionType() {
  const dir = form.querySelector('input[name="money_direction"]:checked')?.value;
  if (dir === "spent") return typeSpent.value;
  return typeReceived.value;
}

async function loadTransactionTypes() {
  const r = await fetch(`${API}/api/transaction-types`);
  const j = await r.json();
  if (!r.ok) throw new Error(j.error || "Failed to load types");
  const types = j.types || [];
  const ins = types.filter((t) => t.flow === "in");
  const outs = types.filter((t) => t.flow === "out");

  fillSelect(typeReceived, ins);
  fillSelect(typeSpent, outs);
  updateDirectionUI();
}

function setDefaultDate() {
  form.querySelector('[name="transaction_date"]').value = new Date().toISOString().slice(0, 10);
}

function resetFormAfterSave() {
  form.reset();
  setDefaultDate();
  const firstDir = form.querySelector('input[name="money_direction"][value="received"]');
  if (firstDir) firstDir.checked = true;
  updateDirectionUI();
}

form.querySelectorAll('input[name="money_direction"]').forEach((el) => {
  el.addEventListener("change", updateDirectionUI);
});

async function checkHealth() {
  dbStatus.textContent = "Checking database…";
  dbStatus.className = "db-status";
  try {
    const r = await fetch(`${API}/api/health`);
    const j = await r.json();
    if (j.ok) {
      dbStatus.textContent = "MySQL connected";
      dbStatus.classList.add("ok");
    } else {
      dbStatus.textContent = "Database issue";
      dbStatus.classList.add("err");
    }
  } catch {
    dbStatus.textContent = "Cannot reach server";
    dbStatus.classList.add("err");
  }
}

async function loadTransactions() {
  txBody.innerHTML = `<tr><td colspan="7" class="empty">Loading…</td></tr>`;
  try {
    const r = await fetch(`${API}/api/transactions?limit=50`);
    const j = await r.json();
    if (!r.ok) throw new Error(j.error || "Failed to load");
    const rows = j.data || [];
    if (rows.length === 0) {
      txBody.innerHTML = `<tr><td colspan="7" class="empty">No transactions yet. Add one above.</td></tr>`;
      return;
    }
    txBody.innerHTML = rows
      .map((t) => {
        const flow = t.flow || (t.transaction_type === "income" ? "in" : "out");
        const pillClass = flow === "in" ? "inflow" : "outflow";
        const typeLabel = escapeHtml(t.transaction_type_label || t.transaction_type);
        const note = t.description ? escapeHtml(t.description) : "—";
        return `<tr>
          <td>${formatDate(t.transaction_date)}</td>
          <td><span class="type-pill ${pillClass}" title="${typeLabel}">${typeLabel}</span></td>
          <td>${escapeHtml(t.category)}</td>
          <td class="num">${formatQty(t.quantity)}</td>
          <td class="num">${formatMoney(t.amount)}</td>
          <td class="num">${t.gst_amount != null ? formatMoney(t.gst_amount) : "—"}</td>
          <td>${note}</td>
        </tr>`;
      })
      .join("");
  } catch (e) {
    txBody.innerHTML = `<tr><td colspan="7" class="empty error">${escapeHtml(
      e.message || "Error loading list"
    )}</td></tr>`;
  }
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  formMessage.textContent = "";
  formMessage.className = "message";

  const fd = new FormData(form);
  const payload = {
    transaction_date: fd.get("transaction_date"),
    transaction_type: getSelectedTransactionType(),
    quantity: fd.get("quantity") || "",
    amount: fd.get("amount"),
    gst_amount: fd.get("gst_amount") || "",
    category: fd.get("category"),
    description: fd.get("description") || "",
  };

  submitBtn.disabled = true;
  try {
    const r = await fetch(`${API}/api/transactions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const j = await r.json();
    if (!r.ok) {
      const msg = [j.error, j.detail].filter(Boolean).join(" — ");
      formMessage.textContent = msg || "Could not save";
      formMessage.classList.add("error");
      return;
    }
    formMessage.textContent = "Saved successfully.";
    formMessage.classList.add("success");
    resetFormAfterSave();
    await loadTransactionTypes();
    await loadTransactions();
  } catch (err) {
    formMessage.textContent = err.message || "Network error";
    formMessage.classList.add("error");
  } finally {
    submitBtn.disabled = false;
  }
});

refreshBtn.addEventListener("click", () => loadTransactions());

(async function init() {
  try {
    await loadTransactionTypes();
  } catch (e) {
    typeReceived.innerHTML = "<option>Failed to load</option>";
    typeSpent.innerHTML = "<option>Failed to load</option>";
    formMessage.textContent = e.message || "Could not load transaction types";
    formMessage.classList.add("error");
  }
  setDefaultDate();
  updateDirectionUI();
  checkHealth();
  loadTransactions();
})();
