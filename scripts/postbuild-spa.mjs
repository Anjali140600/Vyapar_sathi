import fs from "fs";
import path from "path";

const publicDir = path.resolve("public");
const indexHtml = path.join(publicDir, "index.html");
const routes = ["dashboard", "transactions", "assistant", "upload", "reports"];

if (!fs.existsSync(indexHtml)) {
  process.exit(0);
}

const html = fs.readFileSync(indexHtml, "utf8");

for (const route of routes) {
  const routeDir = path.join(publicDir, route);
  fs.mkdirSync(routeDir, { recursive: true });
  fs.writeFileSync(path.join(routeDir, "index.html"), html);
}
