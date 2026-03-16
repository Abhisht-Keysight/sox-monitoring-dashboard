import streamlit as st
import pandas as pd
import os
from datetime import datetime
import plotly.express as px
from openpyxl import load_workbook
from openpyxl.styles import PatternFill

st.set_page_config(page_title="SOX Control Monitoring Platform", layout="wide")

UPLOAD_DIR = "data/uploads"
LOG_FILE = "data/upload_log.csv"
OUTPUT_DIR = "data/output"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ---------------- SESSION STATE ----------------

if "df" not in st.session_state:
    st.session_state.df = None

if "changes" not in st.session_state:
    st.session_state.changes = pd.DataFrame()

# ---------------- HEADER ----------------

st.markdown("""
<div style="background:linear-gradient(90deg,#0f172a,#1e3a8a);
padding:30px;border-radius:12px;color:white;margin-bottom:20px;">
<h1>SOX Control Monitoring Platform</h1>
<p>Internal Audit Analytics Dashboard</p>
</div>
""", unsafe_allow_html=True)

# ---------------- SIDEBAR ----------------

st.sidebar.title("Navigation")

page = st.sidebar.radio(
    "Select Page",
    ["Executive Dashboard", "Change Analysis", "Upload History", "Raw Data"]
)

uploaded_file = st.sidebar.file_uploader("Upload SOX Dashboard", type=["xlsx"])

# ---------------- VALIDATION ----------------

def validate_dataset(df):

    required = [
        "PROCESS_UID",
        "CYCLE",
        "Test Name",
        "TESTS__TEST_SECTION",
        "TESTS__STATUS",
        "TESTS__EFFECTIVENESS",
        "TESTS__TESTER_USER",
        "TESTS__REVIEWER_USER",
        "TESTS__SECONDARY_REVIEWER_USER",
        "TESTS__START_DATE",
        "TESTS__END_DATE",
        "TESTS__DUE_DATE",
        "PWC Reliance",
        "Audit Team"
    ]

    missing = [c for c in required if c not in df.columns]

    if missing:
        st.error(f"Missing columns: {missing}")
        st.stop()

# ---------------- SAVE FILE ----------------

