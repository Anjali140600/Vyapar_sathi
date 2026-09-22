const stopwords = require("./stopwords");

function normalize(text) {
  if (typeof text !== "string") return "";
  return text
    .trim()
    .replace(/\s+/g, " ")
    .replace(/[""'']/g, "'");
}

/**
 * Tokens for “related words” — removes common fillers, keeps meaningful terms.
 */
function extractKeywords(normalizedLower) {
  const raw = normalizedLower.toLowerCase().replace(/[^\p{L}\p{N}\s]/gu, " ");
  const tokens = raw.split(/\s+/).filter(Boolean);
  const out = [];
  const seen = new Set();
  for (const t of tokens) {
    if (t.length < 2) continue;
    if (stopwords.has(t)) continue;
    if (seen.has(t)) continue;
    seen.add(t);
    out.push(t);
  }
  return out;
}

/** Strong signals that the answer lives in transactional DB (Step 1). */
const SQL_PATTERNS = [
  { re: /\b(total|sum|aggregate)\s+(expense|expenses|income|payment|payments|sale|sales)\b/i, w: 3 },
  { re: /\b(total|how much|what is my)\s+(expense|expenses|income|profit|loss|balance)\b/i, w: 3 },
  { re: /\bhow much\s+total\b/i, w: 3 },
  { re: /\b(how much|what)\s+.+\s+(brought|bought|purchased|procured)\b/i, w: 3 },
  { re: /\b(products?|items?|goods|stock|inventory)\s+i\s+(brought|bought|purchased)\b/i, w: 3 },
  { re: /\b(i|we)\s+(brought|bought|purchased)\s+.+\b(products?|items?|milk|goods)\b/i, w: 3 },
  { re: /\b(how much)\s+(did|have)\s+i\s+(spend|earn|pay|receive)\b/i, w: 3 },
  { re: /\b(this month|last month|this week|last week|this year|last year|today|yesterday|ytd)\b/i, w: 2 },
  { re: /\b(my|all)\s+(expense|expenses|income|transactions|payments|sales)\b/i, w: 2 },
  { re: /\b(transaction|transactions)\b/i, w: 1 },
  { re: /\b(category|categories)\s+(wise|breakdown|split)\b/i, w: 2 },
  { re: /\b(profit|loss|p&l|balance)\b/i, w: 2 },
  { re: /\b(between|from)\s+.+\s+(to|and)\s+.+\s+(date|month|year)?/i, w: 2 },
  { re: /\bhow many\s+(transaction|transactions|entries)\b/i, w: 2 },
  { re: /\b(show|list|get)\s+(my\s+)?(last|recent)\s+\d*\s*(transaction|transactions|entries)\b/i, w: 2 },
  { re: /\b(purchase|purchases|spent on)\b/i, w: 2 },
];

/** Strong signals for GST / general knowledge (RAG), not user’s own ledger. */
const GENERAL_PATTERNS = [
  { re: /\bwhat\s+is\s+(the\s+)?gst\b/i, w: 3 },
  { re: /\bgst\s+(rate|slab|percentage|on|applied|exempt)\b/i, w: 3 },
  { re: /\b(cgst|sgst|igst|cess)\b/i, w: 2 },
  { re: /\b(hsn|sac)\s*(code)?\b/i, w: 2 },
  { re: /\b(in india|under gst|as per gst|gst act)\b/i, w: 2 },
  { re: /\b(exempt|nil rated|zero rated|composition)\b/i, w: 2 },
  { re: /\btax\s+(rate|slab|on)\b/i, w: 2 },
  { re: /\b(section\s+\d+|rule\s+\d+)\b/i, w: 2 },
  { re: /\bwhat\s+(does|do)\s+the\s+law\s+say\b/i, w: 2 },
  { re: /\b(difference|compare)\s+between\b/i, w: 1 },
];

/** Hints that the user asked two things (mixed). */
function hasMixedConnectors(t) {
  return (
    /\s+and\s+(also\s+)?(what|how|tell|explain)\b/i.test(t) ||
    /\s+;[\s]*\w/.test(t) ||
    (t.match(/\?/g) || []).length >= 2 ||
    /\bas well as\b/i.test(t) ||
    /\b(according to|along with|as well as)\s+(the\s+)?(gst|tax|rate|slab|percentage|law)\b/i.test(t)
  );
}

function scoreText(lower) {
  let sql = 0;
  let general = 0;
  const sqlHits = [];
  const generalHits = [];

  for (const { re, w } of SQL_PATTERNS) {
    if (re.test(lower)) {
      sql += w;
      sqlHits.push(re.source.slice(0, 40) + "…");
    }
  }
  for (const { re, w } of GENERAL_PATTERNS) {
    if (re.test(lower)) {
      general += w;
      generalHits.push(re.source.slice(0, 40) + "…");
    }
  }

  return { sql, general, sqlHits, generalHits };
}

/**
 * @returns {{
 *   queryType: 'sql' | 'general' | 'mixed',
 *   normalizedQuery: string,
 *   keywords: string[],
 *   scores: { sql: number, general: number },
 *   signals: { sql: string[], general: string[] }
 * }}
 */
function classifyQuery(rawText) {
  const normalizedQuery = normalize(rawText);
  const lower = normalizedQuery.toLowerCase();
  const keywords = extractKeywords(lower);

  if (!normalizedQuery) {
    return {
      queryType: "general",
      normalizedQuery: "",
      keywords: [],
      scores: { sql: 0, general: 0 },
      signals: { sql: [], general: [] },
      note: "empty query",
    };
  }

  const { sql, general, sqlHits, generalHits } = scoreText(lower);
  const mixedConnector = hasMixedConnectors(lower);

  let queryType;

  /** Ledger / purchase question + GST law question in one sentence → mixed. */
  const ledgerPlusGst =
    sql >= 1 &&
    general >= 1 &&
    (sql >= 2 || general >= 2) &&
    /\b(brought|bought|purchased|expense|income|transaction|total|spent|sale|payment)\b/i.test(lower) &&
    /\b(gst|cgst|sgst|igst|tax\s+rate|hsn|exempt|slab)\b/i.test(lower);

  if (ledgerPlusGst) {
    queryType = "mixed";
  } else if (mixedConnector && sql >= 1 && general >= 1) {
    queryType = "mixed";
  } else if (sql >= 2 && general >= 2) {
    queryType = "mixed";
  } else if (sql >= 2 && general >= 1) {
    queryType = "mixed";
  } else if (sql >= 1 && general >= 2) {
    queryType = "mixed";
  } else if (sql > general && sql >= 2) {
    queryType = "sql";
  } else if (general > sql && general >= 2) {
    queryType = "general";
  } else if (sql >= 1 && general >= 1) {
    queryType = "mixed";
  } else if (sql > general) {
    queryType = "sql";
  } else if (general > sql) {
    queryType = "general";
  } else {
    queryType = "general";
  }

  return {
    queryType,
    normalizedQuery,
    keywords,
    scores: { sql, general },
    signals: {
      sql: sqlHits.slice(0, 8),
      general: generalHits.slice(0, 8),
    },
  };
}

module.exports = { classifyQuery, normalize, extractKeywords };
