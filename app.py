import streamlit as st
import pandas as pd
import os
from datetime import datetime
import plotly.express as px
from streamlit_plotly_events import plotly_events

# -----------------------------------------------------
# PAGE CONFIG
# -----------------------------------------------------

st.set_page_config(
    page_title="SOX Control Monitoring Platform",
    layout="wide"
)

# -----------------------------------------------------
# STORAGE CONFIG
# -----------------------------------------------------

UPLOAD_DIR = "data/uploads"
LOG_FILE = "data/upload_log.csv"

os.makedirs(UPLOAD_DIR, exist_ok=True)

# -----------------------------------------------------
# HEADER
# -----------------------------------------------------

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

# -----------------------------------------------------
# SIDEBAR NAVIGATION
# -----------------------------------------------------

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

# -----------------------------------------------------
# SAVE UPLOADED FILE
# -----------------------------------------------------

def save_uploaded_file(uploaded_file):

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    filename = f"{timestamp}_sox_dashboard.xlsx"

    path = os.path.join(UPLOAD_DIR, filename)

    with open(path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    return filename, path


# -----------------------------------------------------
# UPDATE UPLOAD LOG
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
# LOAD PREVIOUS VERSION (SAFE)
# -----------------------------------------------------

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


# -----------------------------------------------------
# COMPARE VERSIONS
# -----------------------------------------------------

def compare_versions(old_df, new_df):

    old_df = old_df.set_index("Control ID")
    new_df = new_df.set_index("Control ID")

    changes = []

    for cid in old_df.index.intersection(new_df.index):

        old_status = old_df.loc[cid]["Status"]
        new_status = new_df.loc[cid]["Status"]

        if old_status != new_status:

            changes.append({
                "Control ID": cid,
                "Old Status": old_status,
                "New Status": new_status
            })

    return pd.DataFrame(changes)


# -----------------------------------------------------
# HANDLE FILE UPLOAD
# -----------------------------------------------------

df = None
changes = pd.DataFrame()

if uploaded_file:

    filename, path = save_uploaded_file(uploaded_file)

    df = pd.read_excel(path)

    update_upload_log(filename, df)

    previous_df = load_previous_file()

    if previous_df is not None:

        changes = compare_versions(previous_df, df)

# -----------------------------------------------------
# EXECUTIVE DASHBOARD
# -----------------------------------------------------

if page == "Executive Dashboard":

    if df is not None:

        total_controls = len(df)

        open_controls = len(df[df["Status"] == "Open"])

        closed_controls = len(df[df["Status"] == "Closed"])

        col1,col2,col3 = st.columns(3)

        col1.metric("Total Controls", total_controls)
        col2.metric("Open Controls", open_controls)
        col3.metric("Closed Controls", closed_controls)

        st.markdown("---")

        colA,colB = st.columns(2)

        with colA:

            fig = px.pie(
                df,
                names="Status",
                hole=0.45,
                title="Control Status Distribution"
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
                title="Status Breakdown"
            )

            st.plotly_chart(fig2, use_container_width=True)

    else:

        st.info("Upload a SOX dashboard to begin analysis.")


# -----------------------------------------------------
# CHANGE ANALYSIS
# -----------------------------------------------------

elif page == "Change Analysis":

    st.subheader("Changes Since Last Upload")

    if not changes.empty:

        col1,col2 = st.columns(2)

        col1.metric("Total Changes", len(changes))
        col2.metric("Affected Controls", changes["Control ID"].nunique())

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

        st.info("No changes detected or only one upload exists.")


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

    if df is not None:

        st.dataframe(df)

    else:

        st.info("Upload dashboard data.")
