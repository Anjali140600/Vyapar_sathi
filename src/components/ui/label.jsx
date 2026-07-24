export function Label({ className = "", ...props }) {
  return <label className={`mb-2 block text-sm font-medium text-slate-700 dark:text-slate-200 ${className}`} {...props} />;
}
