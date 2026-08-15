import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { Bot, Landmark, ShieldCheck, Sparkles, Upload } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { authApi } from "@/lib/api";
import { useAuth } from "@/providers/auth-provider";

const loginSchema = z.object({
  email: z.string().email(),
  password: z.string().min(6),
});

const signupSchema = loginSchema.extend({
  fullName: z.string().min(2),
});

export function AuthPage() {
  const [mode, setMode] = useState("login");
  const navigate = useNavigate();
  const { login } = useAuth();

  const loginForm = useForm({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "" },
  });

  const signupForm = useForm({
    resolver: zodResolver(signupSchema),
    defaultValues: { fullName: "", email: "", password: "" },
  });

  const loginMutation = useMutation({
    mutationFn: (values) => authApi.login({ username: values.email, password: values.password }),
    onSuccess: (response, values) => {
      login(response.data.accessToken, values.email);
      toast.success("Welcome back to Vyapar Sathi.");
      navigate("/dashboard");
    },
    onError: (error) => toast.error(error.response?.data?.detail || "Login failed."),
  });

  const signupMutation = useMutation({
    mutationFn: (values) => authApi.register(values),
    onSuccess: () => {
      toast.success("Account created. You can log in now.");
      setMode("login");
      signupForm.reset();
    },
    onError: (error) => toast.error(error.response?.data?.detail || "Could not create your account."),
  });


  return (
    <div className="min-h-screen bg-slateDeep px-4 py-6 text-white md:px-10">
      <div className="mx-auto grid min-h-[calc(100vh-3rem)] max-w-7xl overflow-hidden rounded-[2rem] border border-white/10 bg-white/5 shadow-glow backdrop-blur-xl lg:grid-cols-[1.15fr_0.85fr]">
        <section className="relative overflow-hidden p-8 md:p-12">
          <div className="absolute inset-0 bg-hero-grid opacity-90" />
          <div className="relative z-10">
            <motion.p initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }} className="text-sm uppercase tracking-[0.35em] text-emerald-300">
              Trusted by small businesses
            </motion.p>
            <motion.h1
              initial={{ opacity: 0, y: 18 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.08 }}
              className="mt-4 max-w-xl font-display text-4xl font-extrabold leading-tight md:text-6xl"
            >
              Vyapar Sathi
              <span className="block text-2xl text-amber-200 md:text-4xl">Aapka Smart Business Diary</span>
            </motion.h1>
            <motion.p
              initial={{ opacity: 0, y: 18 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.16 }}
              className="mt-6 max-w-xl text-lg text-slate-200"
            >
              Track day-to-day money flow, scan bills, and ask finance questions in English without dealing with complicated accounting tools.
            </motion.p>

            <div className="mt-10 grid gap-4 md:grid-cols-3">
              {[
                { icon: Landmark, title: "Track Transactions", text: "Income, expenses, GST, and daily business entries in one place." },
                { icon: Upload, title: "Scan Bills with OCR", text: "Upload invoices and turn them into structured entries faster." },
                { icon: Bot, title: "Ask Finance Questions", text: "Get instant answers about sales, expenses, GST, and profit." },
              ].map(({ icon: Icon, title, text }, index) => (
                <motion.div
                  key={title}
                  initial={{ opacity: 0, y: 30 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.22 + index * 0.08 }}
                  className="rounded-2xl border border-white/15 bg-white/10 p-4 backdrop-blur-xl"
                >
                  <Icon className="h-6 w-6 text-amber-300" />
                  <p className="mt-3 font-semibold">{title}</p>
                  <p className="mt-2 text-sm text-slate-200">{text}</p>
                </motion.div>
              ))}
            </div>

            <div className="mt-10 flex flex-wrap gap-3">
              <TrustPill icon={ShieldCheck} label="Private & Secure" />
              <TrustPill icon={Sparkles} label="Built for Indian Businesses" />
              <TrustPill icon={Bot} label="No CA needed" />
            </div>

            <div className="relative mt-14 hidden h-56 lg:block">
              <FloatingBubble className="left-0 top-8 w-52" label="Sale received ₹12,500 from Client ABC" />
              <FloatingBubble className="left-52 top-0 w-48" label="GST this month: ₹8,240" />
              <FloatingBubble className="left-28 top-28 w-60" label="Rent is your top expense this month" assistant />
            </div>
          </div>
        </section>

        <section className="bg-ivory px-6 py-8 text-slate-900 dark:bg-slate-950 dark:text-slate-50 md:px-10 md:py-12">
          <div className="mx-auto max-w-md">
            <p className="text-sm uppercase tracking-[0.28em] text-assistant">Start your workspace</p>
            <h2 className="mt-3 font-display text-3xl font-bold">Welcome back</h2>
            <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">Use your email to sign in or create a new business account.</p>

            <div className="mt-8 grid grid-cols-2 rounded-2xl bg-slate-100 p-1 dark:bg-slate-800">
              {["login", "signup"].map((tab) => (
                <button
                  key={tab}
                  type="button"
                  onClick={() => setMode(tab)}
                  className={`rounded-2xl px-4 py-3 text-sm font-semibold transition ${
                    mode === tab ? "bg-white text-slate-900 shadow-soft dark:bg-slate-900 dark:text-slate-50" : "text-slate-500 dark:text-slate-300"
                  }`}
                >
                  {tab === "login" ? "Login" : "Sign up"}
                </button>
              ))}
            </div>

            <Card className="mt-6 bg-white/90 dark:bg-slate-900">
              {mode === "login" ? (
                <form className="space-y-4" onSubmit={loginForm.handleSubmit((values) => loginMutation.mutate(values))}>
                  <Field label="Email" error={loginForm.formState.errors.email?.message}>
                    <Input {...loginForm.register("email")} placeholder="you@business.com" />
                  </Field>
                  <Field label="Password" error={loginForm.formState.errors.password?.message}>
                    <Input type="password" {...loginForm.register("password")} placeholder="••••••••" />
                  </Field>
                  <Button type="submit" className="w-full">
                    {loginMutation.isPending ? "Signing in..." : "Login"}
                  </Button>
                </form>
              ) : (
                <form className="space-y-4" onSubmit={signupForm.handleSubmit((values) => signupMutation.mutate(values))}>
                  <Field label="Full Name" error={signupForm.formState.errors.fullName?.message}>
                    <Input {...signupForm.register("fullName")} placeholder="Anjali Sharma" />
                  </Field>
                  <Field label="Email" error={signupForm.formState.errors.email?.message}>
                    <Input {...signupForm.register("email")} placeholder="you@business.com" />
                  </Field>
                  <Field label="Password" error={signupForm.formState.errors.password?.message}>
                    <Input type="password" {...signupForm.register("password")} placeholder="Minimum 6 characters" />
                  </Field>
                  <Button type="submit" className="w-full">
                    {signupMutation.isPending ? "Creating account..." : "Create account"}
                  </Button>
                </form>
              )}

            </Card>
          </div>
        </section>
      </div>
    </div>
  );
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

function TrustPill({ icon: Icon, label }) {
  return (
    <div className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/10 px-4 py-2 text-sm text-slate-100">
      <Icon className="h-4 w-4 text-income" />
      {label}
    </div>
  );
}

function FloatingBubble({ className, label, assistant = false }) {
  return (
    <motion.div
      animate={{ y: [0, -8, 0] }}
      transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
      className={`absolute rounded-2xl border border-white/15 p-4 text-sm shadow-soft ${
        assistant ? "bg-assistant/20 text-cyan-50" : "bg-white/10 text-white"
      } ${className}`}
    >
      {label}
    </motion.div>
  );
}
