import streamlit as st
import pandas as pd
import os
from datetime import datetime
import plotly.express as px
from openpyxl import load_workbook
from openpyxl.styles import PatternFill

st.set_page_config(page_title="SOX Control Monitoring Platform", layout="wide")

# ---------------- FILE STORAGE ---------------- #

LATEST_FILE = "latest_data.csv"
CHANGE_FILE = "change_analysis.csv"
UPLOAD_DIR = "data/uploads"

os.makedirs(UPLOAD_DIR, exist_ok=True)

# ---------------- HEADER ---------------- #

st.markdown("""
<div style="background:linear-gradient(90deg,#0f172a,#1e3a8a);
padding:30px;border-radius:12px;color:white;margin-bottom:20px;">
<h1>SOX Control Monitoring Platform</h1>
<p>Internal Audit Analytics Dashboard</p>
</div>
""", unsafe_allow_html=True)

# ---------------- SIDEBAR ---------------- #

st.sidebar.title("Navigation")

page = st.sidebar.radio(
    "Select Page",
    ["Executive Dashboard","Change Analysis","Upload History","Raw Data"]
)

uploaded_file = st.sidebar.file_uploader("Upload SOX Dashboard", type=["xlsx"])

# ---------------- VALIDATION ---------------- #

def validate_dataset(df):

    required = [
        "PROCESS_UID","CYCLE","Test Name",
        "TESTS__TEST_SECTION","TESTS__STATUS",
        "TESTS__EFFECTIVENESS","TESTS__TESTER_USER",
        "TESTS__REVIEWER_USER","TESTS__SECONDARY_REVIEWER_USER",
        "TESTS__START_DATE","TESTS__END_DATE",
        "TESTS__DUE_DATE","PWC Reliance","Audit Team"
    ]

    missing=[c for c in required if c not in df.columns]

    if missing:
        st.error(f"Missing columns: {missing}")
        st.stop()

# ---------------- COMPARE ---------------- #

def compare_versions(old_df,new_df):

    key="Test Name"

    old_df[key]=old_df[key].astype(str).str.strip()
    new_df[key]=new_df[key].astype(str).str.strip()

    old_df=old_df.set_index(key)
    new_df=new_df.set_index(key)

    changes=[]

    for test in old_df.index.intersection(new_df.index):
        for col in new_df.columns:

            old=str(old_df.loc[test,col])
            new=str(new_df.loc[test,col])

            if old!=new:
                changes.append({
                    "Test Name":test,
                    "Field Changed":col,
                    "Old Value":old,
                    "New Value":new
                })

    return pd.DataFrame(changes)

# ---------------- LOAD EXISTING ---------------- #

latest_df = None
changes_df = None

if os.path.exists(LATEST_FILE):
    try:
        latest_df = pd.read_csv(LATEST_FILE)
    except:
        latest_df = None

if os.path.exists(CHANGE_FILE):
    try:
        changes_df = pd.read_csv(CHANGE_FILE)
        if changes_df.empty:
            changes_df = None
    except:
        changes_df = None

# ---------------- HANDLE UPLOAD ---------------- #

if uploaded_file:

    new_df = pd.read_excel(uploaded_file, sheet_name="IA data")
    validate_dataset(new_df)

    # Compare if previous exists
    if latest_df is not None:

        changes = compare_versions(latest_df.copy(), new_df.copy())

        if changes is not None and not changes.empty:
            changes.to_csv(CHANGE_FILE, index=False)
            changes_df = changes

    # Save latest always
    new_df.to_csv(LATEST_FILE, index=False)
    latest_df = new_df

    st.success("File uploaded & data persisted successfully")

# ---------------- EXECUTIVE DASHBOARD ---------------- #

if page=="Executive Dashboard":

    if latest_df is not None:

        col1,col2=st.columns(2)

        total=len(latest_df)

        open_tests=latest_df[
            latest_df["TESTS__STATUS"].astype(str)
            .str.lower()
            .str.contains("open",na=False)
        ].shape[0]

        col1.metric("Total Tests",total)
        col2.metric("Open Tests",open_tests)

        c1,c2=st.columns(2)

        with c1:
            fig=px.pie(latest_df,names="TESTS__STATUS",hole=0.45)
            st.plotly_chart(fig,use_container_width=True)

        with c2:
            fig2=px.bar(latest_df["TESTS__STATUS"].value_counts())
            st.plotly_chart(fig2,use_container_width=True)

    else:
        st.warning("No data available")

# ---------------- CHANGE ANALYSIS ---------------- #

elif page=="Change Analysis":

    st.subheader("Changes Since Last Upload")

    if changes_df is None:

        st.info("Upload at least two dashboards to detect changes")

    else:

        col1,col2=st.columns(2)

        test_filter=col1.multiselect("Test Name",changes_df["Test Name"].unique())
        field_filter=col2.multiselect("Field Changed",changes_df["Field Changed"].unique())

        filtered=changes_df.copy()

        if test_filter:
            filtered=filtered[filtered["Test Name"].isin(test_filter)]

        if field_filter:
            filtered=filtered[filtered["Field Changed"].isin(field_filter)]

        k1,k2,k3=st.columns(3)

        k1.metric("Status Changes",len(filtered[filtered["Field Changed"]=="TESTS__STATUS"]))
        k2.metric("Unique Tests Affected",filtered["Test Name"].nunique())
        k3.metric("Fields Changed",filtered["Field Changed"].nunique())

        st.dataframe(filtered,use_container_width=True)

        fig=px.bar(filtered["Field Changed"].value_counts())
        st.plotly_chart(fig,use_container_width=True)

# ---------------- HISTORY ---------------- #

elif page=="Upload History":

    if os.path.exists(LATEST_FILE):
        st.success("Latest file stored")
    else:
        st.info("No uploads yet")

# ---------------- RAW DATA ---------------- #

elif page=="Raw Data":

    if latest_df is not None:
        st.dataframe(latest_df)
