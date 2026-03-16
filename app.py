import streamlit as st
import pandas as pd
import os
from datetime import datetime
import plotly.express as px
from streamlit_plotly_events import plotly_events

# -----------------------------------------------------
# CONFIG
# -----------------------------------------------------

st.set_page_config(page_title="SOX Control Monitoring Platform", layout="wide")

UPLOAD_DIR = "data/uploads"
LOG_FILE = "data/upload_log.csv"

os.makedirs(UPLOAD_DIR, exist_ok=True)

# -----------------------------------------------------
# SESSION STATE
# -----------------------------------------------------

if "df" not in st.session_state:
    st.session_state.df = None

if "changes" not in st.session_state:
    st.session_state.changes = pd.DataFrame()

# -----------------------------------------------------
# HEADER
# -----------------------------------------------------

st.markdown("""
<div style="background:linear-gradient(90deg,#0f172a,#1e3a8a);
padding:30px;border-radius:12px;color:white;margin-bottom:20px;">
<h1>SOX Control Monitoring Platform</h1>
<p>Internal Audit Analytics Dashboard</p>
</div>
""", unsafe_allow_html=True)

# -----------------------------------------------------
# SIDEBAR
# -----------------------------------------------------

st.sidebar.title("Navigation")

page = st.sidebar.radio(
    "Select Page",
    ["Executive Dashboard","Change Analysis","Upload History","Raw Data"]
)

uploaded_file = st.sidebar.file_uploader(
    "Upload SOX Dashboard",
    type=["xlsx"]
)

# -----------------------------------------------------
# FILE SAVE
# -----------------------------------------------------

