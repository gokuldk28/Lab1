import { motion } from "framer-motion";
import { Link, useLocation } from "react-router-dom";

const links = [
  { to: "/", label: "Dashboard" },
  { to: "/transactions", label: "Transactions" },
  { to: "/insights", label: "AI Insights" },
];

export default function Navbar({ onTryDemo }) {
  const loc = useLocation();
  return (
    <motion.header
      initial={{ opacity: 0, y: -12 }}
      animate={{ opacity: 1, y: 0 }}
      className="sticky top-0 z-40 border-b border-white/30 bg-white/40 backdrop-blur-xl"
    >
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3">
        <Link to="/" className="flex items-center gap-2">
          <span className="grid h-9 w-9 place-items-center rounded-xl bg-gradient-to-br from-indigo-500 to-violet-500 text-lg text-white shadow-lg">
            ✦
          </span>
          <div>
            <p className="text-sm font-bold text-slate-900">FinSight AI</p>
            <p className="text-xs text-slate-500">Premium finance intelligence</p>
          </div>
        </Link>

        <nav className="hidden items-center gap-1 md:flex">
          {links.map(({ to, label }) => {
            const active = loc.pathname === to;
            return (
              <Link key={to} to={to}>
                <motion.span
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  className={`block rounded-full px-3 py-1.5 text-sm font-medium transition ${
                    active
                      ? "bg-white/80 text-indigo-700 shadow-sm"
                      : "text-slate-600 hover:bg-white/50"
                  }`}
                >
                  {label}
                </motion.span>
              </Link>
            );
          })}
        </nav>

        <motion.button
          type="button"
          whileHover={{ scale: 1.03 }}
          whileTap={{ scale: 0.97 }}
          onClick={onTryDemo}
          className="rounded-full bg-gradient-to-r from-indigo-600 to-violet-600 px-4 py-2 text-sm font-semibold text-white shadow-lg shadow-indigo-500/30"
        >
          Try Demo
        </motion.button>
      </div>
    </motion.header>
  );
}
