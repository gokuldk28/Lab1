import { motion } from "framer-motion";
import { useCallback, useEffect, useRef, useState } from "react";
import { analyzeExpenses, chatInsights, getUserId } from "../api/client";

export default function Insights({ refreshKey }) {
  const userId = getUserId();
  const [analysis, setAnalysis] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [typing, setTyping] = useState("");
  const [pending, setPending] = useState(false);
  const bottomRef = useRef(null);

  const load = useCallback(async () => {
    const a = await analyzeExpenses(userId);
    setAnalysis(a);
  }, [userId]);

  useEffect(() => {
    load();
  }, [load, refreshKey]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, typing]);

  async function send() {
    const text = input.trim();
    if (!text) return;
    setInput("");
    const userMsg = { role: "user", content: text };
    setMessages((m) => [...m, userMsg]);
    setPending(true);

    const res = await chatInsights(userId, text, messages.map((x) => ({ role: x.role, content: x.content })));
    const full = res.reply || "";
    await typewriter(full);
    setPending(false);
    setTyping("");
    setMessages((m) => [...m, { role: "assistant", content: full, source: res.source }]);
  }

  async function typewriter(full) {
    for (let i = 0; i <= full.length; i += 1) {
      setTyping(full.slice(0, i) + (i < full.length ? "▍" : ""));
      await new Promise((r) => setTimeout(r, 10));
    }
  }

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-6 px-4 py-8 lg:flex-row">
      <motion.aside
        initial={{ opacity: 0, x: -12 }}
        animate={{ opacity: 1, x: 0 }}
        className="glass-panel h-fit w-full shrink-0 p-6 lg:w-80"
      >
        <h2 className="text-lg font-bold text-slate-900">Signals</h2>
        <p className="mt-1 text-xs text-slate-500">From /analyze-expenses</p>
        <ul className="mt-4 space-y-2 text-sm text-slate-700">
          {(analysis?.insights || []).map((t, i) => (
            <motion.li
              key={i}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
              className="rounded-xl bg-white/60 px-3 py-2"
            >
              {t}
            </motion.li>
          ))}
        </ul>
        <h3 className="mt-6 text-sm font-bold text-slate-800">Invest & save</h3>
        <ul className="mt-2 space-y-2 text-sm text-slate-600">
          {(analysis?.investment_tips || []).map((t, i) => (
            <li key={i} className="rounded-xl bg-emerald-50/80 px-3 py-2 text-emerald-900">
              {t}
            </li>
          ))}
        </ul>
      </motion.aside>

      <motion.section
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass-panel flex min-h-[520px] flex-1 flex-col overflow-hidden"
      >
        <div className="border-b border-white/40 px-4 py-3">
          <h2 className="font-bold text-slate-900">AI Assistant</h2>
          <p className="text-xs text-slate-500">Context-aware · OpenAI when key is set</p>
        </div>
        <div className="flex-1 space-y-3 overflow-y-auto px-4 py-4">
          {messages.length === 0 && (
            <p className="text-sm text-slate-500">
              Hey! I’m your financial assistant. Let’s improve your money habits. Ask anything about savings or your
              budget.
            </p>
          )}
          {messages.map((m, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[85%] rounded-2xl px-4 py-2 text-sm shadow-sm ${
                  m.role === "user"
                    ? "bg-gradient-to-br from-indigo-500 to-violet-600 text-white"
                    : "border border-slate-200 bg-white/90 text-slate-800"
                }`}
              >
                {m.content}
                {m.source && (
                  <span className="mt-1 block text-[10px] opacity-70">{m.source === "openai" ? "GPT" : "Rules"}</span>
                )}
              </div>
            </motion.div>
          ))}
          {pending && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex justify-start">
              <div className="max-w-[85%] rounded-2xl border border-slate-200 bg-white/90 px-4 py-2 text-sm text-slate-800">
                {typing ? (
                  typing
                ) : (
                  <span className="flex items-center gap-1 text-slate-500">
                    <span className="inline-block h-2 w-2 animate-bounce rounded-full bg-indigo-500 [animation-delay:-0.2s]" />
                    <span className="inline-block h-2 w-2 animate-bounce rounded-full bg-indigo-500 [animation-delay:-0.1s]" />
                    <span className="inline-block h-2 w-2 animate-bounce rounded-full bg-indigo-500" />
                    Thinking…
                  </span>
                )}
              </div>
            </motion.div>
          )}
          <div ref={bottomRef} />
        </div>
        <div className="border-t border-white/40 bg-white/40 p-3 backdrop-blur-md">
          <div className="flex gap-2">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && send()}
              placeholder="Ask for savings tips, budget status, or SIP ideas…"
              className="flex-1 rounded-2xl border border-slate-200 bg-white/90 px-4 py-3 text-sm outline-none ring-indigo-500/25 focus:ring-4"
            />
            <motion.button
              type="button"
              whileHover={{ scale: 1.03 }}
              whileTap={{ scale: 0.95 }}
              onClick={send}
              disabled={pending}
              className="rounded-2xl bg-slate-900 px-5 text-sm font-semibold text-white shadow-lg disabled:opacity-50"
            >
              Send
            </motion.button>
          </div>
        </div>
      </motion.section>
    </div>
  );
}
