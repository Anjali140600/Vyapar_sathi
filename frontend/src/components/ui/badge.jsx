import { cn } from "@/lib/utils";

export function Badge({ className, variant = "default", ...props }) {
  const variants = {
    default: "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-200",
    success: "bg-income/15 text-income dark:bg-income/20",
    danger: "bg-expense/15 text-expense dark:bg-expense/20",
    insight: "bg-insight/15 text-amber-700 dark:bg-insight/20 dark:text-amber-300",
    assistant: "bg-assistant/15 text-assistant dark:bg-assistant/20",
  };

  return (
    <span className={cn("inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold", variants[variant], className)} {...props} />
  );
}
