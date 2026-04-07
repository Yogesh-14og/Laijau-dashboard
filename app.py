import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import time
from gspread.exceptions import APIError

# ---------------- CONFIG ----------------
st.set_page_config(page_title="Laijau Dashboard", layout="wide")

# ---------------- SESSION ----------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "share_password" not in st.session_state:
    st.session_state.share_password = False

# ---------------- LOGIN ----------------
def login():
    col1, col2 = st.columns([2,1])
    with col1:
        st.markdown("# LAIJAU.COM DASHBOARD")
        st.write("Welcome back! Please login to access the dashboard.")
    with col2:
        user = st.text_input("Username")
        pw = st.text_input("Password", type="password")
        if st.button("Login", use_container_width=True):
            if user == "admin" and pw == "123":
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("Invalid credentials")

if not st.session_state.logged_in:
    login()
    st.stop()

# ---------------- SHARE ACCESS ----------------
share_pass = "laijau2026"
if not st.session_state.share_password:
    st.title("Share Access Required")
    share_input = st.text_input("Enter access password", type="password")
    if st.button("Submit"):
        if share_input == share_pass:
            st.session_state.share_password = True
            st.rerun()
        else:
            st.error("Incorrect password")
    st.stop()

# ---------------- LOAD DATA (OPTIMIZED) ----------------
@st.cache_data(ttl=300)
def load_data():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    client = gspread.authorize(creds)
    sh = client.open_by_key("1NEXA1QP-JGcNO9DYBBSg6PNpr-0IZp10h_E7b2RD7oY")

    try:
        dfs = []
        for i in range(2):
            ws = sh.get_worksheet(i)
            temp_df = pd.DataFrame(ws.get_all_records())
            temp_df["Showroom"] = "New Showroom" if i == 0 else "Old Showroom"
            dfs.append(temp_df)
        
        df = pd.concat(dfs, ignore_index=True)
        
        # Clean Numbers
        for col in ["Cash", "Online", "Total"]:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
        
        # Fix Date
        df["Date"] = pd.to_datetime(df["Date"].astype(str) + " 2026", errors="coerce")
        df = df.dropna(subset=["Date"]).sort_values("Date")
        
        # Add Time Periods
        df["Day"] = df["Date"].dt.date
        df["Month_Period"] = df["Date"].dt.strftime("%Y-%m") # Standard Format for sorting
        df["Month_Name"] = df["Date"].dt.strftime("%b %Y")
        
        return df
    except Exception as e:
        st.error(f"Error connecting to Sheets: {e}")
        return None

df_raw = load_data()
if df_raw is None: st.stop()

# ---------------- SIDEBAR ----------------
st.sidebar.title("Dashboard Controls")
showroom = st.sidebar.selectbox("Select Showroom", ["Both", "New Showroom", "Old Showroom"])
view = st.sidebar.selectbox("Quick View", ["Full Report", "Daily Trend", "Monthly Growth", "Payment Mode"])
refresh = st.sidebar.checkbox("Auto refresh (15s)")

# ---------------- FILTER LOGIC ----------------
df = df_raw.copy()
if showroom != "Both":
    df = df[df["Showroom"] == showroom]

# Date Filter
min_d, max_d = df["Date"].min().date(), df["Date"].max().date()
date_range = st.sidebar.date_input("Filter by Date", value=(min_d, max_d))

if isinstance(date_range, tuple) and len(date_range) == 2:
    start, end = date_range
    df = df[(df["Date"].dt.date >= start) & (df["Date"].dt.date <= end)]

# ---------------- METRICS ----------------
st.title(f"{showroom} Performance")
m1, m2, m3, m4 = st.columns(4)
m1.metric("Total Revenue", f"Rs {df['Total'].sum():,.0f}")
m2.metric("Avg Daily Sales", f"Rs {df.groupby('Day')['Total'].sum().mean():,.0f}")
m3.metric("Transaction Count", len(df))
m4.metric("Active Days", df["Day"].nunique())

st.divider()

# ---------------- STYLE FUNCTION ----------------
def apply_style(fig):
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white"),
        margin=dict(l=20, r=20, t=40, b=20),
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor="#1e293b")
    )
    return fig

# ---------------- DASHBOARD VIEWS ----------------
if view == "Full Report" or view == "Daily Trend":
    st.subheader("Sales Trend Analysis")
    daily_sales = df.groupby("Day")["Total"].sum().reset_index()
    fig_daily = px.line(daily_sales, x="Day", y="Total", markers=True, 
                        line_shape="spline", title="Daily Sales (Rs)")
    st.plotly_chart(apply_style(fig_daily), use_container_width=True)

if view == "Full Report" or view == "Monthly Growth":
    st.subheader("Monthly Growth (%)")
    monthly_sales = df.groupby(["Month_Period", "Month_Name"])["Total"].sum().reset_index()
    monthly_sales = monthly_sales.sort_values("Month_Period")
    monthly_sales["Growth %"] = monthly_sales["Total"].pct_change().fillna(0) * 100
    
    fig_growth = px.bar(monthly_sales, x="Month_Name", y="Growth %",
                        color="Growth %", text_auto=".1f",
                        color_continuous_scale="RdYlGn",
                        title="Month-over-Month Growth")
    st.plotly_chart(apply_style(fig_growth), use_container_width=True)

if view == "Full Report" or view == "Payment Mode":
    st.subheader("Payment Breakdown")
    c1, c2 = st.columns([1, 2])
    with c1:
        fig_pie = px.pie(values=[df["Cash"].sum(), df["Online"].sum()], 
                         names=["Cash", "Online"], hole=0.4,
                         color_discrete_sequence=["#00f2fe", "#4facfe"])
        st.plotly_chart(apply_style(fig_pie), use_container_width=True)
    with c2:
        pay_trend = df.groupby("Day")[["Cash", "Online"]].sum().reset_index()
        fig_pay_line = px.area(pay_trend, x="Day", y=["Cash", "Online"], 
                               title="Cash vs Online Flow")
        st.plotly_chart(apply_style(fig_pay_line), use_container_width=True)

# ---------------- DATA TABLE & ANALYTICS ----------------
st.divider()
col_a, col_b = st.columns(2)

with col_a:
    st.subheader("Top 5 Sales Days")
    top_days = df.groupby("Day")["Total"].sum().reset_index().sort_values("Total", ascending=False).head(5)
    st.dataframe(top_days, hide_index=True, use_container_width=True)

with col_b:
    st.subheader("📥 Export Data")
    st.write("Download the filtered dataset for further analysis.")
    st.download_button("Download CSV", df.to_csv(index=False), "sales_report.csv", "text/csv", use_container_width=True)

# ---------------- FOOTER & REFRESH ----------------
if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
    st.session_state.share_password = False
    st.rerun()

if refresh:
    time.sleep(15)
    st.rerun()