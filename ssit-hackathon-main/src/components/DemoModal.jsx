import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useRef, useState } from "react";

const STEPS = [
  {
    title: "Login securely",
    caption: "Login securely using OTP — your session stays private.",
  },
  {
    title: "Import bank data",
    caption: "Import bank transactions in one click (simulated API).",
  },
  {
    title: "Watch spending update",
    caption: "Watch your spending and charts update instantly.",
  },
  {
    title: "Real-time alerts",
    caption: "Get real-time alerts before you overspend.",
  },
  {
    title: "Ask the AI assistant",
    caption: "Ask FinSight AI for smart, contextual money advice.",
  },
];

// Optional: set DEMO_VIDEO_URL in .env as Vite public
const DEMO_VIDEO =
  (typeof import.meta !== "undefined" && import.meta.env?.VITE_DEMO_VIDEO_URL) || "";

export default function DemoModal({ open, onClose }) {
  const [mode, setMode] = useState(DEMO_VIDEO ? "video" : "walkthrough");
  const [step, setStep] = useState(0);
  const videoRef = useRef(null);

  useEffect(() => {
    if (!open) setStep(0);
  }, [open]);

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="fixed inset-0 z-50 flex items-center justify-center p-4"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
        >
          <motion.button
            type="button"
            aria-label="Close demo"
            className="absolute inset-0 bg-slate-900/45 backdrop-blur-md"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
          />
          <motion.div
            role="dialog"
            aria-modal="true"
            initial={{ opacity: 0, scale: 0.94, y: 16 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: 12 }}
            transition={{ type: "spring", damping: 26, stiffness: 320 }}
            className="relative z-10 w-full max-w-3xl overflow-hidden rounded-3xl border border-white/50 bg-white/75 shadow-2xl shadow-indigo-500/10 backdrop-blur-2xl"
          >
            <div className="flex items-center justify-between border-b border-white/40 px-6 py-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-widest text-indigo-600">Cinematic demo</p>
                <h2 className="text-lg font-bold text-slate-900">Product tour — under 2 minutes</h2>
              </div>
              <div className="flex gap-2">
                {DEMO_VIDEO && (
                  <button
                    type="button"
                    onClick={() => setMode("video")}
                    className={`rounded-full px-3 py-1 text-xs font-semibold ${
                      mode === "video" ? "bg-indigo-600 text-white" : "bg-white/70 text-slate-600"
                    }`}
                  >
                    Video
                  </button>
                )}
                <button
                  type="button"
                  onClick={() => setMode("walkthrough")}
                  className={`rounded-full px-3 py-1 text-xs font-semibold ${
                    mode === "walkthrough" ? "bg-indigo-600 text-white" : "bg-white/70 text-slate-600"
                  }`}
                >
                  Guided
                </button>
                <button
                  type="button"
                  onClick={onClose}
                  className="rounded-full bg-white/70 px-3 py-1 text-xs font-semibold text-slate-600 hover:bg-white"
                >
                  Close
                </button>
              </div>
            </div>

            <div className="p-6">
              {mode === "video" && DEMO_VIDEO ? (
                <motion.video
                  ref={videoRef}
                  key={DEMO_VIDEO}
                  className="w-full rounded-2xl shadow-card ring-1 ring-black/5"
                  controls
                  autoPlay
                  muted
                  playsInline
                  src={DEMO_VIDEO}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                />
              ) : (
                <div className="space-y-6">
                  <div className="relative overflow-hidden rounded-2xl border border-indigo-200/60 bg-gradient-to-br from-indigo-50 to-white p-6">
                    <motion.div
                      className="absolute inset-0 opacity-40"
                      animate={{ backgroundPosition: ["0% 50%", "100% 50%", "0% 50%"] }}
                      transition={{ duration: 10, repeat: Infinity }}
                      style={{
                        backgroundImage: "linear-gradient(120deg, #6366f1, #a855f7, #22d3ee)",
                        backgroundSize: "200% 200%",
                      }}
                    />
                    <div className="relative">
                      <p className="text-sm font-medium text-indigo-900">
                        Step {step + 1} of {STEPS.length}
                      </p>
                      <h3 className="mt-1 text-2xl font-bold text-slate-900">{STEPS[step].title}</h3>
                      <p className="mt-2 max-w-xl text-slate-600">{STEPS[step].caption}</p>
                      <motion.div
                        key={step}
                        initial={{ opacity: 0, x: 16 }}
                        animate={{ opacity: 1, x: 0 }}
                        className="mt-4 rounded-xl border border-indigo-100 bg-white/80 p-4 shadow-inner"
                      >
                        <div className="flex gap-3">
                          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-indigo-100 text-indigo-700">
                            {step + 1}
                          </span>
                          <div className="flex-1 space-y-2">
                            <div className="h-3 w-3/4 max-w-[75%] rounded bg-slate-200" />
                            <div className="h-3 w-1/2 max-w-[50%] rounded bg-slate-100" />
                            <div className="h-24 rounded-lg bg-gradient-to-r from-indigo-100 via-violet-100 to-cyan-100" />
                          </div>
                        </div>
                      </motion.div>
                    </div>
                  </div>
                  <div className="flex justify-between gap-3">
                    <button
                      type="button"
                      disabled={step === 0}
                      onClick={() => setStep((s) => Math.max(0, s - 1))}
                      className="rounded-full border border-slate-200 bg-white/80 px-4 py-2 text-sm font-semibold text-slate-700 disabled:opacity-40"
                    >
                      Back
                    </button>
                    <div className="flex gap-2">
                      {STEPS.map((_, i) => (
                        <span
                          key={i}
                          className={`h-2 w-2 rounded-full ${i === step ? "bg-indigo-600" : "bg-slate-300"}`}
                        />
                      ))}
                    </div>
                    {step < STEPS.length - 1 ? (
                      <motion.button
                        type="button"
                        whileTap={{ scale: 0.97 }}
                        onClick={() => setStep((s) => Math.min(STEPS.length - 1, s + 1))}
                        className="rounded-full bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-lg shadow-indigo-500/25"
                      >
                        Next
                      </motion.button>
                    ) : (
                      <motion.button
                        type="button"
                        whileTap={{ scale: 0.97 }}
                        onClick={onClose}
                        className="rounded-full bg-emerald-600 px-4 py-2 text-sm font-semibold text-white shadow-lg shadow-emerald-500/25"
                      >
                        Start using FinSight
                      </motion.button>
                    )}
                  </div>
                  {!DEMO_VIDEO && (
                    <p className="text-center text-xs text-slate-500">
                      Tip: set <code className="rounded bg-slate-100 px-1">VITE_DEMO_VIDEO_URL</code> for a real demo clip.
                    </p>
                  )}
                </div>
              )}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
