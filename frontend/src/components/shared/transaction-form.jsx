import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { transactionApi } from "@/lib/api";

const schema = z.object({
  transaction_date: z.string().min(1, "Date is required"),
  money_direction: z.enum(["received", "spent"]),
  type: z.string().min(1, "Category type is required"),
  amount: z.coerce.number().positive("Amount is required"),
  gst_amount: z.union([z.coerce.number(), z.nan()]).optional(),
  quantity: z.union([z.coerce.number(), z.nan()]).optional(),
  category: z.string().min(2, "Category is required"),
  description: z.string().optional(),
  payment_method: z.string().optional(),
});

export function TransactionForm({ types = [], defaultValues, onSuccess, compact = false }) {
  const queryClient = useQueryClient();
  const form = useForm({
    resolver: zodResolver(schema),
    defaultValues: defaultValues || {
      transaction_date: new Date().toISOString().split("T")[0],
      money_direction: "received",
      type: types.find((item) => item.flow === "in")?.value || "",
      amount: "",
      gst_amount: "",
      quantity: "",
      category: "",
      description: "",
      payment_method: "cash",
    },
  });

  const direction = form.watch("money_direction");

  useEffect(() => {
    if (defaultValues) {
      form.reset(defaultValues);
    }
  }, [defaultValues, form]);

  useEffect(() => {
    const match = types.find((item) => item.flow === (direction === "received" ? "in" : "out"));
    if (match) form.setValue("type", match.value);
  }, [direction, types, form]);

  const mutation = useMutation({
    mutationFn: (values) =>
      transactionApi.create(toPayload(values)),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["transactions"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
      toast.success("Transaction saved successfully.");
      form.reset({
        ...form.getValues(),
        amount: "",
        gst_amount: "",
        quantity: "",
        category: "",
        description: "",
      });
      onSuccess?.();
    },
    onError: (error) => {
      toast.error(error.response?.data?.detail || "Could not save the transaction.");
    },
  });

  const filteredTypes = types.filter((item) => item.flow === (direction === "received" ? "in" : "out"));

  return (
    <form className="space-y-4" onSubmit={form.handleSubmit((values) => mutation.mutate(values))}>
      <div className="grid grid-cols-2 gap-3 rounded-2xl bg-slate-100/80 p-1 dark:bg-slate-800">
        {[
          { label: "Money In", value: "received" },
          { label: "Money Out", value: "spent" },
        ].map((item) => (
          <button
            key={item.value}
            type="button"
            onClick={() => form.setValue("money_direction", item.value)}
            className={`rounded-xl px-4 py-3 text-sm font-semibold transition ${
              direction === item.value
                ? "bg-white text-slate-900 shadow-soft dark:bg-slate-950 dark:text-slate-100"
                : "text-slate-500 dark:text-slate-300"
            }`}
          >
            {item.label}
          </button>
        ))}
      </div>

      <div className={`grid gap-4 ${compact ? "md:grid-cols-2" : "md:grid-cols-2"}`}>
        <Field label="Date / तारीख" error={form.formState.errors.transaction_date?.message}>
          <Input type="date" {...form.register("transaction_date")} />
        </Field>
        <Field label="Type / प्रकार" error={form.formState.errors.type?.message}>
          <select className="h-11 w-full rounded-xl border border-slate-200 bg-white/70 px-3 text-sm dark:border-slate-700 dark:bg-slate-950/50" {...form.register("type")}>
            {filteredTypes.map((item) => (
              <option key={item.value} value={item.value}>
                {item.label}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Amount / राशि" error={form.formState.errors.amount?.message}>
          <Input type="number" step="0.01" placeholder="0.00" {...form.register("amount")} />
        </Field>
        <Field label="GST Amount" error={form.formState.errors.gst_amount?.message}>
          <Input type="number" step="0.01" placeholder="0.00" {...form.register("gst_amount")} />
        </Field>
        <Field label="Quantity" error={form.formState.errors.quantity?.message}>
          <Input type="number" step="0.001" placeholder="12" {...form.register("quantity")} />
        </Field>
        <Field label="Payment Method">
          <select
            className="h-11 w-full rounded-xl border border-slate-200 bg-white/70 px-3 text-sm dark:border-slate-700 dark:bg-slate-950/50"
            {...form.register("payment_method")}
          >
            <option value="cash">Cash</option>
            <option value="upi">UPI</option>
            <option value="bank">Bank Transfer</option>
            <option value="card">Card</option>
          </select>
        </Field>
        <Field label="Category / Item" error={form.formState.errors.category?.message}>
          <Input placeholder="Rent, inventory, client ABC" {...form.register("category")} />
        </Field>
        <Field label="Note / टिप्पणी" error={form.formState.errors.description?.message}>
          <Textarea className="min-h-11" placeholder="Bill no., supplier, rate, or short note" {...form.register("description")} />
        </Field>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <Button type="submit" variant={direction === "received" ? "success" : "default"}>
          {mutation.isPending ? "Saving..." : "Save Transaction"}
        </Button>
        <p className="text-xs text-slate-500 dark:text-slate-400">Payment method is UI-ready and can be persisted once the backend adds support.</p>
      </div>
    </form>
  );
}

export function toPayload(values) {
  return {
    amount: values.amount,
    category: values.category,
    type: values.type,
    quantity: Number.isFinite(values.quantity) ? values.quantity : null,
    gst_amount: Number.isFinite(values.gst_amount) ? values.gst_amount : null,
    description: values.description || null,
    date: values.transaction_date || null,
  };
}

function Field({ label, error, children }) {
  return (
    <div>
      <Label>{label}</Label>
      {children}
      {error ? <p className="mt-1 text-xs text-expense">{error}</p> : null}
    </div>
  );
}
