import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import os

st.set_page_config(layout="wide")

# ---------------- FILE PATHS ---------------- #

DATA_FILE = "latest_data.csv"
CHANGE_FILE = "change_analysis.csv"
LOG_FILE = "version_log.csv"

# ---------------- UI HEADER ---------------- #

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

# ---------------- LOAD FUNCTIONS ---------------- #

def load_csv_safe(path):
    try:
        df = pd.read_csv(path)
        if df.empty:
            return None
        return df
    except:
        return None

latest_df = load_csv_safe(DATA_FILE)
changes_df = load_csv_safe(CHANGE_FILE)
log_df = load_csv_safe(LOG_FILE)

# ---------------- VALIDATION ---------------- #

def validate(df):
    required = ["Test Name","TESTS__STATUS"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        st.error(f"Missing columns: {missing}")
        st.stop()

# ---------------- COMPARE ---------------- #

def compare(old_df,new_df):

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

# ---------------- UPLOAD LOGIC ---------------- #

if uploaded_file:

    df = pd.read_excel(uploaded_file, sheet_name="IA data")
    validate(df)

    if latest_df is None:
        df.to_csv(DATA_FILE,index=False)
        st.success("Base file uploaded")
    else:
        changes = compare(latest_df,df)

        df.to_csv(DATA_FILE,index=False)
        changes.to_csv(CHANGE_FILE,index=False)

        # version log
        log_entry = pd.DataFrame({
            "Timestamp":[datetime.now()],
            "Rows":[len(df)],
            "Changes":[len(changes)]
        })

        if os.path.exists(LOG_FILE):
            log_entry.to_csv(LOG_FILE,mode='a',header=False,index=False)
        else:
            log_entry.to_csv(LOG_FILE,index=False)

        st.success("Change analysis completed and saved")

    latest_df = df
    changes_df = load_csv_safe(CHANGE_FILE)
    log_df = load_csv_safe(LOG_FILE)

# ---------------- EXEC DASHBOARD ---------------- #

if page=="Executive Dashboard":

    if latest_df is not None:

        col1,col2,col3 = st.columns(3)

        col1.metric("Total Tests",len(latest_df))

        open_tests = latest_df[
            latest_df["TESTS__STATUS"].astype(str)
            .str.lower()
            .str.contains("open",na=False)
        ].shape[0]

        col2.metric("Open Tests",open_tests)

        if log_df is not None:
            col3.metric("Last Updated", str(log_df.iloc[-1]["Timestamp"])[:19])

        c1,c2 = st.columns(2)

        with c1:
            st.plotly_chart(px.pie(latest_df,names="TESTS__STATUS",hole=0.4),use_container_width=True)

        with c2:
            st.plotly_chart(px.bar(latest_df["TESTS__STATUS"].value_counts()),use_container_width=True)

    else:
        st.warning("No data available")

# ---------------- CHANGE ANALYSIS ---------------- #

elif page=="Change Analysis":

    if changes_df is None or changes_df.empty:
        st.info("No changes detected")
    else:

        st.subheader("Change Analysis")

        # FILTER
        field_filter = st.selectbox(
            "Filter by Field",
            ["All"] + sorted(changes_df["Field Changed"].unique().tolist())
        )

        filtered = changes_df.copy()

        if field_filter != "All":
            filtered = filtered[filtered["Field Changed"]==field_filter]

        # KPIs
        col1,col2,col3 = st.columns(3)

        col1.metric("Total Status Changes",
            len(filtered[filtered["Field Changed"]=="TESTS__STATUS"])
        )

        col2.metric("Unique Tests Impacted",
            filtered["Test Name"].nunique()
        )

        col3.metric("Fields Changed",
            filtered["Field Changed"].nunique()
        )

        st.dataframe(filtered,use_container_width=True)

        st.plotly_chart(
            px.bar(filtered["Field Changed"].value_counts(),
            title="Changes by Field"),
            use_container_width=True
        )

        # EXPORT
        def highlight(row):
            return ['background-color: #ffe6e6']*len(row)

        styled = filtered.style.apply(highlight,axis=1)

        export_file="change_output.xlsx"
        styled.to_excel(export_file,index=False)

        with open(export_file,"rb") as f:
            st.download_button(
                "Download Change Analysis",
                f,
                file_name="change_analysis.xlsx"
            )

# ---------------- HISTORY ---------------- #

elif page=="Upload History":

    if log_df is not None:
        st.dataframe(log_df,use_container_width=True)
    else:
        st.info("No upload history available")

# ---------------- RAW ---------------- #

elif page=="Raw Data":

    if latest_df is not None:
        st.dataframe(latest_df,use_container_width=True)
    else:
        st.info("No data available")
