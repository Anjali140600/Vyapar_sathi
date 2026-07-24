import re

STOPWORDS = set(
    "a an the and or but if as of at by for from in into like near off on onto out over past per than through to under until up with without "
    "is are was were be been being do does did doing done have has had having "
    "i me my we our you your he she it they them their what which who whom this that these those "
    "there here when where why how all any both each few more most other some such no nor not only same so than too very just can could should would will "
    "about after again against all also am an and another any are as at "
    "before being below between both but by "
    "could did do does doing down during each few for from further had has have having he her here hers herself him himself his how "
    "if in into is it its itself "
    "just like me more most much my myself "
    "no nor not now of off on once only or other ought our ours ourselves out over own "
    "same she should so some such than that the their theirs them themselves then there these they this those through to too "
    "under until up very was we were what when where which while who whom whose why will with would "
    "you your yours yourself yourselves "
    "please tell give show find get list help want need know "
    "something anything everything nothing someone anyone "
    "myself yourself "
    "umm uh er um hey hello hi ok okay yes no".split()
)

class ClassifierService:
    def __init__(self):
        # SQL Patterns (Step 1 Signals)
        self.sql_patterns = [
            (r"\b(total\s+amount\s+of)\s+.+\b", 4),
            (r"\b(total|sum|aggregate)\s+(expense|expenses|income|payment|payments|sale|sales)\b", 3),
            (r"\b(total|how much|what is my)\s+(expense|expenses|income|profit|loss|balance)\b", 3),
            (r"\bhow much\s+total\b", 3),
            (r"\bwhat\s+is\s+my\s+.+\s+amount\b", 3),
            (r"\bhow\s+much\s+is\s+my\s+.+\b", 3),
            (r"\b(amount|total)\s+for\s+.+\b", 2),
            (r"\b(shop\s+rent|rent|salary|purchase|sales|service|expense|income)\b", 2),
            (r"\b(how much|what)\s+.+\s+(brought|bought|purchased|procured)\b", 3),
            (r"\b(products?|items?|goods|stock|inventory)\s+i\s+(brought|bought|purchased)\b", 3),
            (r"\b(i|we)\s+(brought|bought|purchased)\s+.+\b(products?|items?|milk|goods)\b", 3),
            (r"\b(how much)\s+(did|have)\s+i\s+(spend|earn|pay|receive)\b", 3),
            (r"\b(this month|last month|this week|last week|this year|last year|today|yesterday|ytd)\b", 2),
            (r"\b(my|all)\s+(expense|expenses|income|transactions|payments|sales)\b", 2),
            (r"\b(transaction|transactions)\b", 1),
            (r"\b(category|categories)\s+(wise|breakdown|split)\b", 2),
            (r"\b(profit|loss|p&l|balance)\b", 2),
            (r"\b(between|from)\s+.+\s+(to|and)\s+.+\s+(date|month|year)?", 2),
            (r"\bhow many\s+(transaction|transactions|entries)\b", 2),
            (r"\b(show|list|get)\s+(my\s+)?(last|recent)\s+\d*\s*(transaction|transactions|entries)\b", 2),
            (r"\b(purchase|purchases|spent on)\b", 2),
        ]

        # General Patterns (RAG/Knowledge Base Signals)
        self.general_patterns = [
            (r"\bwhat\s+is\s+(the\s+)?gst\b", 3),
            (r"\bgst\s+(rate|slab|percentage|on|applied|exempt)\b", 3),
            (r"\b(cgst|sgst|igst|cess)\b", 2),
            (r"\b(hsn|sac)\s*(code)?\b", 2),
            (r"\b(in india|under gst|as per gst|gst act)\b", 2),
            (r"\b(exempt|nil rated|zero rated|composition)\b", 2),
            (r"\btax\s+(rate|slab|on)\b", 2),
            (r"\b(section\s+\d+|rule\s+\d+)\b", 2),
            (r"\bwhat\s+(does|do)\s+the\s+law\s+say\b", 2),
            (r"\b(difference|compare)\s+between\b", 1),
        ]

    def normalize(self, text: str) -> str:
        if not text: return ""
        text = text.strip()
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"['\"]", "'", text)
        return text

    def extract_keywords(self, text: str) -> list:
        raw = re.sub(r"[^\w\s]", " ", text.lower())
        tokens = raw.split()
        keywords = []
        seen = set()
        for t in tokens:
            if len(t) < 2 or t in STOPWORDS or t in seen:
                continue
            keywords.append(t)
            seen.add(t)
        return keywords

    def has_mixed_connectors(self, text: str) -> bool:
        lower = text.lower()
        if re.search(r"\s+and\s+(also\s+)?(what|how|tell|explain)\b", lower): return True
        if re.search(r"\s+;[\s]*\w", lower): return True
        if lower.count("?") >= 2: return True
        if "as well as" in lower: return True
        if re.search(r"\b(according to|along with|as well as)\s+(the\s+)?(gst|tax|rate|slab|percentage|law)\b", lower): return True
        return False

    def classify(self, text: str) -> dict:
        normalized = self.normalize(text)
        lower = normalized.lower()
        keywords = self.extract_keywords(normalized)

        if not normalized:
            return {
                "query_type": "general",
                "normalized_query": "",
                "keywords": [],
                "scores": {"sql": 0, "general": 0}
            }

        sql_score = 0
        general_score = 0
        
        for pattern, weight in self.sql_patterns:
            if re.search(pattern, lower, re.IGNORECASE):
                sql_score += weight
        
        for pattern, weight in self.general_patterns:
            if re.search(pattern, lower, re.IGNORECASE):
                general_score += weight

        mixed_connector = self.has_mixed_connectors(lower)

        # Ledger / purchase question + GST law question in one sentence → mixed
        ledger_plus_gst = (
            sql_score >= 1 and 
            general_score >= 1 and 
            (sql_score >= 2 or general_score >= 2) and
            re.search(r"\b(brought|bought|purchased|expense|income|transaction|total|spent|sale|payment)\b", lower, re.IGNORECASE) and
            re.search(r"\b(gst|cgst|sgst|igst|tax\s+rate|hsn|exempt|slab)\b", lower, re.IGNORECASE)
        )

        query_type = "general"
        if ledger_plus_gst or (mixed_connector and sql_score >= 1 and general_score >= 1):
            query_type = "mixed"
        elif sql_score >= 2 and general_score >= 2:
            query_type = "mixed"
        elif (sql_score >= 2 and general_score >= 1) or (sql_score >= 1 and general_score >= 2):
            query_type = "mixed"
        elif sql_score > general_score and sql_score >= 2:
            query_type = "sql"
        elif general_score > sql_score and general_score >= 2:
            query_type = "general"
        elif sql_score >= 1 and general_score >= 1:
            query_type = "mixed"
        elif sql_score > general_score:
            query_type = "sql"
        elif general_score > sql_score:
            query_type = "general"

        return {
            "query_type": query_type,
            "normalized_query": normalized,
            "keywords": keywords,
            "scores": {"sql": sql_score, "general": general_score}
        }
