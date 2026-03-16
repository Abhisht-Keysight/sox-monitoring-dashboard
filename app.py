import streamlit as st
import pandas as pd
import os
from datetime import datetime
import plotly.express as px
from streamlit_plotly_events import plotly_events

# ---------------------------------------------------
# PAGE CONFIG
# ---------------------------------------------------

st.set_page_config(
    page_title="SOX Control Monitoring Platform",
    layout="wide"
)

UPLOAD_DIR = "data/uploads"
LOG_FILE = "data/upload_log.csv"

os.makedirs(UPLOAD_DIR, exist_ok=True)

# ---------------------------------------------------
# HEADER
# ---------------------------------------------------

st.markdown("""
<div style="
background:linear-gradient(90deg,#0f172a,#1e3a8a);
padding:30px;
border-radius:12px;
color:white;
margin-bottom:20px;
">
<h1>SOX Control Monitoring Platform</h1>
<p>Internal Audit Analytics Dashboard</p>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------
# SIDEBAR
# ---------------------------------------------------

st.sidebar.title("Navigation")

page = st.sidebar.radio(
    "Select Page",
    [
        "Executive Dashboard",
        "Change Analysis",
        "Upload History",
        "Raw Data"
    ]
)

uploaded_file = st.sidebar.file_uploader(
    "Upload SOX Dashboard",
    type=["xlsx"]
)

# ---------------------------------------------------
# SAVE FILE
# ---------------------------------------------------

def save_uploaded_file(uploaded_file):

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    filename = f"{timestamp}_sox_dashboard.xlsx"

    path = os.path.join(UPLOAD_DIR, filename)

    with open(path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    return filename, path


# ---------------------------------------------------
# UPDATE LOG
# ---------------------------------------------------

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


# ---------------------------------------------------
# LOAD PREVIOUS FILE
# ---------------------------------------------------

def load_previous_file():

    files = sorted(os.listdir(UPLOAD_DIR))
    files = [f for f in files if f.endswith(".xlsx")]

    if len(files) < 2:
        return None

    previous_file = os.path.join(UPLOAD_DIR, files[-2])

    try:
        return pd.read_excel(previous_file)
    except:
        return None


# ---------------------------------------------------
# DETECT CONTROL COLUMN
# ---------------------------------------------------

def get_control_column(df):

    possible = ["Control Number", "Control ID"]

    for col in possible:
        if col in df.columns:
            return col

    return None


# ---------------------------------------------------
# VALIDATE DATASET
# ---------------------------------------------------

def validate_dataset(df):

    control_col = get_control_column(df)

    if control_col is None:

        st.error("Dataset must contain 'Control Number' or 'Control ID'")
        st.stop()

    if "Status" not in df.columns:

        st.error("Dataset must contain a 'Status' column")
        st.stop()

    return control_col


# ---------------------------------------------------
# COMPARE VERSIONS
# ---------------------------------------------------

def compare_versions(old_df, new_df):

    control_col = get_control_column(new_df)

    if control_col is None:
        return pd.DataFrame()

    if control_col not in old_df.columns:
        return pd.DataFrame()

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

        if old_status != new_status:

            changes.append({
                "Control": cid,
                "Old Status": old_status,
                "New Status": new_status
            })

    return pd.DataFrame(changes)


# ---------------------------------------------------
# HANDLE UPLOAD
# ---------------------------------------------------

df = None
changes = pd.DataFrame()

if uploaded_file:

    filename, path = save_uploaded_file(uploaded_file)

    df = pd.read_excel(path)

    control_column = validate_dataset(df)

    update_upload_log(filename, df)

    previous_df = load_previous_file()

    if previous_df is not None:

        changes = compare_versions(previous_df, df)


# ---------------------------------------------------
# EXECUTIVE DASHBOARD
# ---------------------------------------------------

if page == "Executive Dashboard":

    if df is not None:

        total_controls = len(df)

        status_counts = df["Status"].value_counts()

        open_controls = status_counts.get("Open",0)
        closed_controls = status_counts.get("Closed",0) + status_counts.get("Complete",0)

        col1,col2,col3 = st.columns(3)

        col1.metric("Total Controls", total_controls)
        col2.metric("Open Controls", open_controls)
        col3.metric("Closed Controls", closed_controls)

        st.divider()

        colA,colB = st.columns(2)

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
                title="Status Breakdown",
                color="Status"
            )

            st.plotly_chart(fig2, use_container_width=True)

    else:

        st.info("Upload a valid SOX dashboard to begin analysis.")


# ---------------------------------------------------
# CHANGE ANALYSIS
# ---------------------------------------------------

elif page == "Change Analysis":

    st.subheader("Changes Since Last Upload")

    if not changes.empty:

        col1,col2 = st.columns(2)

        col1.metric("Total Changes", len(changes))
        col2.metric("Affected Controls", changes["Control"].nunique())

        st.dataframe(changes)

        movement_counts = changes.groupby(
            ["Old Status","New Status"]
        ).size().reset_index(name="Count")

        fig = px.bar(
            movement_counts,
            x="Old Status",
            y="Count",
            color="New Status",
            title="Status Movement"
        )

        st.plotly_chart(fig, use_container_width=True)

    else:

        st.info("Upload at least two dashboards to detect changes.")


# ---------------------------------------------------
# UPLOAD HISTORY
# ---------------------------------------------------

elif page == "Upload History":

    st.subheader("Dashboard Upload History")

    if os.path.exists(LOG_FILE):

        log = pd.read_csv(LOG_FILE)

        st.dataframe(log)

        for _, row in log.iterrows():

            file_path = os.path.join(UPLOAD_DIR, row["File Name"])

            if os.path.exists(file_path):

                with open(file_path, "rb") as f:

                    st.download_button(
                        label=f"Download {row['File Name']}",
                        data=f,
                        file_name=row["File Name"]
                    )

    else:

        st.info("No uploads recorded yet.")


# ---------------------------------------------------
# RAW DATA
# ---------------------------------------------------

elif page == "Raw Data":

    if df is not None:

        st.dataframe(df)

    else:

        st.info("Upload dashboard data to view dataset.")
