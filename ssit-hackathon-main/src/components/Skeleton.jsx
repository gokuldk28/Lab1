import { motion } from "framer-motion";

export function CardSkeleton() {
  return (
    <div className="glass-panel h-28 animate-pulse overflow-hidden p-4">
      <div className="mb-3 h-3 w-24 rounded-full bg-slate-200/80" />
      <div className="h-8 w-40 rounded-lg bg-slate-200/80" />
    </div>
  );
}

export function ChartSkeleton() {
  return (
    <motion.div
      initial={{ opacity: 0.6 }}
      animate={{ opacity: [0.6, 1, 0.6] }}
      transition={{ duration: 1.6, repeat: Infinity }}
      className="glass-panel h-80 p-4"
    >
      <div className="mb-4 h-4 w-32 rounded bg-slate-200/80" />
      <div className="flex h-56 items-end gap-2 px-2">
        {[40, 65, 35, 80, 50, 70, 45].map((h, i) => (
          <div key={i} className="flex-1 rounded-t-md bg-gradient-to-t from-indigo-200 to-violet-200" style={{ height: `${h}%` }} />
        ))}
      </div>
    </motion.div>
  );
}
