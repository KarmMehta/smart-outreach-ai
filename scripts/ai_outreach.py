import os, random, time
import pandas as pd
from typing import Dict, Any

# ---------- Config helpers ----------
def get_cfg() -> Dict[str, Any]:
    def _bool(v, default=False):
        if v is None: return default
        return str(v).strip().lower() in {"1","true","yes","y","on"}
    return {
        "MOCK_MODE": _bool(os.getenv("MOCK_MODE"), True),
        "WORD_LIMIT": int(os.getenv("WORD_LIMIT", "75")),
        "MAX_ROWS": int(os.getenv("MAX_ROWS", "100")),
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY", "").strip(),
        "OPENAI_MODEL": os.getenv("OPENAI_MODEL", "gpt-5-mini"),
    }

# ---------- Mock generator (FREE) ----------
_OPENERS = [
    "Quick idea",
    "Noticed something you’ll like",
    "Fast win for your team",
    "Worth a peek",
]
_BENEFITS = [
    "replace manual list-building & cold emails",
    "boost reply rates with tailored first lines",
    "free your team from repetitive outreach tasks",
    "A/B test at scale with one click",
]
_CTAS = [
    "Worth a 5-min look?",
    "Open to a 10-min walk-through?",
    "Shall I send a 3-slide mini-demo?",
    "Happy to show a quick preview?",
]

def mock_message(name, company, role, word_limit=75) -> str:
    opener = random.choice(_OPENERS)
    benefit = random.choice(_BENEFITS)
    cta = random.choice(_CTAS)
    base = (
        f"Hi {name}, {opener} for {company}. "
        f"I build Python + AI outreach automations that {benefit}. "
        f"We can personalize at scale and keep it on-brand. {cta}\n—Karm"
    )
    # cheap limiter
    words = base.split()
    if len(words) > word_limit:
        base = " ".join(words[:word_limit]) + "…"
    return base

# ---------- Optional OpenAI generator ----------
def openai_message(name, company, role, word_limit, api_key, model) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    prompt = (
        "You are an expert B2B outreach copywriter.\n"
        f"Write a short LinkedIn DM to {name}, the {role} at {company}.\n"
        "Offer help with AI-powered lead generation & outreach automation "
        "(Python + AI workflows). One concrete benefit. Warm, 70-85 words. "
        "No emojis. End with a single-line CTA signed —Karm."
    )
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.6,
    )
    return resp.choices[0].message.content.strip()

# ---------- Public API ----------
def run_outreach(leads_df: pd.DataFrame, cfg: Dict[str, Any]) -> pd.DataFrame:
    """Return dataframe with outreach_message column."""
    # keep only the columns we need
    cols = [c for c in ["name","company","email","role"] if c in leads_df.columns]
    df = leads_df[cols].copy()

    # dedupe on email if present
    if "email" in df.columns:
        df = df.drop_duplicates(subset="email", keep="first")

    # cap rows
    df = df.head(cfg["MAX_ROWS"]).reset_index(drop=True)

    outputs = []
    use_mock = cfg["MOCK_MODE"] or not cfg["OPENAI_API_KEY"]
    for _, r in df.iterrows():
        try:
            if use_mock:
                msg = mock_message(r.get("name",""), r.get("company",""), r.get("role",""), cfg["WORD_LIMIT"])
            else:
                msg = openai_message(
                    r.get("name",""), r.get("company",""), r.get("role",""),
                    cfg["WORD_LIMIT"], cfg["OPENAI_API_KEY"], cfg["OPENAI_MODEL"]
                )
                time.sleep(0.2)  # gentle rate
        except Exception as e:
            msg = f"[ERROR] {e}"
        row = r.to_dict()
        row["outreach_message"] = msg
        outputs.append(row)

    return pd.DataFrame(outputs)