import { forwardRef } from "react";
import { cn } from "@/lib/utils";

export const Textarea = forwardRef(function Textarea({ className, ...props }, ref) {
  return (
    <textarea
      ref={ref}
      className={cn(
        "flex min-h-28 w-full rounded-xl border border-slate-200 bg-white/70 px-3 py-2 text-sm text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-assistant focus:ring-2 focus:ring-assistant/20 dark:border-slate-700 dark:bg-slate-950/50 dark:text-slate-50",
        className
      )}
      {...props}
    />
  );
});
