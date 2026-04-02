import { motion } from "framer-motion";
import { useCallback, useEffect, useState } from "react";
import {
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { analyzeExpenses, getUserId, importBank, predictSpending, updateBudget } from "../api/client";
import { CardSkeleton, ChartSkeleton } from "../components/Skeleton";

const COLORS = ["#6366f1", "#22c55e", "#f59e0b", "#ef4444", "#06b6d4", "#a855f7"];

function formatInr(n) {
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(n);
}

export default function Dashboard({ refreshKey }) {
  const userId = getUserId();
  const [data, setData] = useState(null);
  const [forecast, setForecast] = useState(null);
  const [loading, setLoading] = useState(true);
  const [budgetInput, setBudgetInput] = useState("");
  const [err, setErr] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setErr("");
    try {
      const [a, p] = await Promise.all([analyzeExpenses(userId), predictSpending(userId, 14)]);
      setData(a);
      setForecast(p);
      setBudgetInput(String(a.budget || ""));
    } catch (e) {
      setErr(e?.message || "Could not reach API. Is the backend running?");
    } finally {
      setLoading(false);
    }
  }, [userId]);

  useEffect(() => {
    load();
  }, [load, refreshKey]);

  async function saveBudget() {
    const b = parseFloat(budgetInput);
    if (Number.isNaN(b)) return;
    await updateBudget(userId, b);
    await load();
  }

  async function quickImport() {
    await importBank(userId, 8);
    await load();
  }

  const pieData = data?.by_category?.map((c) => ({ name: c.category, value: c.amount })) || [];
  const lineData = data?.daily_trend || [];
  const fcHist = forecast?.history?.map((h) => ({ date: h.date, actual: h.amount, forecast: null })) || [];
  const fcFuture = forecast?.forecast?.map((f) => ({ date: f.date, actual: null, forecast: f.predicted })) || [];
  const fcMerged = [...fcHist, ...fcFuture].slice(-30);

  const savings = data ? Math.max(0, (data.budget || 0) - (data.month_spend || 0)) : 0;

  return (
    <div className="mx-auto max-w-6xl space-y-8 px-4 py-8">
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass-panel overflow-hidden p-8"
      >
        <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-widest text-indigo-600">Command center</p>
            <h1 className="mt-1 text-3xl font-bold text-slate-900">Your money, beautifully clear.</h1>
            <p className="mt-2 max-w-xl text-slate-600">
              Live analytics powered by FastAPI. Import data, watch charts animate, and stay ahead of spend.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <motion.button
              type="button"
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={quickImport}
              className="rounded-full border border-white/60 bg-white/70 px-4 py-2 text-sm font-semibold text-slate-800 shadow-sm"
            >
              Simulate bank sync
            </motion.button>
            <motion.button
              type="button"
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={load}
              className="rounded-full bg-slate-900 px-4 py-2 text-sm font-semibold text-white shadow-lg"
            >
              Refresh
            </motion.button>
          </div>
        </div>
      </motion.div>

      {err && (
        <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">{err}</div>
      )}

      <div className="grid gap-4 md:grid-cols-3">
        {loading ? (
          <>
            <CardSkeleton />
            <CardSkeleton />
            <CardSkeleton />
          </>
        ) : (
          <>
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.05 }}
              whileHover={{ y: -4, scale: 1.01 }}
              className="glass-panel p-5 shadow-card"
            >
              <p className="text-sm font-medium text-slate-500">Total balance narrative</p>
              <p className="mt-1 text-2xl font-bold text-slate-900">Month spend</p>
              <p className="mt-2 text-3xl font-extrabold tracking-tight text-indigo-700">{formatInr(data.month_spend)}</p>
              <p className="mt-1 text-xs text-slate-500">All-time: {formatInr(data.total_spend)}</p>
            </motion.div>
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              whileHover={{ y: -4, scale: 1.01 }}
              className="glass-panel p-5 shadow-card"
            >
              <p className="text-sm font-medium text-slate-500">Expenses vs budget</p>
              <p className="mt-1 text-2xl font-bold text-slate-900">Utilization</p>
              <p className="mt-2 text-3xl font-extrabold text-amber-600">{data.budget_used_pct?.toFixed(1) ?? 0}%</p>
              <p className="mt-1 text-xs text-slate-500">Remaining {formatInr(data.remaining_budget)}</p>
            </motion.div>
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.15 }}
              whileHover={{ y: -4, scale: 1.01 }}
              className="glass-panel p-5 shadow-card"
            >
              <p className="text-sm font-medium text-slate-500">Savings buffer</p>
              <p className="mt-1 text-2xl font-bold text-slate-900">This month</p>
              <p className="mt-2 text-3xl font-extrabold text-emerald-600">{formatInr(savings)}</p>
              <p className="mt-1 text-xs text-slate-500">Health score {data.health_score}/100</p>
            </motion.div>
          </>
        )}
      </div>

      <div className="glass-panel p-4 md:p-6">
        <p className="text-sm font-semibold text-slate-800">Monthly budget</p>
        <div className="mt-3 flex flex-wrap items-end gap-3">
          <input
            value={budgetInput}
            onChange={(e) => setBudgetInput(e.target.value)}
            className="w-48 rounded-xl border border-slate-200 bg-white/80 px-3 py-2 text-sm shadow-inner outline-none ring-indigo-500/30 transition focus:ring-4"
            placeholder="12000"
          />
          <motion.button
            type="button"
            whileTap={{ scale: 0.98 }}
            onClick={saveBudget}
            className="rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-md"
          >
            Save budget
          </motion.button>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {loading ? (
          <>
            <ChartSkeleton />
            <ChartSkeleton />
          </>
        ) : (
          <>
            <motion.div
              initial={{ opacity: 0, scale: 0.98 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.35 }}
              className="glass-panel p-4"
            >
              <h3 className="mb-2 text-sm font-bold text-slate-800">Category split</h3>
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={pieData} dataKey="value" nameKey="name" innerRadius={56} outerRadius={88} paddingAngle={2}>
                      {pieData.map((_, i) => (
                        <Cell key={i} fill={COLORS[i % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip formatter={(v) => formatInr(v)} />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </motion.div>
            <motion.div
              initial={{ opacity: 0, scale: 0.98 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.35, delay: 0.05 }}
              className="glass-panel p-4"
            >
              <h3 className="mb-2 text-sm font-bold text-slate-800">Spending trend</h3>
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={lineData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                    <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                    <YAxis tick={{ fontSize: 11 }} />
                    <Tooltip formatter={(v) => formatInr(v)} />
                    <Line type="monotone" dataKey="amount" stroke="#6366f1" strokeWidth={3} dot={{ r: 3 }} isAnimationActive />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </motion.div>
          </>
        )}
      </div>

      {!loading && forecast && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass-panel p-4"
        >
          <h3 className="mb-2 text-sm font-bold text-slate-800">Forecast ({forecast.method})</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={fcMerged}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="date" tick={{ fontSize: 10 }} />
                <YAxis tick={{ fontSize: 10 }} />
                <Tooltip formatter={(v) => (v != null ? formatInr(v) : "")} />
                <Line type="monotone" dataKey="actual" stroke="#22c55e" strokeWidth={2} dot={false} isAnimationActive />
                <Line type="monotone" dataKey="forecast" stroke="#a855f7" strokeWidth={2} dot={false} strokeDasharray="4 4" isAnimationActive />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </motion.div>
      )}

      {!loading && data?.alerts?.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-sm font-bold text-slate-800">Budget signals</h3>
          <div className="grid gap-2 md:grid-cols-2">
            {data.alerts.map((a, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.05 }}
                className="rounded-2xl border border-amber-100 bg-amber-50/80 px-4 py-3 text-sm text-amber-900"
              >
                <span className="font-semibold">{a.threshold_pct}%</span> · {a.message}
              </motion.div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
