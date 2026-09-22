/**
 * Applies database/schema.sql using mysql2 (no mysql.exe required).
 * Requires: MySQL server running, credentials in .env (see .env.example).
 */
require("dotenv").config();
const fs = require("fs");
const path = require("path");
const mysql = require("mysql2/promise");

async function main() {
  const schemaPath = path.join(__dirname, "..", "database", "schema.sql");
  const sql = fs.readFileSync(schemaPath, "utf8");

  const conn = await mysql.createConnection({
    host: process.env.MYSQL_HOST || "127.0.0.1",
    port: Number(process.env.MYSQL_PORT) || 3306,
    user: process.env.MYSQL_USER || "root",
    password: process.env.MYSQL_PASSWORD ?? "",
    multipleStatements: true,
  });

  await conn.query(sql);
  await conn.end();
  console.log("OK: schema applied (database + transactions table).");
}

main().catch((e) => {
  console.error("Failed:", e.message);
  process.exit(1);
});
