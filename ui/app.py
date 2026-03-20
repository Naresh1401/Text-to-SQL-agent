"""
ui/app.py — Streamlit UI for Text-to-SQL Agent
"""
import streamlit as st
import requests
import pandas as pd
import plotly.express as px

API_URL = "http://localhost:8000"

st.set_page_config(page_title="Text-to-SQL", page_icon="🗄️", layout="wide")

st.markdown("""
<style>
.sql-box {
    background:#1e1e1e; color:#d4d4d4;
    font-family:monospace; font-size:0.9em;
    padding:14px; border-radius:8px; margin:8px 0;
    border:1px solid #444;
}
.attempt-badge {
    display:inline-block; background:#007bff; color:white;
    padding:2px 8px; border-radius:12px; font-size:0.8em;
}
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.title("🗄️ Text-to-SQL")
    st.caption("Ask your database in plain English")
    st.divider()
    try:
        requests.get(f"{API_URL}/health", timeout=5)
        st.success("🟢 API Connected")
        schema = requests.get(f"{API_URL}/schema", timeout=5).json()
        st.markdown("**Database Tables:**")
        for table, cols in schema.get("tables", {}).items():
            with st.expander(f"📋 {table}"):
                for c in cols:
                    st.caption(f"• {c}")
    except:
        st.error("🔴 API Offline — run: make run")
        st.stop()

st.title("🗄️ Ask Your Database")
st.caption("Type a question in plain English — get SQL and results instantly")

# Example questions
st.markdown("**Try these:**")
example_questions = [
    "Show me the top 5 customers by total revenue",
    "How many orders are pending or processing?",
    "Which product category has the highest sales?",
    "What is the average order value by country?",
    "List all customers who have placed more than 3 orders",
]
cols = st.columns(len(example_questions))
selected_example = None
for i, (col, q) in enumerate(zip(cols, example_questions)):
    with col:
        if st.button(f"💬", key=f"ex_{i}", help=q):
            selected_example = q

question = st.text_input(
    "Your question",
    value=selected_example or "",
    placeholder="What are the top 5 products by revenue?",
    label_visibility="collapsed",
)

if st.button("🔍 Query", type="primary", use_container_width=True) or selected_example:
    q = selected_example or question
    if not q.strip():
        st.warning("Enter a question.")
    else:
        with st.spinner("Generating and executing SQL..."):
            resp = requests.post(f"{API_URL}/query", json={"question": q}, timeout=60)

        if resp.ok:
            r = resp.json()

            col1, col2, col3 = st.columns(3)
            col1.metric("Status",    "✅ Success" if r["success"] else "❌ Failed")
            col2.metric("Rows",      r["row_count"])
            col3.metric("Attempts",  r["attempts"])

            # SQL display
            st.markdown("**Generated SQL:**")
            st.markdown(f'<div class="sql-box">{r["sql"]}</div>', unsafe_allow_html=True)

            if r.get("explanation"):
                st.caption(f"📖 {r['explanation']}")

            if r.get("attempts", 1) > 1:
                st.info(f"🔄 Self-corrected after {r['attempts']} attempts")

            # Results
            if r["success"] and r["rows"]:
                st.markdown(f"**Results** ({r['row_count']} rows):")
                df = pd.DataFrame(r["rows"])
                st.dataframe(df, use_container_width=True)

                # Auto-chart for numeric data
                num_cols = df.select_dtypes(include="number").columns.tolist()
                str_cols = df.select_dtypes(include="object").columns.tolist()
                if num_cols and str_cols and len(df) > 1:
                    with st.expander("📊 Auto Chart"):
                        x_col = st.selectbox("X axis", str_cols)
                        y_col = st.selectbox("Y axis", num_cols)
                        fig   = px.bar(df, x=x_col, y=y_col, title=q[:60])
                        st.plotly_chart(fig, use_container_width=True)

            elif not r["success"]:
                st.error(f"Query failed: {r.get('error', 'Unknown error')}")

            with st.expander("📋 Raw JSON"):
                st.json(r)
        else:
            st.error(f"Error: {resp.text}")

# SQL Validator
st.divider()
st.subheader("🛡️ SQL Safety Checker")
manual_sql = st.text_area("Paste any SQL to check if it's safe to run:", height=100,
                          placeholder="SELECT * FROM users WHERE id = 1")
if st.button("Check SQL"):
    if manual_sql.strip():
        resp = requests.post(f"{API_URL}/validate-sql", json={"sql": manual_sql}, timeout=10)
        if resp.ok:
            r = resp.json()
            if r["safe"]:
                st.success("✅ Safe — this query is allowed")
            else:
                st.error(f"🚫 Blocked — {r['error']}")
