from __future__ import annotations

import hashlib
import html
import json
import os
import random
import urllib.error
import urllib.request
from time import sleep
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st
import streamlit.components.v1 as components

APP_NAME = "FinSight AI"
CURRENCY = "INR "
CATEGORIES = ["Food", "Transport", "Shopping", "Bills", "Others"]
DATA_FILE = Path(__file__).resolve().parent / "data" / "users_data.json"


def ensure_store() -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not DATA_FILE.exists():
        DATA_FILE.write_text(json.dumps({"users": {}}, indent=2), encoding="utf-8")


def load_store() -> dict[str, Any]:
    ensure_store()
    return json.loads(DATA_FILE.read_text(encoding="utf-8"))


def save_store(store: dict[str, Any]) -> None:
    DATA_FILE.write_text(json.dumps(store, indent=2), encoding="utf-8")


def money(v: float) -> str:
    return f"{CURRENCY}{v:,.2f}"


def month_filter(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    now = date.today()
    d = pd.to_datetime(df["date"], errors="coerce")
    return df[(d.dt.year == now.year) & (d.dt.month == now.month)].copy()


def to_df(expenses: list[dict[str, Any]]) -> pd.DataFrame:
    if not expenses:
        return pd.DataFrame(columns=["date", "merchant", "amount", "category", "source"])
    df = pd.DataFrame(expenses)
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date.astype(str)
    return df


def fake_bank_transactions(mobile: str, n: int = 10) -> list[dict[str, Any]]:
    seed = int(hashlib.sha256(f"{mobile}-{date.today().isoformat()}".encode()).hexdigest()[:8], 16)
    rng = random.Random(seed)
    merchants = [
        ("Swiggy", "Food"),
        ("Uber", "Transport"),
        ("Amazon", "Shopping"),
        ("Electricity Board", "Bills"),
        ("BigBasket", "Food"),
        ("Metro Card", "Transport"),
        ("Myntra", "Shopping"),
        ("Airtel", "Bills"),
    ]
    out: list[dict[str, Any]] = []
    for i in range(n):
        merchant, cat = rng.choice(merchants)
        amount = round(rng.uniform(120, 2200), 2)
        d = (date.today() - timedelta(days=rng.randint(0, 21))).isoformat()
        out.append(
            {
                "txn_id": f"tx_{seed % 10000}_{i+1}",
                "date": d,
                "merchant": merchant,
                "amount": amount,
                "category": cat,
                "source": "bank_api",
            }
        )
    return out


def calc_health_score(df: pd.DataFrame, budget: float) -> int:
    if df.empty:
        return 75
    mdf = month_filter(df)
    monthly_spend = float(mdf["amount"].sum()) if not mdf.empty else 0.0

    ratio_score = 25
    if budget > 0:
        ratio = monthly_spend / budget
        if ratio <= 0.5:
            ratio_score = 35
        elif ratio <= 0.8:
            ratio_score = 28
        elif ratio <= 1.0:
            ratio_score = 18
        else:
            ratio_score = 8

    daily = mdf.groupby("date", as_index=False)["amount"].sum() if not mdf.empty else pd.DataFrame()
    consistency_score = 20
    if not daily.empty and len(daily) > 2:
        avg = float(daily["amount"].mean()) or 1.0
        std = float(daily["amount"].std() or 0.0)
        cv = std / avg
        consistency_score = max(8, int(30 - cv * 18))

    anomaly_penalty = 0
    if not daily.empty and len(daily) > 3:
        threshold = float(daily["amount"].mean()) + 2 * float(daily["amount"].std() or 0.0)
        spikes = int((daily["amount"] > threshold).sum())
        anomaly_penalty = min(20, spikes * 5)

    base = ratio_score + consistency_score + 35
    return max(1, min(100, int(base - anomaly_penalty)))


def budget_alerts(spend: float, budget: float) -> list[tuple[float, str, str]]:
    if budget <= 0:
        return []
    used = (spend / budget) * 100.0
    checks = [
        (95, "error", "Danger: Budget nearly finished"),
        (90, "error", "Critical: Almost exhausted"),
        (75, "warning", "Warning: High spending"),
        (50, "info", "Halfway there!"),
        (25, "success", "You've used 25% of your budget"),
    ]
    return [c for c in checks if used >= c[0]]


def budget_message(used_pct: float) -> tuple[str, str]:
    if used_pct >= 95:
        return ("🚨", "**Danger! You may overspend — take action NOW**")
    if used_pct >= 90:
        return ("🔴", "**Critical: Budget almost exhausted**")
    if used_pct >= 75:
        return ("🟠", "**Warning: Spending is increasing fast**")
    if used_pct >= 50:
        return ("🟡", "**Half your budget used — stay mindful**")
    if used_pct >= 25:
        return ("🟢", "**Good start! You're in control**")
    return ("🟢", "**Great discipline so far — keep going!**")


def ai_system_prompt() -> str:
    return (
        "You are FinSight AI, a highly reliable personal finance copilot.\n\n"
        "Core priorities:\n"
        "- Correctness over creativity: never invent numbers, dates, policies, or user-specific facts. "
        "Only use figures and patterns explicitly given in the financial context or the conversation.\n"
        "- Before writing the user-visible reply, reason step-by-step internally (do not show that chain-of-thought). "
        "Then produce one clear, verified final answer.\n"
        "- If information is missing or uncertain, state assumptions plainly and say what you would need to know; "
        "do not guess.\n"
        "- Avoid hallucinations: no fabricated transactions, institutions, rates, or regulations.\n"
        "- Structure: short direct answer first when possible, then logical explanation. Use bullet points when they "
        "aid clarity; add brief examples only when they reduce ambiguity. Avoid generic filler and vague phrases "
        '("as you know", "it depends on many factors" without specifics).\n'
        "- Financial guidance: practical, realistic, and conservative. Not legal, tax, or investment advice; "
        "suggest consulting a qualified professional for binding decisions. Use INR naturally.\n"
        "- Personalize when the provided context supports it (budget, month spend, categories); otherwise keep "
        "general guidance clearly labeled as general.\n"
        "- Keep answers focused: complete but not unnecessarily long.\n"
    )


def _openai_chat_completion(
    api_key: str,
    model: str,
    messages: list[dict[str, str]],
    *,
    temperature: float,
    max_tokens: int,
    timeout: int = 90,
) -> str | None:
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            body = json.loads(res.read().decode("utf-8"))
        return body["choices"][0]["message"]["content"].strip()
    except (urllib.error.URLError, urllib.error.HTTPError, KeyError, IndexError, json.JSONDecodeError):
        return None


def _validator_system_prompt() -> str:
    return (
        "You are a strict quality checker for FinSight AI answers.\n"
        "Given the user's question, the factual financial context, and a draft answer, produce the final answer "
        "the user should see.\n"
        "Rules:\n"
        "- The answer must directly address the question; remove tangents.\n"
        "- Remove internal contradictions and vague filler.\n"
        "- Do not introduce new factual claims beyond the context and well-known general finance principles.\n"
        "- If the draft is already accurate and well-structured, keep it (minor wording polish only).\n"
        "Output ONLY the final user-facing text. No preamble, labels, or meta-commentary."
    )


def validate_assistant_response(
    user_question: str,
    draft: str,
    financial_context: str,
    api_key: str,
    validator_model: str,
) -> str:
    if not draft.strip():
        return draft
    messages = [
        {"role": "system", "content": _validator_system_prompt()},
        {
            "role": "user",
            "content": (
                f"User question:\n{user_question}\n\n"
                f"Financial context (treat as ground truth for this user):\n{financial_context}\n\n"
                f"Draft answer:\n{draft}\n\n"
                "Return only the improved final answer."
            ),
        },
    ]
    refined = _openai_chat_completion(
        api_key,
        validator_model,
        messages,
        temperature=0.25,
        max_tokens=4096,
        timeout=60,
    )
    return refined if refined else draft


def build_financial_context(df: pd.DataFrame, budget: float) -> str:
    total = float(df["amount"].sum()) if not df.empty else 0.0
    month_df = month_filter(df)
    m_spend = float(month_df["amount"].sum()) if not month_df.empty else 0.0
    used = (m_spend / budget * 100.0) if budget > 0 else 0.0
    remain = max(0.0, budget - m_spend) if budget > 0 else 0.0
    lines: list[str] = [
        f"Total spend (all-time in app): {money(total)}",
        f"Current calendar month spend: {money(m_spend)}",
        f"Monthly budget: {money(budget) if budget > 0 else 'Not set'}",
        f"Budget used (this month): {used:.1f}%",
        f"Budget remaining (this month): {money(remain)}",
    ]
    if not month_df.empty:
        lines.append(f"Transaction count (this month): {len(month_df)}")
        by_m = month_df.groupby("category", as_index=False)["amount"].sum().sort_values("amount", ascending=False)
        cat_rows = [f"  - {r['category']}: {money(float(r['amount']))}" for _, r in by_m.iterrows()]
        lines.append("Current month spending by category:\n" + "\n".join(cat_rows))
        pct_parts: list[str] = []
        for _, r in by_m.iterrows():
            p = (float(r["amount"]) / m_spend * 100.0) if m_spend > 0 else 0.0
            pct_parts.append(f"{r['category']}={p:.1f}%")
        lines.append("Category share of this month's spend: " + ", ".join(pct_parts))
    if df.empty:
        lines.append("All-time top categories: N/A (no expenses recorded)")
    else:
        by_cat = df.groupby("category", as_index=False)["amount"].sum().sort_values("amount", ascending=False)
        top_line = ", ".join(
            [f"{r['category']}={money(float(r['amount']))}" for _, r in by_cat.head(5).iterrows()]
        )
        lines.append(f"All-time top categories (top 5): {top_line}")
    health = calc_health_score(df, budget)
    lines.append(f"App health score (0-100 heuristic): {health}")
    return "\n".join(lines) + "\n"


def ask_openai(
    messages: list[dict[str, str]],
    financial_context: str,
    *,
    latest_user_question: str,
) -> str | None:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return None
    model = (os.getenv("OPENAI_MODEL") or "gpt-4.1").strip()
    validator_model = (os.getenv("OPENAI_VALIDATOR_MODEL") or model).strip()
    main_messages: list[dict[str, str]] = [
        {"role": "system", "content": ai_system_prompt()},
        {
            "role": "system",
            "content": (
                "User financial context (use for personalization; do not invent data outside this block):\n"
                f"{financial_context}"
            ),
        },
        *messages,
    ]
    draft = _openai_chat_completion(
        api_key,
        model,
        main_messages,
        temperature=0.5,
        max_tokens=4096,
        timeout=90,
    )
    if not draft:
        return None
    return validate_assistant_response(latest_user_question, draft, financial_context, api_key, validator_model)


def seed_demo_expenses(mobile: str, store: dict[str, Any]) -> int:
    if mobile not in store["users"]:
        return 0
    base = [
        ("Swiggy", "Food", 420.0, 1),
        ("Uber", "Transport", 260.0, 2),
        ("Amazon", "Shopping", 1299.0, 4),
        ("Airtel", "Bills", 799.0, 6),
        ("Cafe", "Food", 180.0, 8),
        ("Metro Card", "Transport", 240.0, 10),
    ]
    existing = {
        f"{e.get('date','')}-{e.get('merchant','')}-{float(e.get('amount',0.0)):.2f}"
        for e in store["users"][mobile].get("expenses", [])
    }
    added = 0
    for merchant, cat, amount, days_back in base:
        dt = (date.today() - timedelta(days=days_back)).isoformat()
        key = f"{dt}-{merchant}-{float(amount):.2f}"
        if key in existing:
            continue
        store["users"][mobile]["expenses"].append(
            {"date": dt, "merchant": merchant, "amount": amount, "category": cat, "source": "demo_seed"}
        )
        added += 1
    return added


def kpi_card_html(label: str, value: float, prefix: str, gradient: str, emoji: str, suffix: str = "") -> str:
    card_id = f"kpi_{abs(hash(label + str(value))) % 1000000}"
    return f"""
<div style="border-radius:14px;padding:14px;min-height:110px;color:white;background:{gradient};box-shadow:0 10px 30px rgba(30,41,59,.20);">
  <div style="font-size:15px;font-weight:700;opacity:.95;">{label} {emoji}</div>
  <div id="{card_id}" data-target="{value:.2f}" data-prefix="{prefix}" data-suffix="{suffix}" style="font-size:30px;font-weight:800;margin-top:6px;">{prefix}0{suffix}</div>
</div>
<script>
(function() {{
  const el = document.getElementById('{card_id}');
  if (!el) return;
  const target = parseFloat(el.dataset.target || '0');
  const prefix = el.dataset.prefix || '';
  const suffix = el.dataset.suffix || '';
  const duration = 900;
  const start = performance.now();
  function fmt(v) {{
    return prefix + v.toLocaleString(undefined, {{maximumFractionDigits:0}}) + suffix;
  }}
  function step(ts) {{
    const p = Math.min(1, (ts - start) / duration);
    const eased = 1 - Math.pow(1 - p, 3);
    const val = target * eased;
    el.textContent = fmt(val);
    if (p < 1) requestAnimationFrame(step);
  }}
  requestAnimationFrame(step);
}})();
</script>
"""


def run_demo_story(user: dict[str, Any], store: dict[str, Any], df: pd.DataFrame) -> None:
    st.markdown("### Demo Story Mode")
    steps = [
        "1. Seed realistic starter expenses",
        "2. Set monthly budget for narrative",
        "3. Import simulated bank transactions",
        "4. Open AI Assistant and ask for optimization plan",
    ]
    st.markdown("<div class='glass reveal'>" + "<br>".join(steps) + "</div>", unsafe_allow_html=True)
    c1, c2 = st.columns([1, 1])
    if c1.button("Start 2-minute Demo", type="primary"):
        mobile = st.session_state.user_mobile
        added = seed_demo_expenses(mobile, store)
        if float(store["users"][mobile].get("budget", 0.0) or 0.0) <= 0:
            store["users"][mobile]["budget"] = 12000.0
        bank = fake_bank_transactions(mobile, n=8)
        existing = {
            f"{e.get('date','')}-{e.get('merchant','')}-{float(e.get('amount',0.0)):.2f}"
            for e in store["users"][mobile].get("expenses", [])
        }
        imported = 0
        for row in bank:
            key = f"{row['date']}-{row['merchant']}-{float(row['amount']):.2f}"
            if key in existing:
                continue
            store["users"][mobile]["expenses"].append(row)
            imported += 1
        save_store(store)
        st.session_state.last_imported_count = imported
        st.session_state.demo_mode = True
        st.success(f"Demo setup done: seeded {added} entries and imported {imported} bank transactions.")
        st.rerun()
    if c2.button("Stop Demo Mode"):
        st.session_state.demo_mode = False
        st.info("Demo mode paused.")


def smart_insights(df: pd.DataFrame) -> list[str]:
    if df.empty:
        return ["Start by adding expenses to unlock insights."]
    insights: list[str] = []
    by_cat = df.groupby("category", as_index=False)["amount"].sum().sort_values("amount", ascending=False)
    total = float(by_cat["amount"].sum()) or 1.0
    top = by_cat.iloc[0]
    if float(top["amount"]) / total > 0.35:
        insights.append(f"Overspending alert: {top['category']} is {float(top['amount'])/total:.0%} of total spend.")
        insights.append(f"Suggestion: Reduce {top['category']} expenses by 15-20% this month.")

    daily = df.groupby("date", as_index=False)["amount"].sum()
    if len(daily) >= 4:
        avg = float(daily["amount"].mean())
        spike_rows = daily[daily["amount"] > (avg * 1.8)]
        if not spike_rows.empty:
            insights.append("Sudden spike detected in daily spending. Review one-time large purchases.")

    sub_keywords = ["netflix", "spotify", "prime", "subscription"]
    desc = " ".join(df["merchant"].astype(str).str.lower().tolist())
    if any(k in desc for k in sub_keywords):
        insights.append("Limit subscriptions and prune unused auto-renew plans.")
    if not insights:
        insights.append("Great control! Your spending pattern looks balanced.")
    return insights[:6]


def investment_tips(df: pd.DataFrame, budget: float) -> list[str]:
    if budget <= 0:
        return ["Set a monthly budget first to get personalized investment suggestions."]
    current = float(month_filter(df)["amount"].sum()) if not df.empty else 0.0
    savings = max(0.0, budget - current)
    if savings < 1000:
        return ["Focus on building an emergency fund first (target 3-6 months expenses)."]
    if savings < 3000:
        return [f"You can put {money(savings)} into a recurring deposit for disciplined saving."]
    if savings < 8000:
        return [
            f"Consider investing {money(savings*0.7)} in SIP and keep {money(savings*0.3)} as emergency cash."
        ]
    return [
        f"Strong surplus! You can invest {money(savings*0.6)} in SIP for long-term growth.",
        f"Allocate {money(savings*0.25)} to emergency fund and {money(savings*0.15)} to fixed deposit."
    ]


def chatbot_answer(prompt: str, df: pd.DataFrame, budget: float) -> str:
    """Offline / API-failure path: data-grounded, coherent guidance (not keyword-only)."""
    q = (prompt or "").lower().strip()
    if not q:
        return (
            "I can help with **budgets**, **spending patterns**, **savings**, and **investing basics** using your "
            "FinSight data. Ask a specific question, for example how much room you have left this month or which "
            "category to trim first."
        )

    month_df = month_filter(df)
    m_spend = float(month_df["amount"].sum()) if not month_df.empty else 0.0
    used_pct = (m_spend / budget * 100.0) if budget > 0 else 0.0
    remain = max(0.0, budget - m_spend) if budget > 0 else 0.0
    health = calc_health_score(df, budget)

    snapshot_lines = [
        "**From your FinSight data (live summary):**",
        f"- This month's spending: **{money(m_spend)}**",
    ]
    if budget > 0:
        snapshot_lines.append(
            f"- Monthly budget: **{money(budget)}** — about **{used_pct:.1f}%** used, **{money(remain)}** remaining."
        )
    else:
        snapshot_lines.append("- Monthly budget: **not set** — set one to track utilization.")
    snapshot_lines.append(f"- App health score (heuristic): **{health}/100**.")
    if not month_df.empty:
        by_m = month_df.groupby("category")["amount"].sum().sort_values(ascending=False)
        top = [f"**{c}** {money(float(by_m[c]))}" for c in by_m.index[:5]]
        snapshot_lines.append("- This month by category: " + ", ".join(top) + ".")
    snapshot = "\n".join(snapshot_lines)

    prefix = (
        "_I could not reach the AI service just now, so this reply is built directly from your recorded data "
        "and standard budgeting logic — not a full language-model answer._\n\n"
    )

    by_cat_all = df.groupby("category")["amount"].sum().sort_values(ascending=False) if not df.empty else pd.Series(dtype=float)
    specific: list[str] = []

    if any(k in q for k in ("save", "saving", "cut", "reduce", "less spend")):
        if not by_cat_all.empty:
            c0, v0 = str(by_cat_all.index[0]), float(by_cat_all.iloc[0])
            specific.append(
                f"Your largest category **overall** is **{c0}** at **{money(v0)}**. Trimming even 10–15% there "
                "frees cash you can park in an emergency buffer or recurring deposit before taking market risk."
            )
        else:
            specific.append(
                "Add a week of expenses so we can see where money goes; then target the largest category first."
            )

    spend_where = ("where" in q and ("money" in q or "spend" in q)) or (
        "going" in q and ("money" in q or "spend" in q)
    )
    if any(k in q for k in ("most", "highest", "largest")) or spend_where:
        if not month_df.empty:
            by_m = month_df.groupby("category")["amount"].sum().sort_values(ascending=False)
            c0, v0 = str(by_m.index[0]), float(by_m.iloc[0])
            specific.append(
                f"This month, **{c0}** is the top category at **{money(v0)}** — that is the fastest place to review "
                "for discretionary cuts."
            )
        elif not by_cat_all.empty:
            c0, v0 = str(by_cat_all.index[0]), float(by_cat_all.iloc[0])
            specific.append(
                f"Across all recorded data, **{c0}** leads at **{money(v0)}**."
            )
        else:
            specific.append("There are not enough transactions yet to rank categories.")

    if "budget" in q:
        if budget <= 0:
            specific.append("Set a realistic monthly budget in FinSight so alerts and percentages stay meaningful.")
        else:
            emoji, msg = budget_message(used_pct)
            specific.append(f"{emoji} {msg}")
            if remain > 0 and used_pct < 100:
                specific.append(
                    f"Simple pacing idea: splitting **{money(remain)}** left across ~4 weeks is about "
                    f"**{money(remain / 4)}** per week (illustrative only)."
                )

    if any(k in q for k in ("invest", "sip", "mutual fund", "fd", "fixed deposit", "stock")):
        for tip in investment_tips(df, budget)[:2]:
            specific.append(tip)

    if not specific:
        specific.append(
            "**Practical next steps:** (1) Keep logging expenses so category splits stay accurate. "
            "(2) If you have a surplus after needs, build a small emergency fund, then consider disciplined SIPs — "
            "this is general education, not personal investment advice."
        )

    body = "\n\n".join(specific)
    return f"{prefix}{snapshot}\n\n{body}"


def typewriter_markdown(text: str, speed: float = 0.012) -> None:
    holder = st.empty()
    rendered = ""
    for ch in text:
        rendered += ch
        holder.markdown(f"<div class='chat-bubble-ai'><b>FinSight AI:</b> {rendered}▌</div>", unsafe_allow_html=True)
        sleep(speed)
    holder.markdown(f"<div class='chat-bubble-ai'><b>FinSight AI:</b> {rendered}</div>", unsafe_allow_html=True)


def render_chat_panel(chat_history: list[tuple[str, str]]) -> None:
    bubbles = []
    for role, msg in chat_history:
        safe = html.escape(str(msg))
        if role == "user":
            bubbles.append(f"<div class='chat-row user'><div class='chat-bubble user msg-in'><b>You</b><br>{safe}</div></div>")
        else:
            bubbles.append(
                f"<div class='chat-row ai'><div class='chat-bubble ai msg-in'><b>FinSight AI</b><br>{safe}</div></div>"
            )
    content = "\n".join(bubbles) if bubbles else "<div class='chat-empty'>Start the conversation.</div>"
    st.markdown(
        f"""
<div id="chat-scroll-panel" class="chat-scroll-panel">
  {content}
</div>
<script>
(() => {{
  const panel = document.getElementById('chat-scroll-panel');
  if (panel) panel.scrollTo({{top: panel.scrollHeight, behavior: 'smooth'}});
}})();
</script>
""",
        unsafe_allow_html=True,
    )


def style():
    st.markdown(
        """
<style>
body { background: #f5f7fb; }
.stApp { background: linear-gradient(120deg, #dbeafe, #eef2ff, #ecfeff, #ede9fe); background-size: 240% 240%; animation: bgShift 14s ease infinite; }
.hero { background: linear-gradient(135deg, #0ea5e9 0%, #6366f1 60%, #a855f7 100%); color: white; border-radius: 16px; padding: 20px; margin-bottom: 16px; }
.card { border-radius: 14px; padding: 14px; color: white; min-height: 110px; box-shadow: 0 10px 30px rgba(30, 41, 59, 0.20); transition: transform 0.35s ease, box-shadow 0.35s ease; }
.card:hover { transform: translateY(-5px) scale(1.02); box-shadow: 0 18px 40px rgba(59, 130, 246, 0.35); }
.stButton > button, .stDownloadButton > button { border-radius: 12px !important; transition: transform 0.22s ease, box-shadow 0.22s ease, filter 0.22s ease !important; box-shadow: 0 6px 20px rgba(99, 102, 241, 0.22) !important; position: relative; overflow: hidden; }
.stButton > button:hover, .stDownloadButton > button:hover { transform: translateY(-2px) scale(1.01); box-shadow: 0 10px 28px rgba(99, 102, 241, 0.32) !important; filter: brightness(1.02); }
.stButton > button:active, .stDownloadButton > button:active { transform: scale(0.99); }
.stButton > button::after, .stDownloadButton > button::after { content: ""; position: absolute; inset: 0; background: radial-gradient(circle, rgba(255,255,255,0.45) 10%, transparent 11%) center/10px 10px; opacity: 0; transition: opacity 0.4s ease; }
.stButton > button:active::after, .stDownloadButton > button:active::after { opacity: 1; transition: 0s; }
.stTextInput > div[data-baseweb="input"] { border-radius: 12px !important; transition: box-shadow .25s ease, border-color .25s ease, transform .2s ease !important; }
.stTextInput > div[data-baseweb="input"]:focus-within { box-shadow: 0 0 0 3px rgba(99,102,241,.18), 0 10px 24px rgba(99,102,241,.16) !important; border-color: #6366f1 !important; transform: translateY(-1px); }
div[data-testid="stTextInput"] label p { transition: transform .2s ease, color .2s ease; }
div[data-testid="stTextInput"]:focus-within label p { transform: translateY(-2px) scale(.98); color: #4f46e5 !important; }
.c1 { background: linear-gradient(135deg, #06b6d4, #3b82f6); } .c2 { background: linear-gradient(135deg, #22c55e, #16a34a); } .c3 { background: linear-gradient(135deg, #f59e0b, #ef4444); }
.glass { background: rgba(255,255,255,.35); backdrop-filter: blur(8px); border: 1px solid rgba(255,255,255,.45); border-radius: 16px; padding: 14px 16px; box-shadow: 0 10px 30px rgba(30,41,59,.12); }
.fade-in { animation: fadeIn .6s ease both; } .reveal { opacity: 0; transform: translateY(20px); transition: opacity .7s ease, transform .7s ease; } .reveal.visible { opacity:1; transform:translateY(0); }
.alert-box { border-radius: 12px; padding: 10px 14px; margin-bottom: 8px; color: #0f172a; border-left: 6px solid rgba(15,23,42,.4); animation: pulseGlow 1.4s ease-in-out 1; font-weight: 600; }
.alert-green { background:#dcfce7; border-left-color:#16a34a; } .alert-yellow { background:#fef9c3; border-left-color:#ca8a04; } .alert-orange { background:#ffedd5; border-left-color:#ea580c; } .alert-red { background:#fee2e2; border-left-color:#dc2626; }
.budget-shell { background: rgba(255,255,255,.6); border-radius: 14px; padding: 10px 12px; border: 1px solid rgba(148,163,184,.4); }
.budget-fill { height: 14px; border-radius: 999px; background: linear-gradient(90deg,#22c55e 0%,#eab308 55%,#f97316 78%,#ef4444 100%); box-shadow: 0 4px 16px rgba(239,68,68,.25); transition: width .8s ease; }
.budget-fill-danger { animation: dangerFlash .95s linear infinite; }
.typing-dot { display:inline-block; width:6px; height:6px; border-radius:50%; background:#6366f1; margin-right:4px; animation:blink 1s infinite; }
.login-wrap { min-height: 70vh; display:flex; align-items:center; justify-content:center; }
.login-card { width:min(560px,94%); background:rgba(255,255,255,.45); backdrop-filter:blur(10px); border:1px solid rgba(255,255,255,.55); border-radius:18px; box-shadow:0 20px 45px rgba(30,41,59,.18); padding:20px; }
.login-card.shake { animation: shakeX .28s linear 1; }
.otp-success { background:rgba(34,197,94,.12); border:1px solid rgba(34,197,94,.35); color:#14532d; border-radius:12px; padding:10px 12px; animation: popIn .35s ease both; }
.otp-error { background:rgba(239,68,68,.12); border:1px solid rgba(239,68,68,.35); color:#7f1d1d; border-radius:12px; padding:10px 12px; animation: popIn .28s ease both; }
.chart-wrap { background: rgba(255,255,255,.56); border:1px solid rgba(255,255,255,.5); border-radius:14px; padding:8px; box-shadow:0 10px 24px rgba(30,41,59,.10);}
.chat-scroll-panel { height:56vh; overflow-y:auto; padding:10px; border-radius:16px; border:1px solid rgba(148,163,184,.28); background:rgba(255,255,255,.42); backdrop-filter:blur(8px); box-shadow: inset 0 1px 0 rgba(255,255,255,.65), 0 8px 20px rgba(15,23,42,.08); }
.chat-row { display:flex; margin-bottom:8px; } .chat-row.user { justify-content:flex-end; } .chat-row.ai { justify-content:flex-start; }
.chat-bubble { max-width:82%; border-radius:14px; padding:10px 12px; line-height:1.35; }
.chat-bubble.user { background:linear-gradient(135deg,#dbeafe,#bfdbfe); border:1px solid #93c5fd; }
.chat-bubble.ai { background:rgba(255,255,255,.82); border:1px solid #cbd5e1; }
.msg-in { animation: msgIn .28s cubic-bezier(.2,.8,.2,1) both; }
@keyframes fadeIn { from { opacity:0; transform:translateY(8px);} to { opacity:1; transform:translateY(0);} }
@keyframes msgIn { from { opacity:0; transform:translateY(8px);} to { opacity:1; transform:translateY(0);} }
@keyframes pulseGlow { 0% { box-shadow:0 0 0 rgba(59,130,246,0);} 40% { box-shadow:0 0 18px rgba(59,130,246,.25);} 100% { box-shadow:0 0 0 rgba(59,130,246,0);} }
@keyframes bgShift { 0% {background-position:0% 50%;} 50% {background-position:100% 50%;} 100% {background-position:0% 50%;} }
@keyframes dangerFlash { 0% {filter:brightness(1);} 50% {filter:brightness(1.35);} 100% {filter:brightness(1);} }
@keyframes blink { 0% {opacity:.2;} 50% {opacity:1;} 100% {opacity:.2;} }
@keyframes shakeX { 0% {transform:translateX(0);} 25% {transform:translateX(-4px);} 50% {transform:translateX(4px);} 75% {transform:translateX(-3px);} 100% {transform:translateX(0);} }
@keyframes popIn { from {opacity:0; transform:translateY(6px) scale(.98);} to {opacity:1; transform:translateY(0) scale(1);} }
</style>
<script>
document.addEventListener('DOMContentLoaded', function() {
  const obs = new IntersectionObserver((entries) => {
    entries.forEach((entry) => { if (entry.isIntersecting) { entry.target.classList.add('visible'); } });
  }, {threshold: 0.12});
  document.querySelectorAll('.reveal').forEach((el) => obs.observe(el));
});
</script>
        """,
        unsafe_allow_html=True,
    )


def login_page() -> None:
    style()
    login_card_class = "login-card fade-in"
    if st.session_state.get("login_error_fx", False):
        login_card_class += " shake"
        st.session_state.login_error_fx = False
    st.markdown(f"<div class='login-wrap'><div class='{login_card_class}'>", unsafe_allow_html=True)
    st.markdown("## Welcome to FinSight AI")
    st.caption("Premium OTP login (simulated for demo)")

    mobile = st.text_input("Mobile Number", placeholder="Enter 10-digit mobile")
    c1, c2 = st.columns(2)

    if c1.button("Register / Send OTP", type="primary"):
        if not (mobile.isdigit() and len(mobile) == 10):
            st.session_state.login_error_fx = True
            st.markdown("<div class='otp-error'>Enter a valid 10-digit mobile number.</div>", unsafe_allow_html=True)
            return
        otp = f"{random.randint(100000, 999999)}"
        st.session_state.pending_mobile = mobile
        st.session_state.demo_otp = otp
        st.markdown("<div class='otp-success'>OTP sent successfully. (Demo mode)</div>", unsafe_allow_html=True)
        st.code(f"Your OTP is: {otp}")

    otp_input = st.text_input("Enter OTP", type="password")
    if c2.button("Verify OTP & Login"):
        if "pending_mobile" not in st.session_state or "demo_otp" not in st.session_state:
            st.session_state.login_error_fx = True
            st.markdown("<div class='otp-error'>Please generate OTP first.</div>", unsafe_allow_html=True)
            return
        if otp_input.strip() != st.session_state.demo_otp:
            st.session_state.login_error_fx = True
            st.markdown("<div class='otp-error'>Invalid OTP. Please try again.</div>", unsafe_allow_html=True)
            return

        store = load_store()
        mobile_ok = st.session_state.pending_mobile
        if mobile_ok not in store["users"]:
            store["users"][mobile_ok] = {"mobile": mobile_ok, "budget": 0.0, "expenses": []}
            save_store(store)
        st.session_state.user_mobile = mobile_ok
        st.session_state.logged_in = True
        st.markdown("<div class='otp-success'>Verified! Redirecting to your dashboard...</div>", unsafe_allow_html=True)
        sleep(0.25)
        st.rerun()
    st.markdown("</div></div>", unsafe_allow_html=True)


def app_shell() -> None:
    mobile = st.session_state.user_mobile
    store = load_store()
    user = store["users"].get(mobile, {"mobile": mobile, "budget": 0.0, "expenses": []})
    df = to_df(user["expenses"])

    st.sidebar.title("FinSight AI")
    st.sidebar.write(f"User: `{mobile}`")
    st.sidebar.success(f"Welcome back, {mobile}")
    if st.sidebar.button("2-minute Demo Mode"):
        st.session_state.demo_mode = True
        st.rerun()
    nav = st.sidebar.radio("Navigate", ["Dashboard", "Add Expense", "Import Bank Data", "AI Assistant"])
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.pop("user_mobile", None)
        st.rerun()

    if nav == "Dashboard":
        dashboard(user, df)
    elif nav == "Add Expense":
        add_expense(user, store)
    elif nav == "Import Bank Data":
        import_bank(user, store)
    elif nav == "AI Assistant":
        chatbot(user, df)
    else:
        dashboard(user, df)


def dashboard(user: dict[str, Any], df: pd.DataFrame) -> None:
    style()
    st.markdown(
        """
<div class="hero fade-in">
  <h2 style="margin:0;">FinSight AI - Smart Finance Command Center</h2>
  <p style="margin:6px 0 0 0;">Track spending, catch risks early, and get AI-driven advice instantly.</p>
</div>
        """,
        unsafe_allow_html=True,
    )

    budget = float(user.get("budget", 0.0) or 0.0)
    month_df = month_filter(df)
    month_spend = float(month_df["amount"].sum()) if not month_df.empty else 0.0
    total_spend = float(df["amount"].sum()) if not df.empty else 0.0
    score = calc_health_score(df, budget)
    left = max(0.0, budget - month_spend) if budget > 0 else 0.0

    c1, c2, c3 = st.columns(3)
    with c1:
        components.html(
            kpi_card_html("Total Spending", total_spend, CURRENCY, "linear-gradient(135deg,#06b6d4,#3b82f6)", "💰"),
            height=130,
        )
    with c2:
        components.html(
            kpi_card_html("Remaining Budget", left, CURRENCY, "linear-gradient(135deg,#22c55e,#16a34a)", "🏦"),
            height=130,
        )
    with c3:
        components.html(
            kpi_card_html("Financial Health Score", float(score), "", "linear-gradient(135deg,#f59e0b,#ef4444)", "💯", suffix="/100"),
            height=130,
        )

    if st.session_state.get("demo_mode", False):
        store = load_store()
        run_demo_story(user, store, df)

    tab_dash, tab_insights = st.tabs(["📊 Dashboard", "🧠 Insights"])
    with tab_dash:
        st.markdown("### 🚨 Ultra Budget Alert System")
        if budget <= 0:
            st.info("Set a monthly budget from the section below to activate smart alerts.")
        else:
            used_pct = min(100.0, (month_spend / budget) * 100.0)
            emoji, message = budget_message(used_pct)
            st.markdown(
                f"<div class='glass reveal'><div><b>Budget Used:</b> {used_pct:.1f}% ({money(month_spend)} / {money(budget)})</div></div>",
                unsafe_allow_html=True,
            )
            fill_class = "budget-fill budget-fill-danger" if used_pct >= 95 else "budget-fill"
            st.markdown(
                f"<div class='budget-shell'><div class='{fill_class}' style='width:{used_pct:.1f}%;'></div></div>",
                unsafe_allow_html=True,
            )

            alerts = budget_alerts(month_spend, budget)
            if not alerts:
                st.markdown("<div class='alert-box alert-green reveal'>🟢 <b>Good start! You are in control.</b></div>", unsafe_allow_html=True)
            else:
                level_map = {
                    25: "alert-green",
                    50: "alert-yellow",
                    75: "alert-orange",
                    90: "alert-red",
                    95: "alert-red",
                }
                for pct, _, msg in sorted(alerts, key=lambda x: x[0]):
                    css = level_map.get(int(pct), "alert-yellow")
                    em = "🟢" if pct == 25 else "🟡" if pct == 50 else "🟠" if pct == 75 else "🔴"
                    if pct == 95:
                        em = "🚨"
                    st.markdown(f"<div class='alert-box {css} reveal'>{em} <b>{msg}</b></div>", unsafe_allow_html=True)
                st.markdown(
                    f"<div class='alert-box alert-yellow reveal'>{emoji} {message}</div>",
                    unsafe_allow_html=True,
                )

        st.markdown("### 📈 Charts")
        a, b = st.columns(2)
        if df.empty:
            st.info("No expenses yet. Add entries or import bank data.")
        else:
            by_cat = df.groupby("category", as_index=False)["amount"].sum()
            with st.spinner("Loading premium analytics..."):
                pie = px.pie(by_cat, names="category", values="amount", hole=0.45, title="Category Split 🧩")
                daily = df.groupby("date", as_index=False)["amount"].sum().sort_values("date")
                line = px.line(daily, x="date", y="amount", markers=True, title="Spending Trend 📉")
            pie.update_layout(transition_duration=550)
            line.update_layout(transition_duration=550)
            a.markdown("<div class='chart-wrap reveal'>", unsafe_allow_html=True)
            a.plotly_chart(pie, use_container_width=True)
            a.markdown("</div>", unsafe_allow_html=True)
            b.markdown("<div class='chart-wrap reveal'>", unsafe_allow_html=True)
            b.plotly_chart(line, use_container_width=True)
            b.markdown("</div>", unsafe_allow_html=True)

    with tab_insights:
        st.markdown("### 🧠 Smart Financial Insights")
        for tip in smart_insights(df):
            st.markdown(f"<div class='glass reveal' style='margin-bottom:8px;'>- {tip}</div>", unsafe_allow_html=True)
        st.markdown("### 💡 Investment & Savings Suggestions")
        for tip in investment_tips(df, budget):
            st.markdown(f"<div class='glass reveal' style='margin-bottom:8px;'>- {tip}</div>", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("#### Set Monthly Budget")
    new_budget = st.number_input("Monthly budget", min_value=0.0, value=float(budget), step=500.0, format="%.2f")
    if st.button("Save Budget", type="primary"):
        store = load_store()
        mobile = st.session_state.user_mobile
        store["users"][mobile]["budget"] = float(new_budget)
        save_store(store)
        st.success("Budget saved.")
        st.rerun()


def add_expense(user: dict[str, Any], store: dict[str, Any]) -> None:
    style()
    st.subheader("Add Expense")
    with st.form("expense_form", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        amount = c1.number_input("Amount", min_value=0.0, value=0.0, step=10.0, format="%.2f")
        category = c2.selectbox("Category", options=CATEGORIES)
        exp_date = c3.date_input("Date", value=date.today())
        merchant = st.text_input("Merchant / Note", value="Manual Entry")
        ok = st.form_submit_button("Add Expense", type="primary")

    if ok:
        mobile = st.session_state.user_mobile
        store["users"][mobile]["expenses"].append(
            {
                "date": exp_date.isoformat(),
                "merchant": merchant.strip() or "Manual Entry",
                "amount": float(amount),
                "category": category,
                "source": "manual",
            }
        )
        save_store(store)
        st.success("Expense added.")
        st.rerun()

    df = to_df(user.get("expenses", []))
    st.markdown("#### Recent Expenses")
    if df.empty:
        st.info("No expenses yet.")
    else:
        show = df.sort_values("date", ascending=False).copy()
        show["amount"] = show["amount"].map(money)
        st.dataframe(show, use_container_width=True, hide_index=True)


def import_bank(user: dict[str, Any], store: dict[str, Any]) -> None:
    style()
    st.subheader("Import Bank Data")
    st.caption("Simulated API integration: transaction payload generated dynamically.")

    mobile = st.session_state.user_mobile
    if "bank_preview" not in st.session_state:
        st.session_state.bank_preview = []

    if st.button("Fetch from Simulated Bank API", type="primary"):
        st.session_state.bank_preview = fake_bank_transactions(mobile, n=12)
        st.success("Bank API response received.")

    preview = to_df(st.session_state.bank_preview)
    if preview.empty:
        st.info("Click the fetch button to generate bank transactions.")
        return

    show = preview.copy()
    show["amount"] = show["amount"].map(money)
    st.dataframe(show[["date", "merchant", "amount", "category", "source"]], use_container_width=True, hide_index=True)

    if st.button("Import Bank Data"):
        existing = {
            f"{e.get('date','')}-{e.get('merchant','')}-{float(e.get('amount',0.0)):.2f}"
            for e in user.get("expenses", [])
        }
        imported = 0
        for row in st.session_state.bank_preview:
            key = f"{row['date']}-{row['merchant']}-{float(row['amount']):.2f}"
            if key in existing:
                continue
            store["users"][mobile]["expenses"].append(row)
            imported += 1
        save_store(store)
        st.session_state.last_imported_count = imported
        st.success(f"Imported {imported} transactions.")
        st.rerun()


def chatbot(user: dict[str, Any], df: pd.DataFrame) -> None:
    style()
    st.subheader("AI Assistant")
    st.caption("ChatGPT-powered financial copilot with fallback intelligence.")
    st.markdown("<div class='glass reveal' style='margin-bottom:10px;'>💡 Tip: Ask budget-aware questions like 'Can I still invest this month?'</div>", unsafe_allow_html=True)
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = [
            ("assistant", "Hey! I’m your financial assistant. Let’s improve your money habits.")
        ]

    render_chat_panel(st.session_state.chat_history)

    prompt = st.chat_input("Ask your finance question...")
    if prompt:
        st.session_state.chat_history.append(("user", prompt))
        budget = float(user.get("budget", 0.0) or 0.0)
        financial_context = build_financial_context(df, budget)
        history_msgs = [{"role": r, "content": m} for r, m in st.session_state.chat_history[-20:]]
        st.markdown(
            "<div class='chat-bubble-ai'><span class='typing-dot'></span><span class='typing-dot'></span><span class='typing-dot'></span> FinSight AI is thinking...</div>",
            unsafe_allow_html=True,
        )
        answer = ask_openai(history_msgs, financial_context, latest_user_question=prompt)
        if not answer:
            answer = chatbot_answer(prompt, df, budget)
        typewriter_markdown(answer)
        st.session_state.chat_history.append(("assistant", answer))


def main() -> None:
    st.set_page_config(page_title=APP_NAME, page_icon="money_with_wings", layout="wide")
    ensure_store()
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        login_page()
    else:
        if st.session_state.get("last_imported_count", 0) > 0:
            st.toast(f"Bank sync complete: {st.session_state.last_imported_count} new transactions. Dashboard updated live.")
            st.session_state.last_imported_count = 0
        app_shell()


if __name__ == "__main__":
    main()

