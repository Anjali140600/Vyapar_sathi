import { useMotionValueEvent } from "framer-motion";
import { ArrowDownRight, ArrowUpRight } from "lucide-react";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { useCountUp } from "@/hooks/use-count-up";
import { formatCurrency } from "@/lib/format";

export function MetricCard({ title, value, trend = 0, tone = "default", icon: Icon }) {
  const motionValue = useCountUp(value);
  const [displayValue, setDisplayValue] = useState(0);

  useMotionValueEvent(motionValue, "change", (latest) => setDisplayValue(latest));

  const positive = trend >= 0;
  const toneClass =
    tone === "income"
      ? "from-income/20 to-emerald-50 dark:to-emerald-950/20"
      : tone === "expense"
        ? "from-expense/20 to-rose-50 dark:to-rose-950/20"
        : tone === "insight"
          ? "from-insight/20 to-amber-50 dark:to-amber-950/20"
          : "from-assistant/20 to-sky-50 dark:to-sky-950/20";

  return (
    <Card className={`bg-gradient-to-br ${toneClass}`}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-slate-500 dark:text-slate-300">{title}</p>
          <p className="mt-3 font-display text-3xl font-bold">{formatCurrency(displayValue)}</p>
        </div>
        <div className="rounded-2xl bg-white/70 p-3 dark:bg-slate-800">
          <Icon className="h-5 w-5" />
        </div>
      </div>
      <div className="mt-4 flex items-center justify-between">
        <Badge variant={positive ? "success" : "danger"} className="gap-1">
          {positive ? <ArrowUpRight className="h-3 w-3" /> : <ArrowDownRight className="h-3 w-3" />}
          {Math.abs(trend).toFixed(0)}%
        </Badge>
        <span className="text-xs text-slate-500 dark:text-slate-400">vs last month</span>
      </div>
    </Card>
  );
}
