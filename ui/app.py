"""
ui/app.py — Streamlit UI for Text-to-SQL Agent
Premium glassmorphism design
"""
import streamlit as st
import requests
import pandas as pd
import plotly.express as px

API_URL = "http://localhost:8000"

st.set_page_config(page_title="Text-to-SQL Agent", page_icon="🗄️", layout="wide")

# ── Premium CSS ───────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500&display=swap');

.stApp {
    background: linear-gradient(135deg, #0a192f 0%, #112240 40%, #1a365d 100%);
}
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.block-container { padding-top: 2rem; }
header[data-testid="stHeader"] { background: transparent; }

section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0a192f 0%, #0d1b2a 100%) !important;
    border-right: 1px solid rgba(100,200,255,0.08);
}
section[data-testid="stSidebar"] .stMarkdown { color: #ccd6f6; }

.hero {
    text-align: center; padding: 40px 20px 20px 20px;
}
.hero h1 {
    font-size: 3rem; font-weight: 800;
    background: linear-gradient(135deg, #64ffda, #00b4d8, #7b61ff);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 8px; letter-spacing: -1px;
}
.hero p { color: #8892b0; font-size: 1.15rem; font-weight: 300; }

.glass {
    background: rgba(255,255,255,0.04);
    backdrop-filter: blur(16px);
    border: 1px solid rgba(100,255,218,0.1);
    border-radius: 16px; padding: 24px; margin: 12px 0; color: #ccd6f6;
}

.sql-box {
    background: rgba(10,25,47,0.8);
    border: 1px solid rgba(100,255,218,0.2);
    border-radius: 12px; padding: 18px; margin: 10px 0;
    font-family: 'JetBrains Mono', monospace; font-size: 0.9em;
    color: #64ffda; line-height: 1.6;
    box-shadow: 0 4px 20px rgba(0,0,0,0.3);
}

.example-chip {
    display: inline-block;
    background: rgba(100,255,218,0.08);
    border: 1px solid rgba(100,255,218,0.2);
    border-radius: 20px; padding: 8px 16px; margin: 4px;
    color: #8892b0; font-size: 0.85em;
    transition: all 0.3s ease; cursor: pointer;
}
.example-chip:hover {
    background: rgba(100,255,218,0.15);
    color: #64ffda; transform: translateY(-2px);
}

.metric-glass {
    background: rgba(255,255,255,0.04);
    backdrop-filter: blur(12px);
    border: 1px solid rgba(100,255,218,0.1);
    border-radius: 14px; padding: 20px; text-align: center;
}
.metric-glass .value {
    font-size: 2rem; font-weight: 700;
    background: linear-gradient(135deg, #64ffda, #00b4d8);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.metric-glass .label { color: #8892b0; font-size: 0.85rem; margin-top: 4px; }

.correction-badge {
    background: linear-gradient(135deg, rgba(100,255,218,0.1), rgba(0,180,216,0.1));
    border: 1px solid rgba(100,255,218,0.3);
    border-radius: 10px; padding: 12px 18px; color: #64ffda;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    background: rgba(255,255,255,0.03); border-radius: 12px; padding: 4px; gap: 4px;
}
.stTabs [data-baseweb="tab"] { border-radius: 8px; color: #8892b0; font-weight: 500; }
.stTabs [aria-selected="true"] {
    background: rgba(100,255,218,0.15) !important; color: #64ffda !important;
}

/* Buttons */
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #64ffda, #00b4d8) !important;
    border: none !important; border-radius: 10px !important;
    color: #0a192f !important; font-weight: 700 !important;
    transition: all 0.3s ease !important;
}
.stButton > button[kind="primary"]:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 25px rgba(100,255,218,0.3) !important;
}

/* Inputs */
.stTextArea textarea, .stTextInput input {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid rgba(100,255,218,0.15) !important;
    border-radius: 10px !important; color: #ccd6f6 !important;
}

/* Dataframe */
.stDataFrame { border-radius: 12px; overflow: hidden; }

.streamlit-expanderHeader {
    background: rgba(255,255,255,0.03) !important;
    border-radius: 8px !important; color: #8892b0 !important;
}
.js-plotly-plot .plotly .main-svg { background: transparent !important; }

/* Streamlit overrides */
footer, #MainMenu, .stDeployButton, div[data-testid="stDecoration"] { display: none !important; }
[data-testid="stAppViewContainer"] { background: transparent !important; }
[data-testid="stHeader"] { background: transparent !important; }
[data-testid="stSidebarContent"] { background: transparent !important; }
[data-testid="stBottomBlockContainer"] { background: transparent !important; }
div[data-testid="stMetricValue"] > div { color: #ccd6f6 !important; }
div[data-testid="stMetricDelta"] { color: #8892b0 !important; }
div[data-testid="stMetricLabel"] { color: #8892b0 !important; }
</style>
""", unsafe_allow_html=True)

# ── Hero ──────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
    <h1>🗄️ Text-to-SQL Agent</h1>
    <p>Ask your database in plain English — AI generates, validates, and self-corrects SQL in real time</p>
</div>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🗄️ Database Explorer")
    st.caption("Schema & connection status")
    st.divider()
    try:
        requests.get(f"{API_URL}/health", timeout=5)
        st.success("🟢 API Connected")
        schema = requests.get(f"{API_URL}/schema", timeout=5).json()
        st.markdown("**📊 Tables:**")
        for table, cols in schema.get("tables", {}).items():
            with st.expander(f"📋 {table}"):
                for c in cols:
                    st.caption(f"• {c}")
    except Exception:
        st.error("🔴 API Offline — run: make run")
        st.stop()
    st.divider()
    st.caption("Built with OpenAI · FastAPI · SQLite")

# ── Example Questions ─────────────────────────────────────────────────────
example_questions = [
    "Show me the top 5 customers by total revenue",
    "How many orders are pending or processing?",
    "Which product category has the highest sales?",
    "What is the average order value by country?",
    "List all customers who have placed more than 3 orders",
]

st.markdown('<div class="glass">', unsafe_allow_html=True)
st.markdown("#### 💡 Try these example queries")
cols = st.columns(len(example_questions))
selected_example = None
for i, (col, q) in enumerate(zip(cols, example_questions)):
    with col:
        if st.button(f"💬", key=f"ex_{i}", help=q):
            selected_example = q
st.markdown('</div>', unsafe_allow_html=True)

# ── Query Input ───────────────────────────────────────────────────────────
question = st.text_input(
    "Your question",
    value=selected_example or "",
    placeholder="What are the top 5 products by revenue?",
    label_visibility="collapsed",
)

if st.button("🔍 Query Database", type="primary", use_container_width=True) or selected_example:
    q = selected_example or question
    if not q.strip():
        st.warning("Enter a question.")
    else:
        with st.spinner("Generating and executing SQL..."):
            resp = requests.post(f"{API_URL}/query", json={"question": q}, timeout=60)

        if resp.ok:
            r = resp.json()

            col1, col2, col3 = st.columns(3)
            with col1:
                status = "✅ Success" if r["success"] else "❌ Failed"
                st.markdown(
                    f'<div class="metric-glass"><div class="value" '
                    f'style="-webkit-text-fill-color:unset;color:{"#64ffda" if r["success"] else "#ff6b6b"}">'
                    f'{status}</div><div class="label">Status</div></div>',
                    unsafe_allow_html=True
                )
            with col2:
                st.markdown(
                    f'<div class="metric-glass"><div class="value">{r["row_count"]}</div>'
                    f'<div class="label">Rows Returned</div></div>',
                    unsafe_allow_html=True
                )
            with col3:
                st.markdown(
                    f'<div class="metric-glass"><div class="value">{r["attempts"]}</div>'
                    f'<div class="label">Attempts</div></div>',
                    unsafe_allow_html=True
                )

            st.markdown("#### Generated SQL")
            st.markdown(f'<div class="sql-box">{r["sql"]}</div>', unsafe_allow_html=True)

            if r.get("explanation"):
                st.caption(f"📖 {r['explanation']}")

            if r.get("attempts", 1) > 1:
                st.markdown(
                    f'<div class="correction-badge">🔄 Agent self-corrected after '
                    f'{r["attempts"]} attempts</div>',
                    unsafe_allow_html=True
                )

            if r["success"] and r["rows"]:
                st.markdown(f"#### Results ({r['row_count']} rows)")
                df = pd.DataFrame(r["rows"])
                st.dataframe(df, use_container_width=True)

                num_cols = df.select_dtypes(include="number").columns.tolist()
                str_cols = df.select_dtypes(include="object").columns.tolist()
                if num_cols and str_cols and len(df) > 1:
                    with st.expander("📊 Auto Chart"):
                        x_col = st.selectbox("X axis", str_cols)
                        y_col = st.selectbox("Y axis", num_cols)
                        fig = px.bar(df, x=x_col, y=y_col, title=q[:60])
                        fig.update_layout(
                            paper_bgcolor="rgba(0,0,0,0)",
                            plot_bgcolor="rgba(0,0,0,0)",
                            font=dict(color="#8892b0"),
                            xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
                            yaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
                        )
                        st.plotly_chart(fig, use_container_width=True)

            elif not r["success"]:
                st.error(f"Query failed: {r.get('error', 'Unknown error')}")

            with st.expander("📋 Raw JSON"):
                st.json(r)
        else:
            st.error(f"Error: {resp.text}")

# ── SQL Safety Checker ────────────────────────────────────────────────────
st.markdown("---")
st.markdown('<div class="glass">', unsafe_allow_html=True)
st.markdown("#### 🛡️ SQL Safety Checker")
st.caption("Validate any SQL before execution")
manual_sql = st.text_area("Paste any SQL to check if it's safe to run:", height=100,
                          placeholder="SELECT * FROM users WHERE id = 1")
st.markdown('</div>', unsafe_allow_html=True)

if st.button("🛡️ Check SQL Safety"):
    if manual_sql.strip():
        resp = requests.post(f"{API_URL}/validate-sql", json={"sql": manual_sql}, timeout=10)
        if resp.ok:
            r = resp.json()
            if r["safe"]:
                st.success("✅ Safe — this query is allowed")
            else:
                st.error(f"🚫 Blocked — {r['error']}")
