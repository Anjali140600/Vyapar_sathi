import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Copy, HandCoins, Pencil, Search, Trash2 } from "lucide-react";
import { useMemo, useState } from "react";
import { toast } from "sonner";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { PageHeader } from "@/components/shared/page-header";
import { toPayload, TransactionForm } from "@/components/shared/transaction-form";
import { Skeleton } from "@/components/ui/skeleton";
import { formatCurrency, formatDate } from "@/lib/format";
import { transactionApi } from "@/lib/api";
import { summarizeTransactions } from "@/lib/insights";
import { useForm } from "react-hook-form";
import { useAuth } from "@/providers/auth-provider";

export function TransactionsPage() {
  const queryClient = useQueryClient();
  const { role } = useAuth();
  const canEdit = role === "owner" || role === "accountant";
  const canDelete = role === "owner";
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState("all");
  const [duplicateSeed, setDuplicateSeed] = useState(null);
  const [editingItem, setEditingItem] = useState(null);
  const [deleteItem, setDeleteItem] = useState(null);

  const transactionsQuery = useQuery({
    queryKey: ["transactions"],
    queryFn: () => transactionApi.list().then((res) => res.data.data || []),
  });
  const typesQuery = useQuery({
    queryKey: ["transaction-types"],
    queryFn: () => transactionApi.getTypes().then((res) => res.data.types || []),
  });

  const transactions = transactionsQuery.data || [];
  const filtered = useMemo(
    () =>
      transactions.filter((item) => {
        const matchesSearch =
          !search ||
          [item.category, item.description, item.transaction_type]
            .filter(Boolean)
            .some((value) => value.toLowerCase().includes(search.toLowerCase()));
        const matchesType = typeFilter === "all" || item.transaction_type === typeFilter;
        return matchesSearch && matchesType;
      }),
    [transactions, search, typeFilter]
  );

  const summary = summarizeTransactions(filtered);

  const updateMutation = useMutation({
    mutationFn: ({ id, values }) => transactionApi.update(id, toPayload(values)),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["transactions"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
      toast.success("Transaction updated.");
      setEditingItem(null);
    },
    onError: (error) => toast.error(error.response?.data?.detail || "Could not update transaction."),
  });

  const deleteMutation = useMutation({
    mutationFn: (id) => transactionApi.remove(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["transactions"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
      toast.success("Transaction deleted.");
      setDeleteItem(null);
    },
    onError: (error) => toast.error(error.response?.data?.detail || "Could not delete transaction."),
  });

  const settleMutation = useMutation({
    mutationFn: (item) => transactionApi.recordPayment(item.id, Number(item.amount_due)),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["transactions"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
      toast.success("Outstanding balance marked as paid.");
    },
    onError: (error) => toast.error(error.response?.data?.detail || "Could not record payment."),
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="Transaction Workspace"
        description="Record money in and out, then filter recent records with business-friendly controls."
      />

      <div className="grid gap-6 xl:grid-cols-[440px_1fr]">
        <Card>
          <CardHeader>
            <div>
              <CardTitle>Smart Entry Form</CardTitle>
              <CardDescription>Add business transactions with GST-friendly fields.</CardDescription>
            </div>
          </CardHeader>
          <CardContent>
            {typesQuery.isLoading ? <Skeleton className="h-[420px]" /> : <TransactionForm types={typesQuery.data || []} defaultValues={duplicateSeed} />}
          </CardContent>
        </Card>

        <div className="space-y-4">
          <div className="grid gap-4 md:grid-cols-3">
            <SummaryCard label="Total In" value={summary.income} tone="income" />
            <SummaryCard label="Total Out" value={summary.expense} tone="expense" />
            <SummaryCard label="Net" value={summary.income - summary.expense} tone="default" />
          </div>

          <Card>
            <CardHeader>
              <div>
                <CardTitle>Records Table</CardTitle>
                <CardDescription>Search and review your saved transactions.</CardDescription>
              </div>
            </CardHeader>
            <CardContent>
              <div className="mb-4 grid gap-3 lg:grid-cols-[1fr_220px]">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                  <Input value={search} onChange={(e) => setSearch(e.target.value)} className="pl-9" placeholder="Search by category, note, or type" />
                </div>
                <select
                  className="h-11 rounded-xl border border-slate-200 bg-white/70 px-3 text-sm dark:border-slate-700 dark:bg-slate-950/50"
                  value={typeFilter}
                  onChange={(e) => setTypeFilter(e.target.value)}
                >
                  <option value="all">All types</option>
                  {typesQuery.data?.map((item) => (
                    <option key={item.value} value={item.value}>
                      {item.label}
                    </option>
                  ))}
                </select>
              </div>

              {transactionsQuery.isLoading ? (
                <div className="space-y-2">
                  {Array.from({ length: 6 }).map((_, index) => (
                    <Skeleton key={index} className="h-14" />
                  ))}
                </div>
              ) : filtered.length === 0 ? (
                <div className="rounded-2xl border border-dashed border-slate-300 p-10 text-center dark:border-slate-700">
                  <p className="font-semibold">No matching transactions</p>
                  <p className="mt-2 text-sm text-slate-500">Try examples like rent, purchase, salary, or client payment.</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="min-w-full text-sm">
                    <thead>
                      <tr className="border-b border-slate-200 text-left text-slate-500 dark:border-slate-800">
                        <th className="pb-3 font-medium">Date</th>
                        <th className="pb-3 font-medium">Category</th>
                        <th className="pb-3 font-medium">Type</th>
                        <th className="pb-3 font-medium text-right">Amount</th>
                        <th className="pb-3 font-medium text-right">GST</th>
                        <th className="pb-3 font-medium text-right">Payment</th>
                        <th className="pb-3 font-medium">Note</th>
                        <th className="pb-3 font-medium text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filtered.map((item) => (
                        <tr key={item.id} className="border-b border-slate-100 dark:border-slate-900">
                          <td className="py-3">{formatDate(item.transaction_date)}</td>
                          <td className="py-3 font-medium">
                            <span>{item.category}</span>
                            {item.is_recurring ? (
                              <span className="ml-2 rounded-full bg-assistant/10 px-2 py-1 text-xs font-medium text-assistant">
                                {item.frequency}
                              </span>
                            ) : null}
                            {item.recurring_parent_id ? (
                              <span className="ml-2 rounded-full bg-slate-100 px-2 py-1 text-xs font-medium text-slate-500 dark:bg-slate-800">
                                Auto
                              </span>
                            ) : null}
                          </td>
                          <td className="py-3 capitalize text-slate-500">{item.transaction_type}</td>
                          <td className="py-3 text-right">
                            <span className={`data-chip ${Number(item.amount) > 0 ? "bg-income/10 text-income" : "bg-expense/10 text-expense"}`}>
                              {formatCurrency(item.amount)}
                            </span>
                          </td>
                          <td className="py-3 text-right">{formatCurrency(item.gst_amount)}</td>
                          <td className="py-3 text-right">
                            <p className="text-xs text-slate-500">Paid {formatCurrency(item.amount_paid)}</p>
                            {Number(item.amount_due) > 0 ? (
                              <p className="mt-1 font-semibold text-expense">
                                Due {formatCurrency(item.amount_due)}
                                {item.due_date ? ` · ${formatDate(item.due_date)}` : ""}
                              </p>
                            ) : (
                              <p className="mt-1 text-xs font-semibold text-income">Paid</p>
                            )}
                          </td>
                          <td className="py-3 text-slate-500">{item.description || "—"}</td>
                          <td className="py-3">
                            <div className="flex justify-end gap-2">
                              {canEdit ? <ActionIcon
                                icon={Pencil}
                                label="Edit"
                                onClick={() =>
                                  setEditingItem({
                                    id: item.id,
                                    transaction_date: item.transaction_date?.split("T")[0] || new Date().toISOString().split("T")[0],
                                    money_direction: ["sales", "service", "other_income", "income"].includes(item.transaction_type) ? "received" : "spent",
                                    type: item.transaction_type,
                                    amount: item.amount,
                                    gst_amount: item.gst_amount,
                                    quantity: item.quantity,
                                    category: item.category,
                                    description: item.description || "",
                                    payment_method: "cash",
                                    has_due: Number(item.amount_due) > 0,
                                    amount_paid: item.amount_paid ?? item.amount,
                                    due_date: item.due_date?.split("T")[0] || "",
                                    is_recurring: Boolean(item.is_recurring),
                                    frequency: item.frequency || "monthly",
                                    next_run_date: item.next_run_date?.split("T")[0] || "",
                                  })
                                }
                              /> : null}
                              <ActionIcon
                                icon={Copy}
                                label="Duplicate"
                                onClick={() =>
                                  setDuplicateSeed({
                                    transaction_date: item.transaction_date?.split("T")[0] || new Date().toISOString().split("T")[0],
                                    money_direction: ["sales", "service", "other_income", "income"].includes(item.transaction_type) ? "received" : "spent",
                                    type: item.transaction_type,
                                    amount: item.amount,
                                    gst_amount: item.gst_amount,
                                    quantity: item.quantity,
                                    category: item.category,
                                    description: item.description,
                                    payment_method: "cash",
                                    has_due: false,
                                    amount_paid: "",
                                    due_date: "",
                                    is_recurring: false,
                                    frequency: "monthly",
                                    next_run_date: "",
                                  })
                                }
                              />
                              {canEdit && Number(item.amount_due) > 0 ? (
                                <ActionIcon
                                  icon={HandCoins}
                                  label="Mark fully paid"
                                  onClick={() => settleMutation.mutate(item)}
                                />
                              ) : null}
                              {canDelete ? <ActionIcon icon={Trash2} label="Delete" onClick={() => setDeleteItem(item)} /> : null}
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      <Dialog open={Boolean(editingItem)} onOpenChange={(open) => !open && setEditingItem(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit Transaction</DialogTitle>
            <DialogDescription>Update the selected transaction and save your changes.</DialogDescription>
          </DialogHeader>
          {editingItem ? (
            <EditTransactionForm
              item={editingItem}
              types={typesQuery.data || []}
              pending={updateMutation.isPending}
              onSubmit={(values) => updateMutation.mutate({ id: editingItem.id, values })}
            />
          ) : null}
        </DialogContent>
      </Dialog>

      <Dialog open={Boolean(deleteItem)} onOpenChange={(open) => !open && setDeleteItem(null)}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Delete Transaction</DialogTitle>
            <DialogDescription>
              Delete {deleteItem?.category || "this transaction"} permanently? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <div className="flex justify-end gap-3">
            <Button variant="outline" onClick={() => setDeleteItem(null)}>
              Cancel
            </Button>
            <Button variant="danger" onClick={() => deleteMutation.mutate(deleteItem.id)} disabled={deleteMutation.isPending}>
              {deleteMutation.isPending ? "Deleting..." : "Delete"}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function SummaryCard({ label, value, tone }) {
  const classMap = {
    income: "bg-income/10 text-income",
    expense: "bg-expense/10 text-expense",
    default: "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-200",
  };

  return (
    <div className="rounded-2xl border border-white/40 bg-white/70 p-4 shadow-soft dark:border-slate-800 dark:bg-slate-900/80">
      <p className="text-sm text-slate-500">{label}</p>
      <p className={`mt-3 inline-flex rounded-full px-3 py-1 text-lg font-bold ${classMap[tone]}`}>{formatCurrency(value)}</p>
    </div>
  );
}

function ActionIcon({ icon: Icon, label, onClick }) {
  return (
    <Button type="button" variant="ghost" size="icon" onClick={onClick} title={label}>
      <Icon className="h-4 w-4" />
    </Button>
  );
}

function EditTransactionForm({ item, types, onSubmit, pending }) {
  const form = useForm({
    defaultValues: item,
  });

  const direction = form.watch("money_direction");
  const hasDue = form.watch("has_due");
  const isRecurring = form.watch("is_recurring");
  const filteredTypes = types.filter((entry) => entry.flow === (direction === "received" ? "in" : "out"));

  return (
    <form
      className="space-y-4"
      onSubmit={form.handleSubmit((values) => onSubmit(values))}
    >
      <div className="grid grid-cols-2 gap-3 rounded-2xl bg-slate-100/80 p-1 dark:bg-slate-800">
        {[
          { label: "Money In", value: "received" },
          { label: "Money Out", value: "spent" },
        ].map((entry) => (
          <button
            key={entry.value}
            type="button"
            onClick={() => form.setValue("money_direction", entry.value)}
            className={`rounded-xl px-4 py-3 text-sm font-semibold transition ${
              direction === entry.value
                ? "bg-white text-slate-900 shadow-soft dark:bg-slate-950 dark:text-slate-100"
                : "text-slate-500 dark:text-slate-300"
            }`}
          >
            {entry.label}
          </button>
        ))}
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Input type="date" {...form.register("transaction_date")} />
        <select className="h-11 rounded-xl border border-slate-200 bg-white/70 px-3 text-sm dark:border-slate-700 dark:bg-slate-950/50" {...form.register("type")}>
          {filteredTypes.map((entry) => (
            <option key={entry.value} value={entry.value}>
              {entry.label}
            </option>
          ))}
        </select>
        <Input type="number" step="0.01" {...form.register("amount")} />
        <Input type="number" step="0.01" {...form.register("gst_amount")} />
        <Input type="number" step="0.001" {...form.register("quantity")} />
        <Input placeholder="Category" {...form.register("category")} />
      </div>
      <Input placeholder="Note" {...form.register("description")} />
      <div className="rounded-2xl border border-slate-200 p-4 dark:border-slate-700">
        <label className="flex cursor-pointer items-center gap-3 text-sm font-semibold">
          <input
            type="checkbox"
            className="h-4 w-4 rounded border-slate-300"
            {...form.register("has_due")}
          />
          Payment pending / Udhaar
        </label>
        {hasDue ? (
          <div className="mt-4 grid gap-4 md:grid-cols-2">
            <Input type="number" min="0" step="0.01" placeholder="Amount paid" {...form.register("amount_paid")} />
            <Input type="date" title="Due date" {...form.register("due_date")} />
          </div>
        ) : null}
      </div>
      <div className="rounded-2xl border border-slate-200 p-4 dark:border-slate-700">
        <label className="flex cursor-pointer items-center gap-3 text-sm font-semibold">
          <input
            type="checkbox"
            className="h-4 w-4 rounded border-slate-300"
            {...form.register("is_recurring")}
          />
          Repeat this transaction automatically
        </label>
        {isRecurring ? (
          <div className="mt-4 grid gap-4 md:grid-cols-2">
            <select
              className="h-11 rounded-xl border border-slate-200 bg-white/70 px-3 text-sm dark:border-slate-700 dark:bg-slate-950/50"
              {...form.register("frequency")}
            >
              <option value="weekly">Weekly</option>
              <option value="monthly">Monthly</option>
              <option value="yearly">Yearly</option>
            </select>
            <Input type="date" title="Next repeat date" {...form.register("next_run_date")} />
          </div>
        ) : null}
      </div>
      <div className="flex justify-end">
        <Button type="submit">{pending ? "Saving..." : "Save Changes"}</Button>
      </div>
    </form>
  );
}
