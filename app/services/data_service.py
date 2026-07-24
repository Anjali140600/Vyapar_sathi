from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from app.models.schema import Transaction
import datetime
from decimal import Decimal
from difflib import SequenceMatcher
import re

class DataService:
    INCOME_TYPES = {"income", "sales", "service", "other_income"}
    EXPENSE_TYPES = {"expense", "purchase", "salary", "rent", "gst_payment", "other_expense"}
    CATEGORY_HINT_WORDS = {"item", "items", "material", "materials", "rent", "shop", "salary", "steel", "plastic", "goods", "product", "products"}
    QUERY_NOISE_WORDS = {
        "what", "is", "my", "the", "of", "for", "show", "tell", "me", "how", "much", "many",
        "total", "amount", "sum", "value", "quantity", "qty", "units", "pieces", "gst", "tax",
        "recent", "last", "top", "highest", "lowest", "maximum", "minimum", "average", "avg",
        "transaction", "transactions", "entry", "entries", "in", "this", "month", "year", "today",
        "yesterday", "current", "profit", "loss", "balance", "sales", "sale", "income", "expense", "expenses"
    }

    @staticmethod
    def _to_float(value) -> float:
        if value is None:
            return 0.0
        if isinstance(value, Decimal):
            return float(value)
        return float(value)

    @classmethod
    def _apply_user_filter(cls, query, user_id: str):
        if user_id is None:
            return query
        return query.filter(Transaction.user_id == user_id)

    @classmethod
    def _category_variants(cls, query_text: str) -> list[str]:
        normalized = cls._normalize_category_text(query_text)
        if not normalized:
            return []

        variants = {normalized}
        compact = normalized.replace(" ", "")
        if compact:
            variants.add(compact)

        synonyms = {
            "shop rent": {"rent", "shoprent"},
            "rent": {"shop rent", "shoprent"},
        }
        variants.update(synonyms.get(normalized, set()))

        singular = cls._singularize_phrase(normalized)
        if singular:
            variants.add(singular)
            variants.add(singular.replace(" ", ""))

        return [v for v in variants if v]

    @staticmethod
    def _normalize_category_text(text: str) -> str:
        normalized = " ".join((text or "").lower().split())
        normalized = normalized.replace("-", " ")
        return normalized.strip()

    @staticmethod
    def _singularize_word(word: str) -> str:
        if len(word) <= 3:
            return word
        if word.endswith("ies") and len(word) > 4:
            return word[:-3] + "y"
        if word.endswith("es") and len(word) > 4:
            return word[:-2]
        if word.endswith("s") and not word.endswith("ss"):
            return word[:-1]
        return word

    @classmethod
    def _singularize_phrase(cls, text: str) -> str:
        return " ".join(cls._singularize_word(part) for part in cls._normalize_category_text(text).split())

    @staticmethod
    def _token_set(text: str) -> set[str]:
        return {token for token in DataService._normalize_category_text(text).split() if token}

    @staticmethod
    def _similarity(a: str, b: str) -> float:
        return SequenceMatcher(None, a, b).ratio()

    @staticmethod
    def _resolve_best_category_match(db: Session, query_text: str, user_id: str) -> tuple[str | None, float]:
        normalized_query = DataService._normalize_category_text(query_text)
        if not normalized_query:
            return None, 0.0

        query_tokens = DataService._token_set(normalized_query)
        singular_query = DataService._singularize_phrase(normalized_query)

        categories_query = db.query(Transaction.category).distinct()
        categories_query = DataService._apply_user_filter(categories_query, user_id)
        categories = [row[0] for row in categories_query.all() if row[0]]

        best_category = None
        best_score = 0.0

        for category in categories:
            normalized_category = DataService._normalize_category_text(category)
            singular_category = DataService._singularize_phrase(normalized_category)
            category_tokens = DataService._token_set(normalized_category)

            score = max(
                DataService._similarity(normalized_query, normalized_category),
                DataService._similarity(singular_query, singular_category),
            )

            if query_tokens and category_tokens:
                overlap = len(query_tokens & category_tokens) / max(len(query_tokens), len(category_tokens))
                score = max(score, overlap)

            if normalized_query in normalized_category or singular_query in singular_category:
                score = max(score, 0.95)

            if score > best_score:
                best_score = score
                best_category = category

        return best_category, best_score

    @staticmethod
    def _resolve_best_category(db: Session, query_text: str, user_id: str) -> str | None:
        best_category, best_score = DataService._resolve_best_category_match(db, query_text, user_id)
        if best_score >= 0.60:
            return best_category
        return None

    @staticmethod
    def get_total_sales(db: Session, user_id: str):
        """Calculates total sales (income) for the user."""
        query = db.query(func.sum(Transaction.amount)).filter(
            Transaction.type.in_(DataService.INCOME_TYPES)
        )
        query = DataService._apply_user_filter(query, user_id)
        result = query.scalar()
        return DataService._to_float(result)

    @staticmethod
    def get_total_expenses(db: Session, user_id: str):
        """Calculates total expenses for the user."""
        query = db.query(func.sum(Transaction.amount)).filter(
            Transaction.type.in_(DataService.EXPENSE_TYPES)
        )
        query = DataService._apply_user_filter(query, user_id)
        result = query.scalar()
        return DataService._to_float(result)

    @staticmethod
    def get_recent_transactions(db: Session, user_id: str, limit: int = 5):
        """Fetches the most recent transactions."""
        query = db.query(Transaction)
        query = DataService._apply_user_filter(query, user_id)
        return query.order_by(Transaction.created_at.desc()).limit(limit).all()

    @staticmethod
    def get_current_month_summary(db: Session, user_id: str):
        """Summary for the current month."""
        now = datetime.datetime.now()
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        income_query = db.query(func.sum(Transaction.amount)).filter(
            Transaction.type.in_(DataService.INCOME_TYPES),
            Transaction.created_at >= start_of_month
        )
        expense_query = db.query(func.sum(Transaction.amount)).filter(
            Transaction.type.in_(DataService.EXPENSE_TYPES),
            Transaction.created_at >= start_of_month
        )
        income_query = DataService._apply_user_filter(income_query, user_id)
        expense_query = DataService._apply_user_filter(expense_query, user_id)

        income = DataService._to_float(income_query.scalar())
        expense = DataService._to_float(expense_query.scalar())

        return {"income": income, "expense": expense, "profit": income - expense}

    @staticmethod
    def _resolve_date_range(query_text: str):
        now = datetime.datetime.now()
        today = now.date()
        lower = (query_text or "").lower()

        if "today" in lower:
            return today, today, "today"
        if "yesterday" in lower:
            yesterday = today - datetime.timedelta(days=1)
            return yesterday, yesterday, "yesterday"
        if "last month" in lower:
            first_this_month = today.replace(day=1)
            last_prev_month = first_this_month - datetime.timedelta(days=1)
            start_prev_month = last_prev_month.replace(day=1)
            return start_prev_month, last_prev_month, "last month"
        if "this month" in lower or "current month" in lower:
            start_this_month = today.replace(day=1)
            return start_this_month, today, "this month"
        if "this year" in lower:
            start_this_year = today.replace(month=1, day=1)
            return start_this_year, today, "this year"

        return None, None, "overall"

    @staticmethod
    def _build_base_query(db: Session, user_id: str, query_text: str):
        query = db.query(Transaction)
        query = DataService._apply_user_filter(query, user_id)
        start_date, end_date, label = DataService._resolve_date_range(query_text)
        if start_date:
            query = query.filter(Transaction.date >= start_date)
        if end_date:
            query = query.filter(Transaction.date <= end_date)
        return query, label

    @staticmethod
    def _sum_amount(query, types: set[str]) -> float:
        total = query.filter(Transaction.type.in_(types)).with_entities(func.sum(Transaction.amount)).scalar()
        return DataService._to_float(total)

    @staticmethod
    def _sum_field(query, field) -> float:
        total = query.with_entities(func.sum(field)).scalar()
        return DataService._to_float(total)

    @staticmethod
    def _avg_field(query, field) -> float:
        avg_value = query.with_entities(func.avg(field)).scalar()
        return DataService._to_float(avg_value)

    @staticmethod
    def _extract_limit(query_text: str, default: int = 3) -> int:
        match = re.search(r"\b(?:last|recent|top)\s+(\d+)\b", query_text)
        if match:
            return max(1, min(int(match.group(1)), 10))
        return default

    @staticmethod
    def _format_tx(tx: Transaction) -> str:
        category = tx.category or "uncategorized"
        tx_type = tx.type or "transaction"
        amount = DataService._to_float(tx.amount)
        return f"{category} ({tx_type}) Rs. {amount:,.2f}"

    @staticmethod
    def _category_hint_query(query_text: str) -> bool:
        lower = (query_text or "").lower()
        if re.search(r"\b(amount|total|sum|gst|tax|qty|quantity|units?)\s+(of|for)\b", lower):
            return True
        if any(word in lower.split() for word in DataService.CATEGORY_HINT_WORDS):
            return True
        return False

    @staticmethod
    def _extract_category_search_text(query_text: str) -> str:
        lower = DataService._normalize_category_text(query_text)
        if not lower:
            return ""

        patterns = [
            r"\b(?:amount|total|sum|gst|tax|quantity|qty|units?|pieces)\s+(?:of|for)\s+(.+)$",
            r"\b(?:of|for|on)\s+(.+)$",
        ]
        for pattern in patterns:
            match = re.search(pattern, lower)
            if match:
                candidate = DataService._normalize_category_text(match.group(1))
                if candidate:
                    return candidate

        tokens = [token for token in lower.split() if token not in DataService.QUERY_NOISE_WORDS]
        return " ".join(tokens).strip()

    @staticmethod
    def _apply_type_filter(query, lower: str):
        if any(word in lower for word in ("sales", "sale", "income", "revenue", "service income", "other income")):
            return query.filter(Transaction.type.in_(DataService.INCOME_TYPES)), "sales"
        if any(word in lower for word in ("expense", "expenses", "spend", "spent", "purchase", "salary", "rent", "gst payment", "other expense")):
            return query.filter(Transaction.type.in_(DataService.EXPENSE_TYPES)), "expenses"
        return query, "transactions"

    @staticmethod
    def _apply_category_filter(db: Session, query, lower: str, user_id: str):
        if not DataService._category_hint_query(lower):
            return query, None, 0.0

        category_search = DataService._extract_category_search_text(lower) or lower
        best_category, score = DataService._resolve_best_category_match(db, category_search, user_id)
        if not best_category or score < 0.72:
            return query, None, score

        variants = DataService._category_variants(best_category)
        conditions = [func.lower(Transaction.category) == variant for variant in variants]
        conditions.extend(func.lower(Transaction.category).like(f"%{variant}%") for variant in variants if len(variant) >= 4)
        return query.filter(or_(*conditions)), best_category, score

    @staticmethod
    def answer_sql_query(db: Session, query_text: str, user_id: str):
        lower = (query_text or "").lower().strip()
        if not lower:
            return None

        base_query, period_label = DataService._build_base_query(db, user_id, lower)
        label_suffix = f" for {period_label}" if period_label != "overall" else ""
        filtered_query, noun = DataService._apply_type_filter(base_query, lower)
        filtered_query, best_category, _ = DataService._apply_category_filter(db, filtered_query, lower, user_id)
        noun_label = best_category or noun
        sql_signal = bool(
            re.search(
                r"\b(my|transaction|transactions|entries|sales|sale|income|revenue|expense|expenses|spend|spent|purchase|rent|salary|profit|loss|balance|amount|total|sum|quantity|qty|units|pieces|gst|tax|average|avg|recent|last|highest|lowest|maximum|minimum|count|how many)\b",
                lower,
            )
        ) or bool(best_category)

        if not sql_signal:
            return None

        if "how many" in lower or ("count" in lower and any(word in lower for word in ("transaction", "transactions", "entries", "sales", "expenses", "items"))):
            count = filtered_query.count()
            return f"You have {count} {noun_label}{label_suffix} in MySQL."

        if re.search(r"\b(recent|last)\b", lower) and any(word in lower for word in ("transaction", "transactions", "entries")):
            limit = DataService._extract_limit(lower, default=3)
            recent = filtered_query.order_by(Transaction.created_at.desc()).limit(limit).all()
            if not recent:
                return f"No {noun_label} found{label_suffix} in MySQL."
            return f"Recent {noun_label}{label_suffix}: " + "; ".join(DataService._format_tx(tx) for tx in recent) + "."

        if any(word in lower for word in ("highest", "largest", "maximum", "max")):
            tx = filtered_query.order_by(Transaction.amount.desc()).first()
            if not tx:
                return f"No {noun_label} found{label_suffix} in MySQL."
            return f"Your highest {noun_label.rstrip('s')}{label_suffix} is {DataService._format_tx(tx)}."

        if any(word in lower for word in ("lowest", "minimum", "min", "smallest")):
            tx = filtered_query.order_by(Transaction.amount.asc()).first()
            if not tx:
                return f"No {noun_label} found{label_suffix} in MySQL."
            return f"Your lowest {noun_label.rstrip('s')}{label_suffix} is {DataService._format_tx(tx)}."

        if any(word in lower for word in ("average", "avg", "mean")):
            avg_amount = DataService._avg_field(filtered_query, Transaction.amount)
            return f"Your average {noun_label.rstrip('s')}{label_suffix} amount in MySQL is Rs. {avg_amount:,.2f}."

        if any(word in lower for word in ("quantity", "qty", "units", "pieces")):
            total_qty = DataService._sum_field(filtered_query, Transaction.quantity)
            return f"Your total quantity for {noun_label}{label_suffix} in MySQL is {total_qty:,.3f}."

        if any(word in lower for word in ("gst", "gst amount", "tax", "tax amount")):
            total_gst = DataService._sum_field(filtered_query, Transaction.gst_amount)
            return f"Your total GST for {noun_label}{label_suffix} in MySQL is Rs. {total_gst:,.2f}."

        if any(word in lower for word in ("profit", "loss", "balance", "p&l")):
            income = DataService._sum_amount(base_query, DataService.INCOME_TYPES)
            expense = DataService._sum_amount(base_query, DataService.EXPENSE_TYPES)
            profit = income - expense
            return f"Your profit{label_suffix} from MySQL is Rs. {profit:,.2f}."

        if best_category and any(word in lower for word in ("amount", "total", "sum", "value")):
            summary = DataService.summarize_category_amount(db, best_category, user_id)
            if summary:
                amount = DataService._to_float(summary["amount"])
                if summary["count"] == 1:
                    return f"Your {summary['category']} amount from MySQL is Rs. {amount:,.2f}."
                return f"Your total {summary['category']} amount from MySQL is Rs. {amount:,.2f} across {summary['count']} transactions."

        if any(word in lower for word in ("sales", "sale", "income", "revenue")):
            total = DataService._sum_amount(base_query, DataService.INCOME_TYPES)
            return f"Your total sales{label_suffix} from MySQL are Rs. {total:,.2f}."

        if any(word in lower for word in ("expense", "expenses", "spend", "spent", "purchase", "rent", "salary", "gst payment")):
            total = DataService._sum_amount(base_query, DataService.EXPENSE_TYPES)
            return f"Your total expenses{label_suffix} from MySQL are Rs. {total:,.2f}."

        if best_category:
            summary = DataService.summarize_category_amount(db, best_category, user_id)
            if summary:
                return f"MySQL summary for {summary['category']}{label_suffix}: amount Rs. {DataService._to_float(summary['amount']):,.2f}, GST Rs. {DataService._to_float(summary['gst_amount']):,.2f}, quantity {DataService._to_float(summary['quantity']):,.3f}."

        income = DataService._sum_amount(base_query, DataService.INCOME_TYPES)
        expense = DataService._sum_amount(base_query, DataService.EXPENSE_TYPES)
        total_gst = DataService._sum_field(base_query, Transaction.gst_amount)
        return f"MySQL summary{label_suffix}: sales Rs. {income:,.2f}, expenses Rs. {expense:,.2f}, GST Rs. {total_gst:,.2f}, profit Rs. {income - expense:,.2f}."

    @staticmethod
    def find_transactions_by_category(db: Session, query_text: str, user_id: str, limit: int = 10):
        variants = DataService._category_variants(query_text)
        best_category = DataService._resolve_best_category(db, query_text, user_id)
        if best_category:
            variants.extend(DataService._category_variants(best_category))

        if not variants:
            return []

        variants = list(dict.fromkeys(variants))
        conditions = [func.lower(Transaction.category) == variant for variant in variants]
        conditions.extend(func.lower(Transaction.category).like(f"%{variant}%") for variant in variants if len(variant) >= 4)
        query = db.query(Transaction).filter(or_(*conditions))
        query = DataService._apply_user_filter(query, user_id)
        return query.order_by(Transaction.created_at.desc()).limit(limit).all()

    @staticmethod
    def summarize_category_amount(db: Session, query_text: str, user_id: str):
        matches = DataService.find_transactions_by_category(db, query_text, user_id)
        if not matches:
            return None

        total_amount = float(sum(DataService._to_float(tx.amount) for tx in matches))
        total_gst = float(sum(DataService._to_float(tx.gst_amount) for tx in matches))
        total_quantity = float(sum(DataService._to_float(tx.quantity) for tx in matches))
        latest = matches[0]

        return {
            "category": latest.category,
            "count": len(matches),
            "amount": total_amount,
            "gst_amount": total_gst,
            "quantity": total_quantity,
            "latest_date": str(latest.date) if latest.date else None,
            "types": sorted({tx.type for tx in matches if tx.type}),
        }
