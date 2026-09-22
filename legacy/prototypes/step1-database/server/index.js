require("dotenv").config();
const path = require("path");
const express = require("express");
const cors = require("cors");
const mysql = require("mysql2/promise");
const {
  TRANSACTION_TYPES,
  ALLOWED,
  LABEL_BY_VALUE,
  isAllowed,
  normalizeLegacyType,
} = require("./transactionTypes");

const PORT = Number(process.env.PORT) || 3000;

const pool = mysql.createPool({
  host: process.env.MYSQL_HOST || "127.0.0.1",
  port: Number(process.env.MYSQL_PORT) || 3306,
  user: process.env.MYSQL_USER || "root",
  password: process.env.MYSQL_PASSWORD ?? "",
  database: process.env.MYSQL_DATABASE || "vyapar_sathi",
  waitForConnections: true,
  connectionLimit: 10,
  namedPlaceholders: true,
});

const app = express();
app.use(cors());
app.use(express.json({ limit: "1mb" }));
app.use(express.static(path.join(__dirname, "..", "public")));

function parseAmount(value) {
  if (value === undefined || value === null || value === "") return null;
  const n = Number(String(value).replace(/,/g, "").trim());
  return Number.isFinite(n) ? n : null;
}

function parseQuantity(value) {
  if (value === undefined || value === null || value === "") return null;
  const n = Number(String(value).replace(/,/g, "").trim());
  if (!Number.isFinite(n) || n < 0) return null;
  return n;
}

function parseDate(value) {
  if (!value || typeof value !== "string") return null;
  const d = new Date(value + (value.length === 10 ? "T00:00:00" : ""));
  if (Number.isNaN(d.getTime())) return null;
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function enrichRow(row) {
  if (!row) return row;
  const code = normalizeLegacyType(row.transaction_type);
  return {
    ...row,
    transaction_type: code,
    transaction_type_label: LABEL_BY_VALUE[code] || String(code),
    flow: TRANSACTION_TYPES.find((t) => t.value === code)?.flow || null,
  };
}

app.get("/api/transaction-types", (_req, res) => {
  res.json({ types: TRANSACTION_TYPES });
});

app.get("/api/health", async (_req, res) => {
  try {
    await pool.query("SELECT 1 AS ok");
    res.json({ ok: true, db: "connected" });
  } catch (e) {
    res.status(503).json({ ok: false, error: "Database unavailable", detail: e.message });
  }
});

app.get("/api/transactions", async (req, res) => {
  const limit = Math.min(Math.max(Number(req.query.limit) || 100, 1), 500);
  const offset = Math.max(Number(req.query.offset) || 0, 0);
  try {
    const [rows] = await pool.query(
      `SELECT id, amount, quantity, gst_amount, transaction_date, category, transaction_type, description, created_at
       FROM transactions
       ORDER BY transaction_date DESC, id DESC
       LIMIT :limit OFFSET :offset`,
      { limit, offset }
    );
    const [[{ total }]] = await pool.query(`SELECT COUNT(*) AS total FROM transactions`);
    res.json({
      data: rows.map(enrichRow),
      total: Number(total),
    });
  } catch (e) {
    console.error(e);
    res.status(500).json({ error: "Failed to load transactions", detail: e.message });
  }
});

app.post("/api/transactions", async (req, res) => {
  const body = req.body || {};
  const amount = parseAmount(body.amount);
  const quantity =
    body.quantity === undefined || body.quantity === null || body.quantity === ""
      ? null
      : parseQuantity(body.quantity);
  const gstAmount =
    body.gst_amount === undefined || body.gst_amount === null || body.gst_amount === ""
      ? null
      : parseAmount(body.gst_amount);
  const transactionDate = parseDate(body.transaction_date);
  const category = typeof body.category === "string" ? body.category.trim() : "";
  const transactionType =
    typeof body.transaction_type === "string" ? body.transaction_type.trim() : "";

  const description =
    typeof body.description === "string" ? body.description.trim().slice(0, 512) : null;

  if (amount === null || amount < 0) {
    return res.status(400).json({ error: "Invalid or missing amount" });
  }
  if (!transactionDate) {
    return res.status(400).json({ error: "Invalid or missing transaction_date (YYYY-MM-DD)" });
  }
  if (!category) {
    return res.status(400).json({ error: "Category is required" });
  }
  if (!isAllowed(transactionType)) {
    return res.status(400).json({ error: "Invalid transaction type" });
  }
  if (gstAmount !== null && gstAmount < 0) {
    return res.status(400).json({ error: "gst_amount cannot be negative" });
  }
  if (
    body.quantity !== undefined &&
    body.quantity !== null &&
    body.quantity !== "" &&
    quantity === null
  ) {
    return res.status(400).json({ error: "Invalid quantity (use a non-negative number)" });
  }

  try {
    const [result] = await pool.query(
      `INSERT INTO transactions (amount, quantity, gst_amount, transaction_date, category, transaction_type, description)
       VALUES (:amount, :quantity, :gst_amount, :transaction_date, :category, :transaction_type, :description)`,
      {
        amount,
        quantity,
        gst_amount: gstAmount,
        transaction_date: transactionDate,
        category,
        transaction_type: transactionType,
        description: description || null,
      }
    );
    const [rows] = await pool.query(
      `SELECT id, amount, quantity, gst_amount, transaction_date, category, transaction_type, description, created_at
       FROM transactions WHERE id = :id`,
      { id: result.insertId }
    );
    res.status(201).json(enrichRow(rows[0]));
  } catch (e) {
    console.error(e);
    res.status(500).json({ error: "Failed to save transaction", detail: e.message });
  }
});

app.use((err, _req, res, _next) => {
  console.error(err);
  res.status(500).json({ error: "Server error" });
});

app.listen(PORT, () => {
  console.log(`Vyapar Sathi server http://localhost:${PORT}`);
});
