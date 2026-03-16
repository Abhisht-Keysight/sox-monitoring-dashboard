import streamlit as st
import pandas as pd
import os
from datetime import datetime
import plotly.express as px

st.set_page_config(page_title="SOX Control Monitoring Platform", layout="wide")

UPLOAD_DIR="data/uploads"
LOG_FILE="data/upload_log.csv"

os.makedirs(UPLOAD_DIR,exist_ok=True)

# --------------------------------------------------
# SESSION STATE
# --------------------------------------------------

if "df" not in st.session_state:
    st.session_state.df=None

if "changes" not in st.session_state:
    st.session_state.changes=pd.DataFrame()

# --------------------------------------------------
# HEADER
# --------------------------------------------------

st.markdown("""
<div style="background:linear-gradient(90deg,#0f172a,#1e3a8a);
padding:30px;border-radius:12px;color:white;margin-bottom:20px;">
<h1>SOX Control Monitoring Platform</h1>
<p>Internal Audit Analytics Dashboard</p>
</div>
""",unsafe_allow_html=True)

# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------

st.sidebar.title("Navigation")

page=st.sidebar.radio(
    "Select Page",
    ["Executive Dashboard","Change Analysis","Upload History","Raw Data"]
)

uploaded_file=st.sidebar.file_uploader(
    "Upload SOX Dashboard",
    type=["xlsx"]
)

# --------------------------------------------------
# VALIDATION
# --------------------------------------------------

