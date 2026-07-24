import { cva } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 rounded-xl text-sm font-semibold transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-assistant disabled:pointer-events-none disabled:opacity-60",
  {
    variants: {
      variant: {
        default: "bg-slateDeep text-ivory shadow-soft hover:-translate-y-0.5 dark:bg-income dark:text-slate-950",
        secondary: "bg-white/70 text-slate-700 ring-1 ring-slate-200 hover:bg-white dark:bg-slate-800 dark:text-slate-100 dark:ring-slate-700",
        outline:
          "border border-slate-300 bg-transparent text-slate-700 hover:bg-slate-100 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800",
        ghost: "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800",
        success: "bg-income text-white hover:bg-income/90",
        danger: "bg-expense text-white hover:bg-expense/90",
      },
      size: {
        default: "h-11 px-4 py-2",
        sm: "h-9 rounded-lg px-3",
        lg: "h-12 px-5 text-base",
        icon: "h-10 w-10",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
);

export function Button({ className, variant, size, asChild = false, ...props }) {
  const Comp = asChild ? "span" : "button";
  return <Comp className={cn(buttonVariants({ variant, size }), className)} {...props} />;
}

export { buttonVariants };
