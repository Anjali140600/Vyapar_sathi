/**
 * Allowed business transaction kinds (stored in DB as VARCHAR).
 * flow: "in" = receipt / income side, "out" = payment / expense side.
 */
const TRANSACTION_TYPES = [
  { value: "payment_received", label: "Payment received (from customer)", flow: "in" },
  { value: "sales", label: "Sales / invoice", flow: "in" },
  { value: "service_income", label: "Service income", flow: "in" },
  { value: "interest_income", label: "Interest received", flow: "in" },
  { value: "refund_received", label: "Refund / credit received", flow: "in" },
  { value: "capital_introduced", label: "Capital / owner funds introduced", flow: "in" },
  { value: "loan_received", label: "Loan / borrowing received", flow: "in" },
  { value: "other_income", label: "Other income", flow: "in" },

  { value: "purchase", label: "Purchase / stock / raw materials", flow: "out" },
  { value: "rent", label: "Rent", flow: "out" },
  { value: "salary_wages", label: "Salary & wages", flow: "out" },
  { value: "utilities", label: "Utilities (electricity, water, etc.)", flow: "out" },
  { value: "transport", label: "Transport & logistics", flow: "out" },
  { value: "marketing", label: "Marketing & advertising", flow: "out" },
  { value: "repairs_maintenance", label: "Repairs & maintenance", flow: "out" },
  { value: "professional_fees", label: "Professional / legal / CA fees", flow: "out" },
  { value: "gst_tax_payment", label: "GST / tax payment", flow: "out" },
  { value: "bank_charges", label: "Bank charges & fees", flow: "out" },
  { value: "loan_repayment", label: "Loan repayment", flow: "out" },
  { value: "interest_expense", label: "Interest paid", flow: "out" },
  { value: "drawings", label: "Owner drawings / personal", flow: "out" },
  { value: "other_expense", label: "Other expense", flow: "out" },
];

const ALLOWED = new Set(TRANSACTION_TYPES.map((t) => t.value));

const LABEL_BY_VALUE = Object.fromEntries(TRANSACTION_TYPES.map((t) => [t.value, t.label]));

function isAllowed(value) {
  return typeof value === "string" && ALLOWED.has(value);
}

/** Legacy rows from first schema */
function normalizeLegacyType(value) {
  if (value === "income") return "payment_received";
  if (value === "expense") return "other_expense";
  return value;
}

module.exports = {
  TRANSACTION_TYPES,
  ALLOWED,
  LABEL_BY_VALUE,
  isAllowed,
  normalizeLegacyType,
};
