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

const schema = z
  .object({
    transaction_date: z.string().min(1, "Date is required"),
    money_direction: z.enum(["received", "spent"]),
    type: z.string().min(1, "Category type is required"),
    amount: z.coerce.number().positive("Amount is required"),
    gst_amount: z.union([z.coerce.number(), z.nan()]).optional(),
    quantity: z.union([z.coerce.number(), z.nan()]).optional(),
    category: z.string().min(2, "Category is required"),
    description: z.string().optional(),
    payment_method: z.string().optional(),
    has_due: z.boolean().default(false),
    amount_paid: z.union([z.coerce.number().min(0), z.nan()]).optional(),
    due_date: z.string().optional(),
    is_recurring: z.boolean().default(false),
    frequency: z.enum(["weekly", "monthly", "yearly"]).optional(),
    next_run_date: z.string().optional(),
  })
  .superRefine((values, context) => {
    if (values.is_recurring && !values.frequency) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["frequency"],
        message: "Frequency is required",
      });
    }
    if (values.has_due && Number(values.amount_paid || 0) > Number(values.amount)) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["amount_paid"],
        message: "Paid amount cannot exceed the total",
      });
    }
    if (
      values.has_due &&
      Number(values.amount_paid || 0) < Number(values.amount) &&
      !values.due_date
    ) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["due_date"],
        message: "Due date is required",
      });
    }
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
      has_due: false,
      amount_paid: "",
      due_date: "",
      is_recurring: false,
      frequency: "monthly",
      next_run_date: "",
    },
  });

  const direction = form.watch("money_direction");
  const hasDue = form.watch("has_due");
  const isRecurring = form.watch("is_recurring");

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
        has_due: false,
        amount_paid: "",
        due_date: "",
        is_recurring: false,
        frequency: "monthly",
        next_run_date: "",
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
            <Field label="Amount already paid" error={form.formState.errors.amount_paid?.message}>
              <Input type="number" min="0" step="0.01" placeholder="0.00" {...form.register("amount_paid")} />
            </Field>
            <Field label="Due date" error={form.formState.errors.due_date?.message}>
              <Input type="date" {...form.register("due_date")} />
            </Field>
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
            <Field label="Frequency" error={form.formState.errors.frequency?.message}>
              <select
                className="h-11 w-full rounded-xl border border-slate-200 bg-white/70 px-3 text-sm dark:border-slate-700 dark:bg-slate-950/50"
                {...form.register("frequency")}
              >
                <option value="weekly">Weekly</option>
                <option value="monthly">Monthly</option>
                <option value="yearly">Yearly</option>
              </select>
            </Field>
            <Field label="First repeat date (optional)">
              <Input type="date" {...form.register("next_run_date")} />
            </Field>
          </div>
        ) : null}
        {isRecurring ? (
          <p className="mt-3 text-xs text-slate-500 dark:text-slate-400">
            If the first repeat date is blank, it is calculated from the transaction date.
          </p>
        ) : null}
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
  const amount = Number(values.amount);
  const amountPaid = Number(values.amount_paid);
  const quantity = Number(values.quantity);
  const gstAmount = Number(values.gst_amount);

  return {
    amount,
    category: values.category,
    type: values.type,
    quantity: Number.isFinite(quantity) && values.quantity !== "" ? quantity : null,
    gst_amount: Number.isFinite(gstAmount) && values.gst_amount !== "" ? gstAmount : null,
    description: values.description || null,
    date: values.transaction_date || null,
    amount_paid: values.has_due && Number.isFinite(amountPaid) ? amountPaid : amount,
    due_date: values.has_due && values.due_date ? values.due_date : null,
    is_recurring: Boolean(values.is_recurring),
    frequency: values.is_recurring ? values.frequency : null,
    next_run_date: values.is_recurring && values.next_run_date ? values.next_run_date : null,
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
