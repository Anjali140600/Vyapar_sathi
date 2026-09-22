#!/usr/bin/env node
/**
 * Step 3 — classify a user query (terminal only).
 * Later: pipe Step 2 output into this script.
 */
const readline = require("readline");
const { classifyQuery } = require("./server/classifier");

function help() {
  console.log(`Vyapar Sathi — Step 3 query classifier

Usage:
  node cli.js "your question here"
  node cli.js
      (interactive: prompts for one line)
  echo "your question" | node cli.js
      (stdin — good for piping Step 2 output)

Output: JSON on stdout (queryType, normalizedQuery, keywords, scores, signals).
`);
}

function readStdin() {
  return new Promise((resolve, reject) => {
    let data = "";
    process.stdin.setEncoding("utf8");
    process.stdin.on("data", (chunk) => {
      data += chunk;
    });
    process.stdin.on("end", () => resolve(data.trim()));
    process.stdin.on("error", reject);
  });
}

function promptQuery() {
  return new Promise((resolve) => {
    const rl = readline.createInterface({
      input: process.stdin,
      output: process.stdout,
    });
    rl.question("Enter query: ", (line) => {
      rl.close();
      resolve(line.trim());
    });
  });
}

async function main() {
  const args = process.argv.slice(2);
  if (args[0] === "-h" || args[0] === "--help") {
    help();
    process.exit(0);
  }

  let text;

  if (!process.stdin.isTTY) {
    text = await readStdin();
  } else if (args.length > 0) {
    text = args.join(" ").trim();
  } else {
    text = await promptQuery();
  }

  if (!text) {
    console.error("Error: empty query.");
    help();
    process.exit(1);
  }

  const result = classifyQuery(text);
  console.log(JSON.stringify(result, null, 2));
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
