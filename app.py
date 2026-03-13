import streamlit as st
import pandas as pd
import os
from datetime import datetime
import plotly.express as px

# -----------------------------
# PAGE CONFIG
# -----------------------------

st.set_page_config(
    page_title="SOX Control Monitoring",
    page_icon="📊",
    layout="wide"
)

# -----------------------------
# CONFIG
# -----------------------------

CONTROL_ID = "Control ID"
STATUS = "Status"

DATA_DIR = "data"
VERSIONS_DIR = os.path.join(DATA_DIR, "versions")
HISTORY_FILE = os.path.join(DATA_DIR, "history.csv")

os.makedirs(VERSIONS_DIR, exist_ok=True)

# -----------------------------
# CUSTOM CSS (UI IMPROVEMENT)
# -----------------------------

st.markdown("""
<style>

.main-title {
    font-size:40px;
    font-weight:700;
}

.metric-card {
    background-color:#f7f9fc;
    padding:20px;
    border-radius:10px;
    text-align:center;
}

</style>
""", unsafe_allow_html=True)

# -----------------------------
# SAVE DASHBOARD VERSION
# -----------------------------

def save_dashboard_version(df):

    today = datetime.today().strftime("%Y-%m-%d")

    file_path = os.path.join(
        VERSIONS_DIR,
        f"{today}_dashboard.xlsx"
    )

    df.to_excel(file_path, index=False)

# -----------------------------
# GET PREVIOUS VERSION
# -----------------------------

def get_previous_version():

    files = sorted(os.listdir(VERSIONS_DIR))

    if len(files) < 1:
        return None

    latest = os.path.join(VERSIONS_DIR, files[-1])

    return pd.read_excel(latest)

# -----------------------------
# UPDATE HISTORY METRICS
# -----------------------------

def update_history(df):

    metrics = {
        "date": datetime.today().date(),
        "total_controls": len(df),
        "open": len(df[df[STATUS] == "Open"]),
        "closed": len(df[df[STATUS] == "Closed"])
    }

    new_row = pd.DataFrame([metrics])

    if os.path.exists(HISTORY_FILE):

        hist = pd.read_csv(HISTORY_FILE)
        hist = pd.concat([hist, new_row], ignore_index=True)

    else:

        hist = new_row

    hist.to_csv(HISTORY_FILE, index=False)

    return hist

# -----------------------------
# COMPARE REPORTS
# -----------------------------

def compare_reports(old_df, new_df):

    if old_df is None:
        return pd.DataFrame()

    old_df = old_df.set_index(CONTROL_ID)
    new_df = new_df.set_index(CONTROL_ID)

    movements = []

    for cid in old_df.index.intersection(new_df.index):

        old_status = old_df.loc[cid][STATUS]
        new_status = new_df.loc[cid][STATUS]

        if old_status != new_status:

            movements.append({
                "Control ID": cid,
                "Old Status": old_status,
                "New Status": new_status
            })

    return pd.DataFrame(movements)

# -----------------------------
# CHARTS
# -----------------------------

def status_pie(df):

    fig = px.pie(
        df,
        names=STATUS,
        title="Control Status Distribution",
        hole=0.4
    )

    return fig

def trend_chart(history):

    fig = px.line(
        history,
        x="date",
        y=["open", "closed"],
        markers=True,
        title="Daily Control Status Trend"
    )

    return fig

# -----------------------------
# HEADER
# -----------------------------

st.markdown(
    "<div class='main-title'>📊 SOX Control Monitoring Dashboard</div>",
    unsafe_allow_html=True
)

st.write("Upload today's SOX dashboard to detect control changes and monitor trends.")

# -----------------------------
# FILE UPLOAD
# -----------------------------

uploaded = st.file_uploader(
    "Upload SOX Dashboard",
    type=["xlsx"]
)

if uploaded:

    new_df = pd.read_excel(uploaded)

    st.subheader("Dashboard Preview")
    st.dataframe(new_df)

    # -----------------------------
    # PREVIOUS VERSION
    # -----------------------------

    old_df = get_previous_version()

    movements = compare_reports(old_df, new_df)

    # -----------------------------
    # METRICS
    # -----------------------------

    open_controls = len(new_df[new_df[STATUS] == "Open"])
    closed_controls = len(new_df[new_df[STATUS] == "Closed"])

    col1, col2, col3 = st.columns(3)

    col1.metric("Total Controls", len(new_df))
    col2.metric("Open Controls", open_controls)
    col3.metric("Closed Controls", closed_controls)

    # -----------------------------
    # STATUS MOVEMENTS
    # -----------------------------

    if not movements.empty:

        st.subheader("Status Changes Detected")

        st.dataframe(movements)

    # -----------------------------
    # SAVE VERSION
    # -----------------------------

    save_dashboard_version(new_df)

    history = update_history(new_df)

    # -----------------------------
    # DASHBOARD
    # -----------------------------

    st.subheader("Analytics Dashboard")

    colA, colB = st.columns(2)

    with colA:
        st.plotly_chart(status_pie(new_df), use_container_width=True)

    with colB:
        st.plotly_chart(trend_chart(history), use_container_width=True)

    st.success("Dashboard processed successfully and version stored.")
