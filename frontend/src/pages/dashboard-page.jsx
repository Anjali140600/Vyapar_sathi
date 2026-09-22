import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { AlertTriangle, ArrowRight, Bot, CircleDollarSign, FileUp, HandCoins, IndianRupee, Plus, ReceiptIndianRupee, Trash2, Wallet } from "lucide-react";
import { useMemo, useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { MetricCard } from "@/components/shared/metric-card";
import { PageHeader } from "@/components/shared/page-header";
import { TransactionForm } from "@/components/shared/transaction-form";
import { budgetApi, transactionApi } from "@/lib/api";
import { formatCurrency, formatDate, getGreeting } from "@/lib/format";
import { buildChartData, buildInsightMessages, buildPeriodStats } from "@/lib/insights";
import { useAuth } from "@/providers/auth-provider";
import { Link } from "react-router-dom";
import { toast } from "sonner";

export function DashboardPage() {
  const queryClient = useQueryClient();
  const { email, role } = useAuth();
  const canManageBudgets = role === "owner" || role === "accountant";
  const [chartMode, setChartMode] = useState("monthly");
  const [quickAddOpen, setQuickAddOpen] = useState(false);
  const [budgetForm, setBudgetForm] = useState({ category: "", amount: "", warning_threshold: "80" });

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
  const budgetsQuery = useQuery({
    queryKey: ["budgets"],
    queryFn: () => budgetApi.list().then((res) => res.data.data || []),
    enabled: canManageBudgets,
  });
  const saveBudgetMutation = useMutation({
    mutationFn: () => budgetApi.save({
      category: budgetForm.category.trim() || null,
      amount: Number(budgetForm.amount),
      warning_threshold: Number(budgetForm.warning_threshold || 80),
    }),
    onSuccess: () => {
      toast.success("Monthly budget saved.");
      setBudgetForm({ category: "", amount: "", warning_threshold: "80" });
      queryClient.invalidateQueries({ queryKey: ["budgets"] });
    },
    onError: (error) => toast.error(error.response?.data?.detail || "Could not save budget."),
  });
  const deleteBudgetMutation = useMutation({
    mutationFn: (id) => budgetApi.remove(id),
    onSuccess: () => {
      toast.success("Budget removed.");
      queryClient.invalidateQueries({ queryKey: ["budgets"] });
    },
    onError: (error) => toast.error(error.response?.data?.detail || "Could not remove budget."),
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

      <div className="grid gap-4 md:grid-cols-2">
        <DueSummaryCard
          title="Outstanding Receivables"
          description="Money customers still owe you"
          value={summaryQuery.data?.outstandingReceivables || 0}
          tone="income"
          icon={CircleDollarSign}
        />
        <DueSummaryCard
          title="Outstanding Payables"
          description="Money you still need to pay"
          value={summaryQuery.data?.outstandingPayables || 0}
          tone="expense"
          icon={Wallet}
        />
      </div>

      {canManageBudgets ? <Card>
        <CardHeader>
          <div>
            <CardTitle>Monthly Budgets & Alerts</CardTitle>
            <CardDescription>Leave category empty to set an overall expense limit.</CardDescription>
          </div>
          <AlertTriangle className="h-5 w-5 text-amber-500" />
        </CardHeader>
        <CardContent className="space-y-5">
          <div className="grid gap-3 md:grid-cols-[1fr_1fr_160px_auto] md:items-end">
            <div>
              <Label>Category (optional)</Label>
              <Input
                placeholder="e.g. Rent"
                value={budgetForm.category}
                onChange={(event) => setBudgetForm((previous) => ({ ...previous, category: event.target.value }))}
              />
            </div>
            <div>
              <Label>Monthly limit</Label>
              <Input
                type="number"
                min="1"
                placeholder="10000"
                value={budgetForm.amount}
                onChange={(event) => setBudgetForm((previous) => ({ ...previous, amount: event.target.value }))}
              />
            </div>
            <div>
              <Label>Warn at %</Label>
              <Input
                type="number"
                min="1"
                max="100"
                value={budgetForm.warning_threshold}
                onChange={(event) => setBudgetForm((previous) => ({ ...previous, warning_threshold: event.target.value }))}
              />
            </div>
            <Button
              onClick={() => saveBudgetMutation.mutate()}
              disabled={!Number(budgetForm.amount) || saveBudgetMutation.isPending}
            >
              Save budget
            </Button>
          </div>

          {(budgetsQuery.data || []).length === 0 ? (
            <div className="rounded-2xl border border-dashed border-slate-300 p-6 text-center text-sm text-slate-500 dark:border-slate-700">
              No budget set for this month.
            </div>
          ) : (
            <div className="grid gap-4 lg:grid-cols-2">
              {(budgetsQuery.data || []).map((budget) => (
                <BudgetStatusCard
                  key={budget.id}
                  budget={budget}
                  onRemove={() => deleteBudgetMutation.mutate(budget.id)}
                />
              ))}
            </div>
          )}
        </CardContent>
      </Card> : null}

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

function BudgetStatusCard({ budget, onRemove }) {
  const width = Math.min(Math.max(Number(budget.percentage) || 0, 0), 100);
  const tone = budget.status === "exceeded"
    ? "bg-expense"
    : budget.status === "warning" ? "bg-amber-500" : "bg-income";
  return (
    <div className="rounded-2xl border border-slate-200 p-4 dark:border-slate-800">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-semibold">{budget.label}</p>
          <p className="text-sm text-slate-500">
            {formatCurrency(budget.spent)} of {formatCurrency(budget.amount)} used
          </p>
        </div>
        <Button size="icon" variant="ghost" onClick={onRemove} aria-label="Remove budget">
          <Trash2 className="h-4 w-4" />
        </Button>
      </div>
      <div className="mt-4 h-2 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
        <div className={`h-full rounded-full ${tone}`} style={{ width: `${width}%` }} />
      </div>
      <div className="mt-2 flex justify-between text-xs">
        <span className={budget.status === "safe" ? "text-slate-500" : "font-semibold text-amber-600"}>
          {budget.status === "exceeded" ? "Budget exceeded" : budget.status === "warning" ? "Budget warning" : "Within budget"}
        </span>
        <span>{Number(budget.percentage).toFixed(1)}%</span>
      </div>
    </div>
  );
}

function DueSummaryCard({ title, description, value, tone, icon: Icon }) {
  const toneClass = tone === "income" ? "text-income bg-income/10" : "text-expense bg-expense/10";
  return (
    <Card>
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-sm text-slate-500 dark:text-slate-300">{title}</p>
          <p className="mt-2 font-display text-2xl font-bold">{formatCurrency(value)}</p>
          <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{description}</p>
        </div>
        <div className={`rounded-2xl p-3 ${toneClass}`}>
          <Icon className="h-5 w-5" />
        </div>
      </div>
    </Card>
  );
}