def save_uploaded_file(uploaded_file):

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    filename = f"{timestamp}_sox_dashboard.xlsx"

    path = os.path.join(UPLOAD_DIR, filename)

    with open(path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    return filename, path


# -----------------------------------------------------
# UPLOAD LOG
# -----------------------------------------------------

def update_upload_log(filename, df):

    entry = {
        "Upload Time": datetime.now(),
        "File Name": filename,
        "Controls": len(df)
    }

    new_row = pd.DataFrame([entry])

    if os.path.exists(LOG_FILE):

        log = pd.read_csv(LOG_FILE)
        log = pd.concat([log, new_row], ignore_index=True)

    else:

        log = new_row

    log.to_csv(LOG_FILE, index=False)


# -----------------------------------------------------
# LOAD LATEST FILES
# -----------------------------------------------------

def load_latest_files():

    files = sorted(os.listdir(UPLOAD_DIR))
    files = [f for f in files if f.endswith(".xlsx")]

    if len(files) == 0:
        return None, None

    latest_file = os.path.join(UPLOAD_DIR, files[-1])
    latest_df = pd.read_excel(latest_file)

    previous_df = None

    if len(files) > 1:

        previous_file = os.path.join(UPLOAD_DIR, files[-2])
        previous_df = pd.read_excel(previous_file)

    return latest_df, previous_df


# -----------------------------------------------------
# CONTROL COLUMN DETECTION
# -----------------------------------------------------

def get_control_column(df):

    for col in ["Control Number", "Control ID"]:
        if col in df.columns:
            return col

    return None


# -----------------------------------------------------
# DATASET VALIDATION
# -----------------------------------------------------

def validate_dataset(df):

    control_col = get_control_column(df)

    if control_col is None:
        st.error("File must contain Control Number or Control ID column")
        st.stop()

    if "Status" not in df.columns:
        st.error("File must contain Status column")
        st.stop()

    return control_col


# -----------------------------------------------------
# CHANGE DETECTION
# -----------------------------------------------------

def compare_versions(old_df, new_df):

    control_col = get_control_column(new_df)

    old_df[control_col] = old_df[control_col].astype(str).str.strip()
    new_df[control_col] = new_df[control_col].astype(str).str.strip()

    old_df = old_df.set_index(control_col)
    new_df = new_df.set_index(control_col)

    changes = []

    common_controls = old_df.index.intersection(new_df.index)

    for cid in common_controls:

        old_status = old_df.loc[cid, "Status"]
        new_status = new_df.loc[cid, "Status"]

        if isinstance(old_status, pd.Series):
            old_status = old_status.iloc[0]

        if isinstance(new_status, pd.Series):
            new_status = new_status.iloc[0]

        if str(old_status).strip() != str(new_status).strip():

            changes.append({
                "Control": cid,
                "Change Type": "Status Change",
                "Old": old_status,
                "New": new_status
            })

    new_controls = new_df.index.difference(old_df.index)

    for cid in new_controls:

        changes.append({
            "Control": cid,
            "Change Type": "New Control",
            "Old": "N/A",
            "New": new_df.loc[cid, "Status"]
        })

    removed_controls = old_df.index.difference(new_df.index)

    for cid in removed_controls:

        changes.append({
            "Control": cid,
            "Change Type": "Control Removed",
            "Old": old_df.loc[cid, "Status"],
            "New": "N/A"
        })

    return pd.DataFrame(changes)


# -----------------------------------------------------
# HANDLE UPLOAD
# -----------------------------------------------------

if uploaded_file:

    filename, path = save_uploaded_file(uploaded_file)

    df = pd.read_excel(path)

    validate_dataset(df)

    update_upload_log(filename, df)

# -----------------------------------------------------
# LOAD LATEST DATA
# -----------------------------------------------------

latest_df, previous_df = load_latest_files()

if latest_df is not None:
    st.session_state.df = latest_df

if latest_df is not None and previous_df is not None:
    st.session_state.changes = compare_versions(previous_df, latest_df)

# -----------------------------------------------------
# EXECUTIVE DASHBOARD
# -----------------------------------------------------

if page == "Executive Dashboard":

    df = st.session_state.df

    if df is not None:

        total_controls = len(df)

        status_counts = df["Status"].value_counts()

        open_controls = status_counts.get("Open", 0)

        closed_controls = (
            status_counts.get("Closed", 0)
            + status_counts.get("Complete", 0)
            + status_counts.get("Review Complete", 0)
        )

        col1, col2, col3 = st.columns(3)

        col1.metric("Total Controls", total_controls)
        col2.metric("Open Controls", open_controls)
        col3.metric("Closed Controls", closed_controls)

        st.divider()

        colA, colB = st.columns(2)

        with colA:

            fig = px.pie(
                df,
                names="Status",
                hole=0.45,
                title="Control Status Distribution",
                color="Status",
                color_discrete_map={
                    "Open": "#EF4444",
                    "Closed": "#22C55E",
                    "Complete": "#22C55E",
                    "Review Complete": "#3B82F6"
                }
            )

            selected = plotly_events(fig)

            st.plotly_chart(fig, use_container_width=True)

            if selected:

                status_clicked = selected[0]["label"]

                st.subheader(f"Controls with status: {status_clicked}")

                st.dataframe(df[df["Status"] == status_clicked])

        with colB:

            status_counts = df["Status"].value_counts().reset_index()

            fig2 = px.bar(
                status_counts,
                x="Status",
                y="count",
                color="Status",
                title="Status Breakdown"
            )

            st.plotly_chart(fig2, use_container_width=True)

    else:

        st.info("Upload dashboard to begin analysis.")

# -----------------------------------------------------
# CHANGE ANALYSIS
# -----------------------------------------------------

elif page == "Change Analysis":

    changes = st.session_state.changes

    st.subheader("Changes Since Last Upload")

    if not changes.empty:

        col1, col2 = st.columns(2)

        col1.metric("Total Changes", len(changes))
        col2.metric("Affected Controls", changes["Control"].nunique())

        st.dataframe(changes)

        change_counts = changes["Change Type"].value_counts()

        chart_df = pd.DataFrame({
            "Change Type": change_counts.index,
            "Count": change_counts.values
        })

        fig = px.bar(
            chart_df,
            x="Change Type",
            y="Count",
            color="Change Type",
            title="Detected Changes"
        )

        st.plotly_chart(fig, use_container_width=True)

    else:

        st.info("Upload at least two dashboards to detect changes.")

# -----------------------------------------------------
# UPLOAD HISTORY
# -----------------------------------------------------

elif page == "Upload History":

    st.subheader("Dashboard Upload History")

    if os.path.exists(LOG_FILE):

        log = pd.read_csv(LOG_FILE)

        st.dataframe(log)

        for _, row in log.iterrows():

            path = os.path.join(UPLOAD_DIR, row["File Name"])

            if os.path.exists(path):

                with open(path, "rb") as f:

                    st.download_button(
                        label=f"Download {row['File Name']}",
                        data=f,
                        file_name=row["File Name"]
                    )

    else:

        st.info("No uploads recorded yet.")

# -----------------------------------------------------
# RAW DATA
# -----------------------------------------------------

elif page == "Raw Data":

    df = st.session_state.df

    if df is not None:

        st.dataframe(df)

    else:

        st.info("Upload dashboard to view raw data.")
