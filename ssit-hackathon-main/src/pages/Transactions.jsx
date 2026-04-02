import { motion, useScroll, useSpring } from "framer-motion";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { addTransaction, getTransactions, getUserId } from "../api/client";

const CATEGORIES = ["Food", "Transport", "Shopping", "Bills", "Others"];

export default function Transactions({ refreshKey, onDataChange }) {
  const userId = getUserId();
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const scrollRef = useRef(null);
  const { scrollYProgress } = useScroll({ container: scrollRef });
  const scaleX = useSpring(scrollYProgress, { stiffness: 120, damping: 28 });

  const load = useCallback(async () => {
    setLoading(true);
    const data = await getTransactions(userId);
    setRows(data.transactions || []);
    setLoading(false);
  }, [userId]);

  useEffect(() => {
    load();
  }, [load, refreshKey]);

  const sorted = useMemo(
    () => [...rows].sort((a, b) => String(b.date).localeCompare(String(a.date))),
    [rows]
  );

  const [form, setForm] = useState({
    date: new Date().toISOString().slice(0, 10),
    merchant: "",
    amount: "",
    category: "Food",
  });

  async function submit(e) {
    e.preventDefault();
    const amount = parseFloat(form.amount);
    if (!form.merchant || Number.isNaN(amount)) return;
    await addTransaction({
      user_id: userId,
      date: form.date,
      merchant: form.merchant,
      amount,
      category: form.category,
      source: "manual",
    });
    setForm({ ...form, merchant: "", amount: "" });
    await load();
    onDataChange?.();
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6 px-4 py-8">
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="glass-panel p-6">
        <h1 className="text-2xl font-bold text-slate-900">Transactions</h1>
        <p className="mt-1 text-slate-600">Scroll the list — entries animate in as you explore.</p>
        <motion.div className="mt-3 h-1 origin-left rounded-full bg-gradient-to-r from-indigo-500 to-purple-500" style={{ scaleX }} />
      </motion.div>

      <form onSubmit={submit} className="glass-panel grid gap-4 p-6 md:grid-cols-2">
        <input
          type="date"
          value={form.date}
          onChange={(e) => setForm({ ...form, date: e.target.value })}
          className="rounded-xl border border-slate-200 bg-white/90 px-3 py-2 text-sm outline-none ring-indigo-500/25 focus:ring-4"
        />
        <input
          placeholder="Merchant"
          value={form.merchant}
          onChange={(e) => setForm({ ...form, merchant: e.target.value })}
          className="rounded-xl border border-slate-200 bg-white/90 px-3 py-2 text-sm outline-none ring-indigo-500/25 focus:ring-4"
        />
        <input
          placeholder="Amount"
          type="number"
          step="0.01"
          value={form.amount}
          onChange={(e) => setForm({ ...form, amount: e.target.value })}
          className="rounded-xl border border-slate-200 bg-white/90 px-3 py-2 text-sm outline-none ring-indigo-500/25 focus:ring-4"
        />
        <select
          value={form.category}
          onChange={(e) => setForm({ ...form, category: e.target.value })}
          className="rounded-xl border border-slate-200 bg-white/90 px-3 py-2 text-sm outline-none ring-indigo-500/25 focus:ring-4"
        >
          {CATEGORIES.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
        <div className="md:col-span-2">
          <motion.button
            type="submit"
            whileHover={{ scale: 1.01 }}
            whileTap={{ scale: 0.98 }}
            className="w-full rounded-xl bg-indigo-600 py-2.5 text-sm font-semibold text-white shadow-lg shadow-indigo-500/25"
          >
            Add transaction
          </motion.button>
        </div>
      </form>

      <div
        ref={scrollRef}
        className="glass-panel max-h-[520px] overflow-y-auto p-2"
      >
        {loading ? (
          <p className="p-4 text-sm text-slate-500">Loading…</p>
        ) : sorted.length === 0 ? (
          <p className="p-4 text-sm text-slate-500">No transactions yet. Add one above.</p>
        ) : (
          <ul className="space-y-2 p-2">
            {sorted.map((r, i) => (
              <motion.li
                key={`${r.date}-${r.merchant}-${r.amount}-${i}`}
                initial={{ opacity: 0, y: 12 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-40px" }}
                transition={{ delay: (i % 8) * 0.04 }}
                whileHover={{ scale: 1.01 }}
                className="flex items-center justify-between rounded-2xl border border-white/50 bg-white/70 px-4 py-3 shadow-sm"
              >
                <div>
                  <p className="font-semibold text-slate-900">{r.merchant}</p>
                  <p className="text-xs text-slate-500">
                    {r.date} · {r.category} · {r.source}
                  </p>
                </div>
                <p className="text-sm font-bold text-indigo-700">
                  {new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR" }).format(r.amount)}
                </p>
              </motion.li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
