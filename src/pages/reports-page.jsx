import { useQuery } from "@tanstack/react-query";
import { Download, TrendingUp } from "lucide-react";
import { useMemo, useState } from "react";
import { Cell, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader } from "@/components/shared/page-header";
import { formatCurrency } from "@/lib/format";
import { groupLastSixMonths, summarizeTransactions, topCategories } from "@/lib/insights";
import { transactionApi } from "@/lib/api";

const colors = ["#10B981", "#0EA5E9", "#F59E0B", "#F43F5E", "#6366F1", "#8B5CF6"];
const colorClasses = ["bg-income", "bg-assistant", "bg-insight", "bg-expense", "bg-indigo-500", "bg-violet-500"];

export function ReportsPage() {
  const [monthFilter, setMonthFilter] = useState("6m");
  const transactionsQuery = useQuery({
    queryKey: ["transactions"],
    queryFn: () => transactionApi.list().then((res) => res.data.data || []),
  });

  const transactions = transactionsQuery.data || [];
  const months = useMemo(() => groupLastSixMonths(transactions), [transactions]);
  const totals = useMemo(() => summarizeTransactions(transactions), [transactions]);
  const expenseCategories = useMemo(() => topCategories(transactions, "expense").slice(0, 5), [transactions]);
  const incomeCategories = useMemo(() => topCategories(transactions, "income").slice(0, 5), [transactions]);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Business Reports & Insights"
        description="Track monthly performance, top categories, and profit trends."
        actions={
          <>
            <select
              value={monthFilter}
              onChange={(e) => setMonthFilter(e.target.value)}
              className="h-11 rounded-xl border border-slate-200 bg-white/70 px-3 text-sm dark:border-slate-700 dark:bg-slate-950/50"
            >
              <option value="6m">Last 6 months</option>
              <option value="3m">Last 3 months</option>
              <option value="1m">This month</option>
            </select>
            <Button variant="outline" onClick={() => toast.info("Export buttons are ready in the UI. Connect a PDF/CSV backend endpoint when available.")}>
              <Download className="h-4 w-4" />
              Export PDF / CSV
            </Button>
          </>
        }
      />

      {transactionsQuery.isLoading ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: 4 }).map((_, index) => (
            <Skeleton key={index} className="h-36" />
          ))}
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <ReportCard title="Sales" value={totals.income} />
          <ReportCard title="Expenses" value={totals.expense} />
          <ReportCard title="Profit" value={totals.income - totals.expense} />
          <ReportCard title="GST" value={totals.gst} />
        </div>
      )}

      <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <Card>
          <CardHeader>
            <div>
              <CardTitle>Profit Trend</CardTitle>
              <CardDescription>Last 6 months performance line</CardDescription>
            </div>
            <TrendingUp className="h-5 w-5 text-income" />
          </CardHeader>
          <CardContent className="h-[320px]">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={months}>
                <XAxis dataKey="label" stroke="#64748b" />
                <YAxis stroke="#64748b" tickFormatter={(value) => `₹${Number(value) / 1000}k`} />
                <Tooltip formatter={(value) => formatCurrency(value)} />
                <Line type="monotone" dataKey="profit" stroke="#10B981" strokeWidth={3} dot={{ r: 4 }} />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div>
              <CardTitle>Top Expense Categories</CardTitle>
              <CardDescription>Donut chart for major outflows</CardDescription>
            </div>
          </CardHeader>
          <CardContent className="grid gap-4 lg:grid-cols-[1fr_220px]">
            <div className="h-[260px]">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={expenseCategories} dataKey="value" nameKey="name" innerRadius={60} outerRadius={100} paddingAngle={3}>
                    {expenseCategories.map((entry, index) => (
                      <Cell key={entry.name} fill={colors[index % colors.length]} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(value) => formatCurrency(value)} />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="space-y-3">
              {expenseCategories.map((item, index) => (
                <div key={item.name} className="flex items-center gap-3 rounded-2xl bg-slate-50 p-3 dark:bg-slate-950/50">
                  <span className={`h-3 w-3 rounded-full ${colorClasses[index % colorClasses.length]}`} />
                  <div>
                    <p className="font-medium">{item.name}</p>
                    <p className="text-xs text-slate-500">{formatCurrency(item.value)}</p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
        <Card>
          <CardHeader>
            <CardTitle>Income Sources</CardTitle>
            <CardDescription>Top categories contributing to revenue</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {incomeCategories.map((item) => (
              <div key={item.name} className="flex items-center justify-between rounded-2xl border border-slate-200 p-4 dark:border-slate-800">
                <div>
                  <p className="font-medium">{item.name}</p>
                  <p className="text-xs text-slate-500">Revenue source</p>
                </div>
                <p className="font-semibold text-income">{formatCurrency(item.value)}</p>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Top Spending Table</CardTitle>
            <CardDescription>Category share of total expenses</CardDescription>
          </CardHeader>
          <CardContent>
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-left text-slate-500 dark:border-slate-800">
                  <th className="pb-3">Category</th>
                  <th className="pb-3 text-right">Amount</th>
                  <th className="pb-3 text-right">% of expense</th>
                  <th className="pb-3 text-right">Trend</th>
                </tr>
              </thead>
              <tbody>
                {expenseCategories.map((item) => (
                  <tr key={item.name} className="border-b border-slate-100 dark:border-slate-900">
                    <td className="py-3">{item.name}</td>
                    <td className="py-3 text-right">{formatCurrency(item.value)}</td>
                    <td className="py-3 text-right">{((item.value / (totals.expense || 1)) * 100).toFixed(1)}%</td>
                    <td className="py-3 text-right">
                      <span className="rounded-full bg-amber-100 px-2.5 py-1 text-xs font-semibold text-amber-700 dark:bg-amber-950/40 dark:text-amber-300">
                        Stable
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function ReportCard({ title, value }) {
  return (
    <div className="rounded-2xl border border-white/40 bg-white/80 p-5 shadow-soft dark:border-slate-800 dark:bg-slate-900/80">
      <p className="text-sm text-slate-500">{title}</p>
      <p className="mt-3 font-display text-3xl font-bold">{formatCurrency(value)}</p>
    </div>
  );
}