def save_file(uploaded_file):

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    filename = f"{timestamp}_dashboard.xlsx"
    path = os.path.join(UPLOAD_DIR, filename)

    with open(path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    return filename, path

# ---------------- UPLOAD LOG ----------------

def update_log(filename, df):

    entry = {
        "Upload Time": datetime.now(),
        "File Name": filename,
        "Tests": len(df)
    }

    new = pd.DataFrame([entry])

    if os.path.exists(LOG_FILE):
        log = pd.read_csv(LOG_FILE)
        log = pd.concat([log, new], ignore_index=True)
    else:
        log = new

    log.to_csv(LOG_FILE, index=False)

# ---------------- LOAD FILES ----------------

def load_latest_files():

    files = sorted(os.listdir(UPLOAD_DIR))
    files = [f for f in files if f.endswith(".xlsx")]

    if len(files) == 0:
        return None, None

    latest = pd.read_excel(os.path.join(UPLOAD_DIR, files[-1]), sheet_name="IA data")

    prev = None

    if len(files) > 1:
        prev = pd.read_excel(os.path.join(UPLOAD_DIR, files[-2]), sheet_name="IA data")

    return latest, prev

# ---------------- CHANGE DETECTION ----------------

def compare_versions(old_df, new_df):

    key = "Test Name"

    old_df[key] = old_df[key].astype(str)
    new_df[key] = new_df[key].astype(str)

    old_df = old_df.set_index(key)
    new_df = new_df.set_index(key)

    fields = list(new_df.columns)

    changes = []

    common = old_df.index.intersection(new_df.index)

    for test in common:

        for field in fields:

            old_val = str(old_df.loc[test, field])
            new_val = str(new_df.loc[test, field])

            if old_val != new_val:

                changes.append({
                    "Test Name": test,
                    "Field Changed": field,
                    "Old Value": old_val,
                    "New Value": new_val
                })

    new_tests = new_df.index.difference(old_df.index)

    for test in new_tests:

        changes.append({
            "Test Name": test,
            "Field Changed": "New Test",
            "Old Value": "",
            "New Value": "Added"
        })

    removed_tests = old_df.index.difference(new_df.index)

    for test in removed_tests:

        changes.append({
            "Test Name": test,
            "Field Changed": "Removed Test",
            "Old Value": "Removed",
            "New Value": ""
        })

    return pd.DataFrame(changes)

# ---------------- EXCEL HIGHLIGHT EXPORT ----------------

def generate_highlight_file(base_df, changes):

    path = os.path.join(OUTPUT_DIR, "change_highlight.xlsx")

    base_df.to_excel(path, index=False)

    wb = load_workbook(path)
    ws = wb.active

    yellow = PatternFill(start_color="FFFF00", end_color="FFFF00", fill_type="solid")

    headers = [cell.value for cell in ws[1]]

    for _, row in changes.iterrows():

        test = row["Test Name"]
        field = row["Field Changed"]

        if field in headers:

            col = headers.index(field) + 1

            for r in range(2, ws.max_row + 1):

                if ws.cell(r, headers.index("Test Name")+1).value == test:

                    ws.cell(r, col).fill = yellow

    wb.save(path)

    return path

# ---------------- HANDLE UPLOAD ----------------

if uploaded_file:

    filename, path = save_file(uploaded_file)

    df = pd.read_excel(path, sheet_name="IA data")

    validate_dataset(df)

    update_log(filename, df)

# ---------------- LOAD DATA ----------------

latest_df, previous_df = load_latest_files()

if latest_df is not None:
    st.session_state.df = latest_df

if latest_df is not None and previous_df is not None:
    st.session_state.changes = compare_versions(previous_df, latest_df)

# ---------------- EXECUTIVE DASHBOARD ----------------

if page == "Executive Dashboard":

    df = st.session_state.df

    if df is not None:

        col1, col2 = st.columns(2)

        col1.metric("Total Tests", len(df))
        col2.metric("Cycles", df["CYCLE"].nunique())

        status_counts = df["TESTS__STATUS"].value_counts()

        colA, colB = st.columns(2)

        with colA:

            fig = px.pie(
                df,
                names="TESTS__STATUS",
                hole=0.45,
                title="Test Status Distribution"
            )

            st.plotly_chart(fig, use_container_width=True)

        with colB:

            fig2 = px.bar(
                status_counts,
                title="Status Breakdown"
            )

            st.plotly_chart(fig2, use_container_width=True)

# ---------------- CHANGE ANALYSIS ----------------

elif page == "Change Analysis":

    changes = st.session_state.changes

    st.subheader("Changes Since Last Upload")

    if not changes.empty:

        col1, col2, col3 = st.columns(3)

        with col1:
            test_filter = st.multiselect(
                "Test Name",
                options=changes["Test Name"].unique()
            )

        with col2:
            field_filter = st.multiselect(
                "Field Changed",
                options=changes["Field Changed"].unique()
            )

        with col3:
            old_filter = st.multiselect(
                "Old Value",
                options=changes["Old Value"].astype(str).unique()
            )

        filtered = changes.copy()

        if test_filter:
            filtered = filtered[filtered["Test Name"].isin(test_filter)]

        if field_filter:
            filtered = filtered[filtered["Field Changed"].isin(field_filter)]

        if old_filter:
            filtered = filtered[filtered["Old Value"].isin(old_filter)]

        st.dataframe(filtered, use_container_width=True)

        counts = filtered["Field Changed"].value_counts()

        fig = px.bar(
            counts,
            title="Change Distribution"
        )

        st.plotly_chart(fig, use_container_width=True)

        if st.button("Download Highlighted Excel"):

            path = generate_highlight_file(st.session_state.df, changes)

            with open(path, "rb") as f:
                st.download_button(
                    "Download",
                    f,
                    file_name="highlighted_changes.xlsx"
                )

    else:

        st.info("Upload at least two dashboards to detect changes")

# ---------------- UPLOAD HISTORY ----------------

elif page == "Upload History":

    if os.path.exists(LOG_FILE):

        log = pd.read_csv(LOG_FILE)

        st.dataframe(log)

# ---------------- RAW DATA ----------------

elif page == "Raw Data":

    if st.session_state.df is not None:
        st.dataframe(st.session_state.df)
