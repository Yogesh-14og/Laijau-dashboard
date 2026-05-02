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
    import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials
import datetime

# --- CONFIG & STYLING ---
st.set_page_config(page_title="Laijau Dashboard", layout="wide")

# १. CSS FOR PREMIUM LOOK (NO EMOJIS)
st.markdown("""
    <style>
    [data-testid="stSidebar"] { background-color: #0E1117; border-right: 1px solid #333; }
    .stMetric { background-color: #1E1E1E; padding: 15px; border-radius: 10px; border: 1px solid #333; }
    div.stButton > button { width: 100%; border-radius: 5px; height: 3em; }
    </style>
""", unsafe_allow_html=True)

# २. GOOGLE SHEETS CONNECTION
try:
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_file("credentials.json", scopes=scope)
    client = gspread.authorize(creds)
    sheet_id = "1NEXA1QP-JGcNO9DYBBSg6PNpr-0IZp10h_E7b2RD7oY" 
    
    sh = client.open_by_key(sheet_id)
    
    # Sales Data (Index 0)
    ws_new = sh.worksheet("New showroom")
    ws_old = sh.worksheet("Old Showroom")
    df_new=pd.DataFrame(ws_new.get_all_records())
    df_old=pd.DataFrame(ws_old.get_all_records())
    df_sale_raw=pd.concat([df_new, df_old], ignore_index=True)
    df_sale_raw['Date'] = pd.to_datetime(df_sale_raw['Date'])
    
    # Stock Data (Index 2)
    ws_stock = sh.worksheet("stock")
    df_stock_raw = pd.DataFrame(ws_stock.get_all_records())
except Exception as e:
    st.error(f"Connection Error: {e}")
    st.stop()

# --- SIDEBAR NAVIGATION ---
with st.sidebar:
    st.markdown("""
        <div style='text-align: center; padding: 10px; background-color: #1E1E1E; border-radius: 10px; margin-bottom: 20px; border: 1px solid #00CC96;'>
            <h1 style='color: #00CC96; margin: 0; font-family: sans-serif;'>LAIJAU</h1>
            <p style='color: #888; font-size: 12px; margin: 0;'>Business Analytics v2.0</p>
        </div>
    """, unsafe_allow_html=True)

    app_mode = st.radio("Navigation", ["Sales Dashboard", "Stock Management", "Attendance"])
    st.divider()
    st.success("System Online")
    st.caption(f"Admin: Yogesh Khatri | {datetime.date.today()}")

if app_mode == "Sales Dashboard":
    st.title("Sales Analysis")
    
    # यदि डाटा नै छैन भने खाली देखाउने
    if df_sale_raw.empty:
        st.warning("गुगल सिटमा सेल्स डाटा भेटिएन। कृपया सिटको पहिलो रो मा 'Date', 'Showroom', र 'Total' लेखिएको छ कि छैन चेक गर।")
    else:
        with st.expander("Filters", expanded=True):
            showroom_filter = st.selectbox("Select View", ["Both", "New Showroom", "Old Showroom"], index=0)

        df_f = df_sale_raw.copy()
        if showroom_filter != "Both":
            df_f = df_f[df_f["Showroom"] == showroom_filter]

        if not df_f.empty:
            m1, m2, m3 = st.columns(3)
            total_revenue = df_f['Total'].sum()
            best_day_row = df_f.loc[df_f['Total'].idxmax()]
            
            m1.metric("Total Revenue", f"Rs {total_revenue:,.0f}")
            m2.metric("Best Sales Day", f"{best_day_row['Date'].strftime('%b %d')}", f"Rs {best_day_row['Total']:,.0f}")
            m3.metric("Avg Sale", f"Rs {df_f['Total'].mean():,.0f}")

            st.subheader("Daily Sales Trend")
            daily_sales = df_f.groupby('Date')['Total'].sum().reset_index()
            fig_daily = px.area(daily_sales, x="Date", y="Total", template="plotly_dark", 
                                line_shape="spline", color_discrete_sequence=['#00CC96'])
            st.plotly_chart(fig_daily, use_container_width=True)
