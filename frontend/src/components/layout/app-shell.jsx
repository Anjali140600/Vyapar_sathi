import {
  BarChart3,
  Bot,
  FileText,
  LayoutDashboard,
  LogOut,
  Menu,
  Moon,
  ReceiptText,
  SunMedium,
} from "lucide-react";
import { NavLink, useLocation, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { useAuth } from "@/providers/auth-provider";
import { useTheme } from "@/providers/theme-provider";

const navItems = [
  { label: "Dashboard", to: "/dashboard", icon: LayoutDashboard },
  { label: "Transactions", to: "/transactions", icon: ReceiptText },
  { label: "Assistant", to: "/assistant", icon: Bot },
  { label: "Upload", to: "/upload", icon: FileText },
  { label: "Reports", to: "/reports", icon: BarChart3 },
];

export function AppShell({ children }) {
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const { email, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();

  const handleLogout = () => {
    logout();
    toast.success("Signed out successfully.");
    navigate("/");
  };

  return (
    <div className="min-h-screen pb-24 md:pb-0">
      <div className="mx-auto grid min-h-screen max-w-[1600px] md:grid-cols-[260px_1fr]">
        <aside className="hidden border-r border-white/40 bg-slateDeep px-4 py-6 text-white md:block">
          <div className="flex items-center gap-3 px-3">
            <div className="rounded-2xl bg-white/10 p-3">
              <ReceiptText className="h-6 w-6 text-income" />
            </div>
            <div>
              <p className="font-display text-lg font-bold">Vyapar Sathi</p>
              <p className="text-xs text-slate-300">Aapka Smart Business Diary</p>
            </div>
          </div>

          <div className="mt-8 space-y-1">
            {navItems.map(({ label, to, icon: Icon }) => (
              <NavItem key={to} to={to} icon={Icon} label={label} />
            ))}
          </div>

          <div className="mt-8 rounded-2xl bg-white/10 p-4">
            <Badge variant="insight" className="mb-3 bg-amber-400/15 text-amber-200">
              Secure workspace
            </Badge>
            <p className="text-sm text-slate-100">Built for Indian shop owners, traders, and service businesses.</p>
          </div>

          <div className="mt-auto flex h-[40vh] flex-col justify-end gap-3 px-3">
            <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
              <p className="text-sm font-semibold">{email}</p>
              <p className="text-xs text-slate-300">Private and secure account</p>
            </div>
            <Button variant="secondary" className="w-full justify-start" onClick={toggleTheme}>
              {theme === "dark" ? <SunMedium className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
              {theme === "dark" ? "Light mode" : "Dark mode"}
            </Button>
            <Button variant="outline" className="w-full justify-start border-white/20 text-white hover:bg-white/10" onClick={handleLogout}>
              <LogOut className="h-4 w-4" />
              Logout
            </Button>
          </div>
        </aside>

        <div className="flex min-h-screen flex-col">
          <header className="sticky top-0 z-30 border-b border-slate-200/70 bg-background/90 px-4 py-4 backdrop-blur-xl dark:border-slate-800 md:px-8">
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <div className="rounded-2xl bg-slate-900 p-2 text-white md:hidden">
                  <Menu className="h-5 w-5" />
                </div>
                <div>
                  <p className="text-xs uppercase tracking-[0.24em] text-slate-500 dark:text-slate-400">Vyapar Sathi</p>
                  <h1 className="font-display text-lg font-bold capitalize md:text-xl">{pathname.slice(1) || "Welcome"}</h1>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Badge variant="assistant">English ready</Badge>
                <Button variant="ghost" size="icon" onClick={toggleTheme}>
                  {theme === "dark" ? <SunMedium className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
                </Button>
              </div>
            </div>
          </header>

          <main className="flex-1 px-4 py-6 md:px-8">{children}</main>
        </div>
      </div>

      <nav className="fixed inset-x-3 bottom-3 z-40 rounded-2xl border border-white/30 bg-white/85 p-2 shadow-soft backdrop-blur-xl dark:border-slate-800 dark:bg-slate-900/90 md:hidden">
        <div className="grid grid-cols-5 gap-1">
          {navItems.map(({ label, to, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                cn(
                  "flex flex-col items-center gap-1 rounded-xl px-2 py-2 text-[11px] font-medium",
                  isActive ? "bg-slateDeep text-white dark:bg-income dark:text-slate-950" : "text-slate-500 dark:text-slate-300"
                )
              }
            >
              <Icon className="h-4 w-4" />
              {label}
            </NavLink>
          ))}
        </div>
      </nav>
    </div>
  );
}

function NavItem({ to, icon: Icon, label }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        cn(
          "flex items-center gap-3 rounded-xl px-3 py-3 text-sm font-medium transition",
          isActive ? "bg-white text-slateDeep shadow-soft" : "text-slate-300 hover:bg-white/10 hover:text-white"
        )
      }
    >
      <Icon className="h-4 w-4" />
      {label}
    </NavLink>
  );
}
