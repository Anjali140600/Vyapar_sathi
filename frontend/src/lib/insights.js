import { formatCurrency, toMonthLabel, toWeekLabel } from "@/lib/format";

const incomeTypes = new Set(["income", "sales", "service", "other_income", "inflow"]);
const expenseTypes = new Set(["expense", "purchase", "salary", "rent", "gst_payment", "other_expense", "outflow"]);

export function isIncome(type = "") {
  return incomeTypes.has(type);
}

export function isExpense(type = "") {
  return expenseTypes.has(type);
}

export function summarizeTransactions(transactions = []) {
  return transactions.reduce(
    (acc, item) => {
      const amount = Number(item.amount || 0);
      const gst = Number(item.gst_amount || 0);
      if (isIncome(item.transaction_type || item.type)) acc.income += amount;
      if (isExpense(item.transaction_type || item.type)) acc.expense += amount;
      acc.gst += gst;
      return acc;
    },
    { income: 0, expense: 0, gst: 0 }
  );
}

export function getTrend(current, previous) {
  if (!previous) return 0;
  return ((current - previous) / previous) * 100;
}

export function buildPeriodStats(transactions = []) {
  const now = new Date();
  const currentMonth = now.getMonth();
  const previousMonth = currentMonth === 0 ? 11 : currentMonth - 1;
  const currentYear = now.getFullYear();
  const previousYear = currentMonth === 0 ? currentYear - 1 : currentYear;

  const current = summarizeTransactions(
    transactions.filter((item) => {
      const d = new Date(item.transaction_date || item.date);
      return d.getMonth() === currentMonth && d.getFullYear() === currentYear;
    })
  );
  const previous = summarizeTransactions(
    transactions.filter((item) => {
      const d = new Date(item.transaction_date || item.date);
      return d.getMonth() === previousMonth && d.getFullYear() === previousYear;
    })
  );

  return {
    current,
    previous,
    trend: {
      income: getTrend(current.income, previous.income),
      expense: getTrend(current.expense, previous.expense),
      profit: getTrend(current.income - current.expense, previous.income - previous.expense),
      gst: getTrend(current.gst, previous.gst),
    },
  };
}

export function buildChartData(transactions = [], mode = "monthly") {
  const map = new Map();
  transactions.forEach((item) => {
    const date = new Date(item.transaction_date || item.date);
    const key = mode === "weekly" ? toWeekLabel(date) : toMonthLabel(date);
    const current = map.get(key) || { label: key, income: 0, expense: 0, profit: 0 };
    const amount = Number(item.amount || 0);
    if (isIncome(item.transaction_type || item.type)) current.income += amount;
    if (isExpense(item.transaction_type || item.type)) current.expense += amount;
    current.profit = current.income - current.expense;
    map.set(key, current);
  });
  return Array.from(map.values());
}

export function topCategories(transactions = [], kind = "expense") {
  const tracker = {};
  transactions.forEach((item) => {
    const type = item.transaction_type || item.type;
    if (kind === "expense" && !isExpense(type)) return;
    if (kind === "income" && !isIncome(type)) return;
    const key = item.category || "General";
    tracker[key] = (tracker[key] || 0) + Number(item.amount || 0);
  });

  return Object.entries(tracker)
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value);
}

export function buildInsightMessages(transactions = []) {
  const { current, trend } = buildPeriodStats(transactions);
  const topExpense = topCategories(transactions, "expense")[0];
  const lines = [];
  if (topExpense) lines.push(`${topExpense.name} is your top expense at ${formatCurrency(topExpense.value)}.`);
  lines.push(
    trend.profit >= 0
      ? `Profit is up ${Math.abs(trend.profit).toFixed(0)}% versus last month.`
      : `Profit is down ${Math.abs(trend.profit).toFixed(0)}% versus last month.`
  );
  lines.push(`Current month snapshot: sales ${formatCurrency(current.income)}, expenses ${formatCurrency(current.expense)}.`);
  return lines;
}

export function groupLastSixMonths(transactions = []) {
  const now = new Date();
  const months = Array.from({ length: 6 }, (_, index) => {
    const d = new Date(now.getFullYear(), now.getMonth() - (5 - index), 1);
    return {
      key: `${d.getFullYear()}-${d.getMonth()}`,
      label: toMonthLabel(d),
      income: 0,
      expense: 0,
      profit: 0,
      gst: 0,
    };
  });

  const map = Object.fromEntries(months.map((item) => [item.key, item]));
  transactions.forEach((item) => {
    const d = new Date(item.transaction_date || item.date);
    const key = `${d.getFullYear()}-${d.getMonth()}`;
    if (!map[key]) return;
    const target = map[key];
    const amount = Number(item.amount || 0);
    const gst = Number(item.gst_amount || 0);
    if (isIncome(item.transaction_type || item.type)) target.income += amount;
    if (isExpense(item.transaction_type || item.type)) target.expense += amount;
    target.gst += gst;
    target.profit = target.income - target.expense;
  });

  return months;
}