def validate_dataset(df):

    required=[
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

    missing=[c for c in required if c not in df.columns]

    if missing:
        st.error(f"Missing columns: {missing}")
        st.stop()

# --------------------------------------------------
# SAVE FILE
# --------------------------------------------------

def save_file(uploaded_file):

    timestamp=datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    filename=f"{timestamp}_sox_dashboard.xlsx"

    path=os.path.join(UPLOAD_DIR,filename)

    with open(path,"wb") as f:
        f.write(uploaded_file.getbuffer())

    return filename,path

# --------------------------------------------------
# LOG
# --------------------------------------------------

def update_log(filename,df):

    entry={
        "Upload Time":datetime.now(),
        "File Name":filename,
        "Tests":len(df)
    }

    new=pd.DataFrame([entry])

    if os.path.exists(LOG_FILE):

        log=pd.read_csv(LOG_FILE)
        log=pd.concat([log,new],ignore_index=True)

    else:

        log=new

    log.to_csv(LOG_FILE,index=False)

# --------------------------------------------------
# LOAD FILES
# --------------------------------------------------

def load_latest_files():

    files=sorted(os.listdir(UPLOAD_DIR))
    files=[f for f in files if f.endswith(".xlsx")]

    if len(files)==0:
        return None,None

    latest_file=os.path.join(UPLOAD_DIR,files[-1])
    latest_df=pd.read_excel(latest_file,sheet_name="IA data")

    previous_df=None

    if len(files)>1:

        previous_file=os.path.join(UPLOAD_DIR,files[-2])
        previous_df=pd.read_excel(previous_file,sheet_name="IA data")

    return latest_df,previous_df

# --------------------------------------------------
# CHANGE DETECTION
# --------------------------------------------------

def compare_versions(old_df,new_df):

    key="Test Name"

    old_df[key]=old_df[key].astype(str).str.strip()
    new_df[key]=new_df[key].astype(str).str.strip()

    old_df=old_df.set_index(key)
    new_df=new_df.set_index(key)

    fields=[
        "PROCESS_UID",
        "CYCLE",
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

    changes=[]

    common=old_df.index.intersection(new_df.index)

    for test in common:

        for field in fields:

            old_val=old_df.loc[test,field]
            new_val=new_df.loc[test,field]

            if isinstance(old_val,pd.Series):
                old_val=old_val.iloc[0]

            if isinstance(new_val,pd.Series):
                new_val=new_val.iloc[0]

            if str(old_val).strip()!=str(new_val).strip():

                changes.append({
                    "Test Name":test,
                    "Field Changed":field,
                    "Old Value":old_val,
                    "New Value":new_val
                })

    new_tests=new_df.index.difference(old_df.index)

    for test in new_tests:

        changes.append({
            "Test Name":test,
            "Field Changed":"New Test",
            "Old Value":"N/A",
            "New Value":"Added"
        })

    removed_tests=old_df.index.difference(new_df.index)

    for test in removed_tests:

        changes.append({
            "Test Name":test,
            "Field Changed":"Removed Test",
            "Old Value":"Removed",
            "New Value":"N/A"
        })

    return pd.DataFrame(changes)

# --------------------------------------------------
# HANDLE UPLOAD
# --------------------------------------------------

if uploaded_file:

    filename,path=save_file(uploaded_file)

    df=pd.read_excel(path,sheet_name="IA data")

    validate_dataset(df)

    update_log(filename,df)

# --------------------------------------------------
# LOAD DATA
# --------------------------------------------------

latest_df,previous_df=load_latest_files()

if latest_df is not None:
    st.session_state.df=latest_df

if latest_df is not None and previous_df is not None:
    st.session_state.changes=compare_versions(previous_df,latest_df)

# --------------------------------------------------
# EXECUTIVE DASHBOARD
# --------------------------------------------------

if page=="Executive Dashboard":

    df=st.session_state.df

    if df is not None:

        total=len(df)

        status_counts=df["TESTS__STATUS"].value_counts()

        col1,col2=st.columns(2)

        col1.metric("Total Tests",total)
        col2.metric("Unique Cycles",df["CYCLE"].nunique())

        st.divider()

        colA,colB=st.columns(2)

        with colA:

            fig=px.pie(
                df,
                names="TESTS__STATUS",
                hole=0.45,
                title="Test Status Distribution"
            )

            st.plotly_chart(fig,use_container_width=True)

        with colB:

            status_counts=status_counts.reset_index()

            fig2=px.bar(
                status_counts,
                x="TESTS__STATUS",
                y="count",
                color="TESTS__STATUS",
                title="Status Breakdown"
            )

            st.plotly_chart(fig2,use_container_width=True)

    else:

        st.info("Upload dashboard to begin analysis")

# --------------------------------------------------
# CHANGE ANALYSIS
# --------------------------------------------------

elif page=="Change Analysis":

    changes=st.session_state.changes

    st.subheader("Changes Since Last Upload")

    if not changes.empty:

        col1,col2=st.columns(2)

        col1.metric("Total Changes",len(changes))
        col2.metric("Affected Tests",changes["Test Name"].nunique())

        st.dataframe(changes)

        change_counts=changes["Field Changed"].value_counts()

        chart_df=pd.DataFrame({
            "Change Type":change_counts.index,
            "Count":change_counts.values
        })

        fig=px.bar(
            chart_df,
            x="Change Type",
            y="Count",
            color="Change Type",
            title="Detected Changes"
        )

        st.plotly_chart(fig,use_container_width=True)

    else:

        st.info("Upload at least two dashboards to detect changes")

# --------------------------------------------------
# UPLOAD HISTORY
# --------------------------------------------------

elif page=="Upload History":

    st.subheader("Upload History")

    if os.path.exists(LOG_FILE):

        log=pd.read_csv(LOG_FILE)

        st.dataframe(log)

        for _,row in log.iterrows():

            path=os.path.join(UPLOAD_DIR,row["File Name"])

            if os.path.exists(path):

                with open(path,"rb") as f:

                    st.download_button(
                        label=f"Download {row['File Name']}",
                        data=f,
                        file_name=row["File Name"]
                    )

    else:

        st.info("No uploads recorded")

# --------------------------------------------------
# RAW DATA
# --------------------------------------------------

elif page=="Raw Data":

    df=st.session_state.df

    if df is not None:

        st.dataframe(df)

    else:

        st.info("Upload dashboard to view raw data")
