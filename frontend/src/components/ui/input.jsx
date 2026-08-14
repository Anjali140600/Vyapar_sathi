import { forwardRef } from "react";
import { cn } from "@/lib/utils";

export const Input = forwardRef(function Input({ className, ...props }, ref) {
  return (
    <input
      ref={ref}
      className={cn(
        "flex h-11 w-full rounded-xl border border-slate-200 bg-white/70 px-3 py-2 text-sm text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-assistant focus:ring-2 focus:ring-assistant/20 dark:border-slate-700 dark:bg-slate-950/50 dark:text-slate-50",
        className
      )}
      {...props}
    />
  );
});
