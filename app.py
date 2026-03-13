import streamlit as st
import pandas as pd
import os
from datetime import datetime
import plotly.express as px

# ---------------------------------------------------
# PAGE CONFIG
# ---------------------------------------------------

st.set_page_config(
    page_title="SOX Analytics Platform",
    page_icon="📊",
    layout="wide"
)

# ---------------------------------------------------
# CUSTOM STYLING
# ---------------------------------------------------

st.markdown("""
<style>

body {
background-color:#f5f7fb;
}

.header{
background:linear-gradient(90deg,#0f172a,#1e3a8a);
padding:30px;
border-radius:12px;
color:white;
margin-bottom:25px;
}

.metric-card{
background:white;
padding:20px;
border-radius:10px;
box-shadow:0px 3px 8px rgba(0,0,0,0.08);
}

</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------
# HEADER
# ---------------------------------------------------

st.markdown("""
<div class="header">
<h1>SOX Control Monitoring Platform</h1>
<p>Internal Audit Analytics Dashboard</p>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------
# SIDEBAR NAVIGATION
# ---------------------------------------------------

st.sidebar.title("Navigation")

page = st.sidebar.radio(
    "Select Page",
    [
        "Executive Dashboard",
        "Control Monitoring",
        "Control Analytics",
        "Raw Data"
    ]
)

# ---------------------------------------------------
# DATA STORAGE
# ---------------------------------------------------

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

# ---------------------------------------------------
# FILE UPLOAD
# ---------------------------------------------------

uploaded = st.sidebar.file_uploader(
    "Upload SOX Dashboard",
    type=["xlsx"]
)

if uploaded:

    df = pd.read_excel(uploaded)

    total_controls = len(df)
    open_controls = len(df[df["Status"] == "Open"])
    closed_controls = len(df[df["Status"] == "Closed"])

else:

    df = pd.DataFrame()
    total_controls = 0
    open_controls = 0
    closed_controls = 0

# ---------------------------------------------------
# EXECUTIVE DASHBOARD
# ---------------------------------------------------

if page == "Executive Dashboard":

    col1,col2,col3 = st.columns(3)

    with col1:
        st.metric("Total Controls", total_controls)

    with col2:
        st.metric("Open Controls", open_controls)

    with col3:
        st.metric("Closed Controls", closed_controls)

    st.markdown("---")

    if not df.empty:

        colA,colB = st.columns(2)

        with colA:

            fig = px.pie(
                df,
                names="Status",
                hole=0.45,
                title="Control Status Distribution",
                color_discrete_sequence=[
                    "#ef4444",
                    "#22c55e",
                    "#3b82f6"
                ]
            )

            st.plotly_chart(fig, use_container_width=True)

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

        st.info("Upload a SOX dashboard file to begin analysis.")

# ---------------------------------------------------
# CONTROL MONITORING
# ---------------------------------------------------

elif page == "Control Monitoring":

    st.subheader("Control Status Table")

    if not df.empty:

        status_filter = st.selectbox(
            "Filter by Status",
            ["All"] + list(df["Status"].unique())
        )

        if status_filter != "All":

            filtered = df[df["Status"] == status_filter]

        else:

            filtered = df

        st.dataframe(filtered)

    else:

        st.info("Upload dashboard data.")

# ---------------------------------------------------
# CONTROL ANALYTICS
# ---------------------------------------------------

elif page == "Control Analytics":

    if not df.empty:

        tab1,tab2 = st.tabs([
            "Control Trends",
            "Owner Analysis"
        ])

        with tab1:

            status_counts = df["Status"].value_counts().reset_index()

            fig = px.bar(
                status_counts,
                x="Status",
                y="count",
                color="Status",
                title="Control Status Overview"
            )

            st.plotly_chart(fig, use_container_width=True)

        with tab2:

            if "Owner" in df.columns:

                owner_counts = df["Owner"].value_counts().reset_index()

                fig2 = px.bar(
                    owner_counts,
                    x="Owner",
                    y="count",
                    title="Controls by Owner"
                )

                st.plotly_chart(fig2, use_container_width=True)

            else:

                st.info("Owner column not available in dataset.")

    else:

        st.info("Upload dashboard data.")

# ---------------------------------------------------
# RAW DATA
# ---------------------------------------------------

elif page == "Raw Data":

    if not df.empty:

        with st.expander("View Uploaded Dashboard"):

            st.dataframe(df)

    else:

        st.info("Upload dashboard data.")
