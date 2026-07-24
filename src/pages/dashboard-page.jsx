import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { ArrowRight, Bot, CircleDollarSign, FileUp, HandCoins, IndianRupee, Plus, ReceiptIndianRupee, Wallet } from "lucide-react";
import { useMemo, useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { MetricCard } from "@/components/shared/metric-card";
import { PageHeader } from "@/components/shared/page-header";
import { TransactionForm } from "@/components/shared/transaction-form";
import { transactionApi } from "@/lib/api";
import { formatCurrency, formatDate, getGreeting } from "@/lib/format";
import { buildChartData, buildInsightMessages, buildPeriodStats } from "@/lib/insights";
import { useAuth } from "@/providers/auth-provider";
import { Link } from "react-router-dom";

export function DashboardPage() {
  const { email } = useAuth();
  const [chartMode, setChartMode] = useState("monthly");
  const [quickAddOpen, setQuickAddOpen] = useState(false);

  const transactionsQuery = useQuery({
    queryKey: ["transactions"],
    queryFn: () => transactionApi.list().then((res) => res.data.data || []),
  });
  const typesQuery = useQuery({
    queryKey: ["transaction-types"],
    queryFn: () => transactionApi.getTypes().then((res) => res.data.types || []),
  });
  const summaryQuery = useQuery({
    queryKey: ["dashboard-summary"],
    queryFn: () => transactionApi.summary().then((res) => res.data),
  });

  const transactions = transactionsQuery.data || [];
  const { current, trend } = useMemo(() => buildPeriodStats(transactions), [transactions]);
  const chartData = useMemo(() => buildChartData(transactions, chartMode), [transactions, chartMode]);
  const insights = useMemo(() => buildInsightMessages(transactions), [transactions]);
  const recentTransactions = transactions.slice(0, 5);
  const displayName = email?.split("@")[0] || "Anjali";

  return (
    <div className="space-y-6">
      <PageHeader
        title={`${getGreeting()}, ${displayName} 👋`}
        description={`Here's your ${new Date().toLocaleDateString("en-IN", { month: "long" })} snapshot.`}
        actions={
          <>
            <Button variant="secondary" onClick={() => setQuickAddOpen(true)}>
              <Plus className="h-4 w-4" />
              Quick add
            </Button>
            <Link to="/assistant" className={buttonVariants({ variant: "default", size: "default" })}>
              Ask assistant
              <ArrowRight className="h-4 w-4" />
            </Link>
          </>
        }
      />

      {transactionsQuery.isLoading ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: 4 }).map((_, index) => (
            <Skeleton key={index} className="h-40" />
          ))}
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <MetricCard title="Total Sales" value={current.income || summaryQuery.data?.totalSales} trend={trend.income} tone="income" icon={CircleDollarSign} />
          <MetricCard title="Total Expenses" value={current.expense} trend={trend.expense} tone="expense" icon={Wallet} />
          <MetricCard title="Net Profit" value={(current.income || 0) - (current.expense || 0) || summaryQuery.data?.profit} trend={trend.profit} tone="insight" icon={HandCoins} />
          <MetricCard title="GST Tracked" value={current.gst} trend={trend.gst} tone="default" icon={ReceiptIndianRupee} />
        </div>
      )}

      <div className="grid gap-6 xl:grid-cols-[1.25fr_0.75fr]">
        <Card className="overflow-hidden">
          <CardHeader>
            <div>
              <CardTitle>Income vs Expense</CardTitle>
              <CardDescription>Weekly or monthly business view</CardDescription>
            </div>
            <div className="grid grid-cols-2 gap-2 rounded-2xl bg-slate-100 p-1 dark:bg-slate-800">
              {["weekly", "monthly"].map((mode) => (
                <button
                  key={mode}
                  type="button"
                  onClick={() => setChartMode(mode)}
                  className={`rounded-xl px-3 py-2 text-sm font-semibold ${chartMode === mode ? "bg-white shadow-soft dark:bg-slate-950" : "text-slate-500"}`}
                >
                  {mode}
                </button>
              ))}
            </div>
          </CardHeader>
          <CardContent className="h-[320px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} strokeOpacity={0.2} />
                <XAxis dataKey="label" stroke="#64748b" />
                <YAxis stroke="#64748b" tickFormatter={(value) => `₹${Number(value) / 1000}k`} />
                <Tooltip formatter={(value) => formatCurrency(value)} />
                <Bar dataKey="income" fill="#10B981" radius={[8, 8, 0, 0]} />
                <Bar dataKey="expense" fill="#F43F5E" radius={[8, 8, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <div className="space-y-6">
          <Card className="bg-gradient-to-br from-amber-50 to-sky-50 dark:from-amber-950/30 dark:to-sky-950/30">
            <CardHeader>
              <div>
                <CardTitle>AI Insights</CardTitle>
                <CardDescription>Client-side insights based on your live business data</CardDescription>
              </div>
              <Bot className="h-5 w-5 text-assistant" />
            </CardHeader>
            <CardContent className="space-y-3">
              {insights.map((line) => (
                <motion.div
                  key={line}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  className="rounded-2xl border border-amber-100 bg-white/70 p-3 text-sm dark:border-slate-800 dark:bg-slate-950/40"
                >
                  {line}
                </motion.div>
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <div>
                <CardTitle>Quick Actions</CardTitle>
                <CardDescription>Fast shortcuts for day-to-day operations</CardDescription>
              </div>
            </CardHeader>
            <CardContent className="grid gap-3 sm:grid-cols-2">
              <QuickAction icon={IndianRupee} label="Add Sale" color="bg-income/10 text-income" onClick={() => setQuickAddOpen(true)} />
              <QuickAction icon={Wallet} label="Add Expense" color="bg-expense/10 text-expense" onClick={() => setQuickAddOpen(true)} />
              <QuickAction icon={FileUp} label="Upload Bill" color="bg-amber-100 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300" href="/upload" />
              <QuickAction icon={Bot} label="Ask Assistant" color="bg-assistant/10 text-assistant" href="/assistant" />
            </CardContent>
          </Card>
        </div>
      </div>

      <Card>
        <CardHeader>
          <div>
            <CardTitle>Recent Transactions</CardTitle>
            <CardDescription>Last 5 entries from your business ledger</CardDescription>
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          {recentTransactions.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-slate-300 p-8 text-center text-sm text-slate-500 dark:border-slate-700">
              No transactions yet. Use quick add to record your first business entry.
            </div>
          ) : (
            recentTransactions.map((item) => (
              <div key={item.id} className="flex items-center justify-between rounded-2xl border border-slate-200/70 bg-white/70 p-4 dark:border-slate-800 dark:bg-slate-950/40">
                <div>
                  <p className="font-semibold">{item.category}</p>
                  <p className="text-sm text-slate-500">{formatDate(item.transaction_date)}</p>
                </div>
                <div className="text-right">
                  <p className={`data-chip ${Number(item.amount) >= 0 ? "bg-income/10 text-income" : "bg-expense/10 text-expense"}`}>
                    {formatCurrency(item.amount)}
                  </p>
                  <p className="mt-2 text-xs text-slate-500">{item.description || item.transaction_type}</p>
                </div>
              </div>
            ))
          )}
        </CardContent>
      </Card>

      <Dialog open={quickAddOpen} onOpenChange={setQuickAddOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Quick Add Transaction</DialogTitle>
            <DialogDescription>Add a sale or expense without leaving the dashboard.</DialogDescription>
          </DialogHeader>
          <TransactionForm types={typesQuery.data || []} onSuccess={() => setQuickAddOpen(false)} compact />
        </DialogContent>
      </Dialog>

      <button
        type="button"
        onClick={() => setQuickAddOpen(true)}
        className="fixed bottom-24 right-4 z-30 inline-flex h-14 w-14 items-center justify-center rounded-full bg-slateDeep text-white shadow-soft md:bottom-8 md:right-8"
      >
        <Plus className="h-6 w-6" />
      </button>
    </div>
  );
}

function QuickAction({ icon: Icon, label, color, href, onClick }) {
  const content = (
    <div className={`flex items-center gap-3 rounded-2xl p-4 text-left transition hover:-translate-y-1 ${color}`}>
      <div className="rounded-xl bg-white/70 p-2 dark:bg-slate-900">
        <Icon className="h-4 w-4" />
      </div>
      <span className="font-semibold">{label}</span>
    </div>
  );

  if (href) {
    return (
      <Link to={href} className="block">
        {content}
      </Link>
    );
  }

  return (
    <button type="button" onClick={onClick}>
      {content}
    </button>
  );
}
