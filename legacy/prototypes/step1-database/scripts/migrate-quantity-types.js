/**
 * Migrates existing DBs: add quantity, widen transaction_type from ENUM to VARCHAR,
 * map legacy income/expense to new codes.
 */
require("dotenv").config();
const mysql = require("mysql2/promise");

const db = process.env.MYSQL_DATABASE || "vyapar_sathi";

async function columnExists(conn, table, column) {
  const [rows] = await conn.query(
    `SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
     WHERE TABLE_SCHEMA = :db AND TABLE_NAME = :table AND COLUMN_NAME = :col`,
    { db, table, col: column }
  );
  return rows.length > 0;
}

async function main() {
  const conn = await mysql.createConnection({
    host: process.env.MYSQL_HOST || "127.0.0.1",
    port: Number(process.env.MYSQL_PORT) || 3306,
    user: process.env.MYSQL_USER || "root",
    password: process.env.MYSQL_PASSWORD ?? "",
    database: db,
    multipleStatements: true,
    namedPlaceholders: true,
  });

  if (!(await columnExists(conn, "transactions", "quantity"))) {
    await conn.query(
      `ALTER TABLE transactions ADD COLUMN quantity DECIMAL(12, 3) NULL DEFAULT NULL
       COMMENT 'Units (optional)' AFTER amount`
    );
    console.log("Added column: quantity");
  } else {
    console.log("Column quantity already exists — skip");
  }

  const [colRows] = await conn.query(
    `SELECT COLUMN_TYPE AS t FROM INFORMATION_SCHEMA.COLUMNS
     WHERE TABLE_SCHEMA = :db AND TABLE_NAME = 'transactions' AND COLUMN_NAME = 'transaction_type'`,
    { db }
  );
  const colType = colRows[0]?.t || "";
  if (colType.toLowerCase().includes("enum")) {
    await conn.query(
      `ALTER TABLE transactions MODIFY COLUMN transaction_type VARCHAR(64) NOT NULL`
    );
    await conn.query(
      `UPDATE transactions SET transaction_type = 'payment_received' WHERE transaction_type = 'income'`
    );
    await conn.query(
      `UPDATE transactions SET transaction_type = 'other_expense' WHERE transaction_type = 'expense'`
    );
    console.log("Converted transaction_type from ENUM to VARCHAR and mapped legacy values");
  } else {
    console.log("transaction_type is not ENUM — skip enum migration");
  }

  await conn.end();
  console.log("OK: migration finished.");
}

main().catch((e) => {
  console.error("Migration failed:", e.message);
  process.exit(1);
});
