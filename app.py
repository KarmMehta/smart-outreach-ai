import os
from io import StringIO
import pandas as pd
import streamlit as st
import plotly.express as px
from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader, select_autoescape
from scripts.ai_outreach import get_cfg, run_outreach

# ----------------- Setup -----------------
st.set_page_config(page_title="Smart Outreach AI", page_icon="🤖", layout="wide")
load_dotenv()  # read .env
cfg = get_cfg()

BRAND = {
    "accent": "#3E8EFB",
    "bg_grad_1": "#0B1220",
    "bg_grad_2": "#0F1C2E",
    "card": "#121B2A",
    "text": "#E8EEF6",
    "muted": "#A7B3C5",
}

CSS = f"""
<style>
/* background gradient */
.stApp {{
  background: linear-gradient(135deg, {BRAND['bg_grad_1']} 0%, {BRAND['bg_grad_2']} 100%);
  color: {BRAND['text']};
}}
/* cards */
.block-container {{ padding-top: 2rem; }}
div[data-testid="stHeader"] {{ background: transparent; }}
.css-1r6slb0, .css-1r6slb0.e1fqkh3o3 {{ background: transparent !important; }}
/* metric-like header */
.hero {{
  border: 1px solid rgba(255,255,255,0.08);
  background: {BRAND['card']};
  border-radius: 16px; padding: 20px 24px; margin-bottom: 14px;
}}
.pill {{
  background: rgba(62,142,251,0.15);
  color: {BRAND['accent']}; padding: 4px 10px; border-radius: 999px;
  font-size: 0.85rem; letter-spacing: .02em;
}}
.small {{ color: {BRAND['muted']}; font-size: 0.9rem; }}
.card {{
  border: 1px solid rgba(255,255,255,0.08);
  background: {BRAND['card']};
  border-radius: 14px; padding: 18px;
}}
.msg {{
  white-space: pre-wrap; line-height: 1.45;
}}
.downloads > * {{ margin-right: 10px; }}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# ----------------- Sidebar -----------------
st.sidebar.title("⚙️ Settings")
st.sidebar.caption("Defaults keep it **FREE** (Mock Mode).")

mock_mode = st.sidebar.toggle("Mock Mode (free)", value=cfg["MOCK_MODE"])
word_limit = st.sidebar.slider("Word limit", 60, 100, cfg["WORD_LIMIT"])
max_rows = st.sidebar.slider("Max leads", 5, 200, cfg["MAX_ROWS"])

api_key = st.sidebar.text_input("OpenAI API Key (optional)", type="password")
model = st.sidebar.selectbox("Model", ["gpt-5-mini", "gpt-4o-mini"], index=0)

st.sidebar.markdown("---")
st.sidebar.caption("Upload your .CSV or use the sample.")
uploaded = st.sidebar.file_uploader("Upload leads.csv", type=["csv"])

# ----------------- Load leads -----------------
@st.cache_data
def load_sample() -> pd.DataFrame:
    path = os.path.join("data", "leads.csv")
    if os.path.exists(path):
        return pd.read_csv(path)
    return pd.DataFrame(columns=["name","company","email","role"])

leads_df = pd.read_csv(uploaded) if uploaded else load_sample()
st.session_state["leads"] = leads_df

# ----------------- Header -----------------
st.markdown(
    """
<div class="hero">
  <span class="pill">Smart Outreach AI</span>
  <h1 style="margin:8px 0 0 0;">AI-Powered Lead Generation & Outreach Automation</h1>
  <div class="small">Personalized first lines, A/B testing, CRM-ready exports.</div>
</div>
""",
    unsafe_allow_html=True,
)

# ----------------- Controls & Generate -----------------
c1, c2, c3 = st.columns([2,2,1])
with c1:
    st.write("**Leads preview**")
    st.dataframe(leads_df.head(8), use_container_width=True, height=260)
with c2:
    st.write("**Configuration**")
    st.write(f"Mode: {'MOCK (FREE)' if mock_mode else 'API'}")
    st.write(f"Word limit: {word_limit}")
    st.write(f"Max rows: {max_rows}")
with c3:
    st.write("")
    run = st.button("🚀 Generate Messages", type="primary", use_container_width=True)

# ----------------- Generate -----------------
results_df = None
if run:
    # refresh env-like cfg for this run
    os.environ["MOCK_MODE"] = "true" if mock_mode else "false"
    os.environ["WORD_LIMIT"] = str(word_limit)
    os.environ["MAX_ROWS"] = str(max_rows)
    if api_key:
        os.environ["OPENAI_API_KEY"] = api_key
    os.environ["OPENAI_MODEL"] = model

    cfg_live = get_cfg()
    with st.spinner("Generating outreach messages…"):
        results_df = run_outreach(leads_df, cfg_live)
    st.session_state["results"] = results_df
    st.success(f"Generated {len(results_df)} messages.")

# reuse if already in session
results_df = st.session_state.get("results", results_df)

# ----------------- Results & Charts -----------------
if isinstance(results_df, pd.DataFrame) and not results_df.empty:
    st.subheader("📬 Outreach Pack")
    st.caption("Polished copy, CRM-ready. Click to expand each message.")
    for i, row in results_df.iterrows():
        with st.expander(f"{row.get('name','(no name)')}  ·  {row.get('role','')} @ {row.get('company','')}"):
            st.markdown(f"<div class='msg'>{row['outreach_message']}</div>", unsafe_allow_html=True)

    # chart (word count distribution)
    wc = results_df["outreach_message"].str.split().map(len)
    chart_df = pd.DataFrame({"Words": wc})
    fig = px.histogram(chart_df, x="Words", nbins=14, title="Message Length Distribution")
    fig.update_layout(height=340, margin=dict(l=10,r=10,t=50,b=10))
    st.plotly_chart(fig, use_container_width=True)

    # ----------------- Exports -----------------
    st.subheader("⬇️ Export")
    st.caption("CSV for CRM · HTML deck for review")
    # CSV
    csv_bytes = results_df.to_csv(index=False).encode("utf-8")

    # HTML (Jinja2 template)
    env = Environment(
        loader=FileSystemLoader("templates"),
        autoescape=select_autoescape()
    )
    tpl = env.get_template("report.html")
    html = tpl.render(
        title="Outreach Pack",
        mode="MOCK" if mock_mode else "API",
        word_limit=word_limit,
        count=len(results_df),
        rows=results_df.to_dict(orient="records"),
    )
    html_bytes = html.encode("utf-8")

    d1, d2 = st.columns(2)
    with d1:
        st.download_button(
            "Download CSV",
            data=csv_bytes,
            file_name="outreach_results.csv",
            mime="text/csv",
            use_container_width=True
        )
    with d2:
        st.download_button(
            "Download HTML report",
            data=html_bytes,
            file_name="outreach_report.html",
            mime="text/html",
            use_container_width=True
        )

else:
    st.info("Upload a leads CSV or use the sample, then click **Generate Messages**.")