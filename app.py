import streamlit as st
import pandas as pd
import os
from datetime import datetime
import plotly.express as px

# -----------------------------
# CONFIG
# -----------------------------

CONTROL_ID = "Control ID"
STATUS = "Status"

DATA_DIR = "data"
VERSIONS_DIR = os.path.join(DATA_DIR, "dashboard_versions")
HISTORY_FILE = os.path.join(DATA_DIR, "history_metrics.csv")

os.makedirs(VERSIONS_DIR, exist_ok=True)

# -----------------------------
# SAVE DASHBOARD VERSION
# -----------------------------

def save_dashboard_version(df):

    today = datetime.today().strftime("%Y-%m-%d")
    file_path = os.path.join(VERSIONS_DIR, f"{today}_dashboard.xlsx")

    df.to_excel(file_path, index=False)

# -----------------------------
# GET LATEST VERSION
# -----------------------------

def get_latest_version():

    files = sorted(os.listdir(VERSIONS_DIR))

    if len(files) == 0:
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
# REPORT COMPARISON
# -----------------------------

def compare_reports(old_df, new_df):

    if old_df is None:
        return pd.DataFrame(), pd.DataFrame()

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
        title="Control Status Distribution"
    )

    return fig

def trend_chart(history):

    fig = px.line(
        history,
        x="date",
        y=["open", "closed"],
        title="Daily Control Status Trend"
    )

    return fig

# -----------------------------
# STREAMLIT APP
# -----------------------------

st.set_page_config(layout="wide")

st.title("SOX Monitoring Dashboard")

uploaded = st.file_uploader(
    "Upload Today's SOX Dashboard",
    type=["xlsx"]
)

if uploaded:

    new_df = pd.read_excel(uploaded)

    st.subheader("Dashboard Preview")
    st.dataframe(new_df)

    # Load last version
    old_df = get_latest_version()

    # Compare reports
    movements = compare_reports(old_df, new_df)

    if not movements.empty:

        st.subheader("Status Movements Detected")
        st.dataframe(movements)

    # Save new version
    save_dashboard_version(new_df)

    # Update historical metrics
    history = update_history(new_df)

    st.subheader("Analytics Dashboard")

    col1, col2 = st.columns(2)

    with col1:
        st.plotly_chart(status_pie(new_df), use_container_width=True)

    with col2:
        st.plotly_chart(trend_chart(history), use_container_width=True)

    st.success("Dashboard version stored successfully.")