# --- 2. STOCK MANAGEMENT (FIXED CONFLICT) ---
elif app_mode == "Stock Management":
    st.title("Stock Inventory Control")
    selected_room = st.radio("Select Showroom", ["Old Showroom", "New Showroom"], horizontal=True)
    
    if selected_room == "Old Showroom":
        suppliers = ["Prasiddha", "Max", "SK", "Citizen"]
        category = "Shoes"
    else:
        category = st.selectbox("Category", ["Sports Shoes", "Clothes"])
        suppliers = ["Leo", "Megha Traders", "New Road"] if category == "Sports Shoes" else ["SM", "Devkota", "Star Denim", "New Road"]

    with st.form("stock_form"):
        st.subheader(f"Add Entry for {selected_room}")
        c1, c2, c3 = st.columns(3)
        f_supp = c1.selectbox("Supplier/Factory", suppliers)
        f_code = c2.text_input("Item/Jutta Code")
        f_qty = c3.number_input("Quantity", min_value=1, step=1)
        
        if st.form_submit_button("Update Stock (Restock)"):
            try:
                new_row = [str(datetime.date.today()), selected_room, category, f_supp, f_code, f_qty]
                ws_stock.append_row(new_row)
                st.success(f"Successfully added {f_qty} units of {f_code} to Google Sheet!")
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")
    st.divider()
    st.subheader("Current Inventory Status")
    df_display = df_stock_raw.copy()
    df_display.insert(0, 'S.N.', range(1, len(df_display) + 1))
    st.dataframe(df_display, use_container_width=True, hide_index=True)
elif app_mode == "Attendance":
    st.title("Staff HR Management")
    staff_names = ["Pradip Ramtel", "Niru Mishra", "Yogesh Khatri", "Aavash Bogati", "Sahanshila Shrestha", "Prakash Karki"]
    selected_staff = st.selectbox("Select Staff Name", staff_names)
    
    col1, col2 = st.columns(2)
    today_str = str(datetime.date.today())
    ws_at = sh.worksheet("Attendance")

    if col1.button("Punch IN"):
        now = datetime.datetime.now()
        status = "Late" if now.time() > datetime.time(11, 0) else "On Time"
        try:
            ws_at.append_row([today_str, selected_staff, now.strftime("%I:%M %p"), "", status])
            st.success(f"Check-in Successful: {now.strftime('%I:%M %p')}")
            st.cache_data.clear()
        except Exception as e:
            st.error(f"Error: {e}")

    if col2.button("Punch OUT", use_container_width=True):
        try:
            all_records = ws_at.get_all_records()
            found_row_index = None
            today = datetime.date.today()न
            t_dash = today.strftime("%Y-%m-%d")
            t_slash = f"{today.month}/{today.day}/{today.year}"
            possible_dates = [t_dash, t_slash]
            for i, row in enumerate(all_records):
                clean_row = {str(k).strip(): v for k, v in row.items()}
                s_staff = str(clean_row.get('Staff Name', '')).strip()
                s_out = str(clean_row.get('Out time', '')).strip()
                s_date = str(clean_row.get('Date', '')).strip()
                if s_staff == selected_staff and (s_out == "" or s_out == "None" or s_out == "nan"):
                    if s_date in possible_dates or s_date == "":
                        found_row_index = i + 2
                        break
        
            if found_row_index:
                now_out = datetime.datetime.now().strftime("%I:%M %p")
                ws_at.update_cell(found_row_index, 4, now_out) 
                ws_at.update_cell(found_row_index, 5, "Completed")             
                st.warning(f"{selected_staff} Out भयो! समय: {now_out}")
                st.cache_data.clear()
                st.rerun()
            else:
                st.error("डाटा भेटिएन! एकचोटी सिटमा गएर 'In' भएको छ कि छैन हेर त।")
            
        except Exception as e:
            st.error(f"केही गडबड भयो: {e}")
