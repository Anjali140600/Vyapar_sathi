import { animate, useMotionValue, useTransform } from "framer-motion";
import { useEffect } from "react";

export function useCountUp(target = 0) {
  const count = useMotionValue(0);
  const rounded = useTransform(count, (latest) => Math.round(latest));

  useEffect(() => {
    const controls = animate(count, Number(target || 0), {
      duration: 0.8,
      ease: "easeOut",
    });
    return () => controls.stop();
  }, [count, target]);

  return rounded;
}
