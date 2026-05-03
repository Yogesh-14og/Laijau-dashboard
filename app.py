import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials
import datetime
import time

# --- CONFIG & STYLING ---
st.set_page_config(page_title="Laijau Dashboard", layout="wide")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "share_password" not in st.session_state:
    st.session_state.share_password = False

# ---------------- LOGIN ----------------
def login():
    col1, col2 = st.columns([1.5,1])
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

# --- CSS FOR PREMIUM LOOK ---
st.markdown("""
    <style>
    [data-testid="stSidebar"] { background-color: #0E1117; border-right: 1px solid #333; }
    .stMetric { background-color: #1E1E1E; padding: 15px; border-radius: 10px; border: 1px solid #333; }
    div.stButton > button { width: 100%; border-radius: 5px; height: 3em; }
    </style>
""", unsafe_allow_html=True)

# ---------------- GOOGLE SHEETS CONNECTION ----------------
try:
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_file("credentials.json", scopes=scope)
    client = gspread.authorize(creds)
    sheet_id = "1NEXA1QP-JGcNO9DYBBSg6PNpr-0IZp10h_E7b2RD7oY" 
    sh = client.open_by_key(sheet_id)
    
    # Sales Data Fetch
    ws_new = sh.worksheet("New Showroom")
    ws_old = sh.worksheet("Old Showroom")
    df_new = pd.DataFrame(ws_new.get_all_records())
    df_old = pd.DataFrame(ws_old.get_all_records())
    df_sale_raw = pd.concat([df_new, df_old], ignore_index=True)
    
    # Data Cleaning for Charts
    if not df_sale_raw.empty:
        df_sale_raw['Date'] = pd.to_datetime(df_sale_raw['Date'])
        df_sale_raw['Month_Name'] = df_sale_raw['Date'].dt.strftime('%b')
        df_sale_raw['Month_Period'] = df_sale_raw['Date'].dt.to_period('M').astype(str)
    
    # Stock Data Fetch
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
    
    if st.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.share_password = False
        st.rerun()
if app_mode == "Sales Dashboard":
    st.title("Sales Analytics")
    st.markdown("### Dashboard Controls")
    ctrl_col1, ctrl_col2, ctrl_col3 = st.columns(3)
    
    with ctrl_col1:
        Showroom = st.selectbox("Select Showroom", ["Both", "New Showroom", "Old Showroom"])
    with ctrl_col2:
        view = st.selectbox("Quick View", ["Full Report", "Daily Trend", "Monthly Growth", "Payment Mode"])
    with ctrl_col3:
        min_date = df_sale_raw['Date'].min().date()
        max_date = df_sale_raw['Date'].max().date()
        date_range = st.date_input("Filter Date Range", value=(min_date, max_date))
    df = df_sale_raw.copy()
    if Showroom != "Both":
        df = df[df["Showroom"] == Showroom]
    
    if len(date_range) == 2:
        df = df[(df['Date'].dt.date >= date_range[0]) & (df['Date'].dt.date <= date_range[1])]

    st.divider()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Revenue", f"Rs {df['Total'].sum():,.0f}")
    m2.metric("Total Cash", f"Rs {df['Cash'].sum():,.0f}")
    m3.metric("Total Online", f"Rs {df['Online'].sum():,.0f}")
    m4.metric("Transactions", len(df))
    st.divider()
    if view in ["Full Report", "Daily Trend"]:
        st.subheader("Daily Sales Trend")
        daily_sales = df.groupby(df["Date"].dt.date)["Total"].sum().reset_index()
        fig_daily = px.line(daily_sales, x="Date", y="Total", markers=True, color_discrete_sequence=['#00CC96'])
        st.plotly_chart(fig_daily, use_container_width=True)
    if view in ["Full Report", "Monthly Growth"]:
       if view == "Full Report" or view == "Monthly Growth":
            st.subheader("Monthly Growth (%)")
            monthly_sales = df.groupby(["Month_Period", "Month_Name"])["Total"].sum().reset_index()
            monthly_sales = monthly_sales.sort_values("Month_Period")
            monthly_sales["Growth %"] = monthly_sales["Total"].pct_change().fillna(0) * 100
            fig_growth = px.bar(monthly_sales, x="Month_Name", y="Growth %",
                        color="Growth %", text_auto=".1f",
                        color_continuous_scale="RdYlGn",
                        title="Month-over-Month Growth")
            st.plotly_chart(fig_growth, use_container_width=True)
    if view in ["Full Report", "Payment Mode"]:
        st.subheader("Cash vs Online Breakdown")
        p_trend = df.groupby(df["Date"].dt.date)[["Cash", "Online"]].sum().reset_index()
        fig_pay = px.area(p_trend, x="Date", y=["Cash", "Online"])
        st.plotly_chart(fig_pay, use_container_width=True)
elif app_mode == "Stock Management":
    st.title("Stock Inventory Control")
    selected_room = st.radio("Select Showroom", ["Old Showroom", "New Showroom"], horizontal=True)
    trans_type = st.radio("Action", ["Stock In (+)", "Stock Out (-)"], index=0, horizontal=True)
    if selected_room == "Old Showroom":
        suppliers = ["Prasiddha", "Max", "SK", "Citizen", "Local Market"]
        category = "Shoes"
    else:
        category = st.selectbox("Category", ["Sports Shoes", "Clothes", "Accessories"])
        suppliers = ["Leo", "Megha Traders", "New Road"] if category == "Sports Shoes" else ["SM", "Devkota", "Star Denim", "New Road"]
    with st.form("stock_form", clear_on_submit=True):
        st.subheader(f"Inventory Entry: {selected_room}")
        c1, c2, c3 = st.columns(3)
        f_supp = c1.selectbox("Supplier/Factory", suppliers)
        f_code = c2.text_input("Item/Jutta Code")
        f_qty = c3.number_input("Quantity", min_value=1, step=1)
        if st.form_submit_button("Submit Transaction"):
            if not f_code:
                st.warning("Item code empty!")
            else:
                try:
                    all_rows = ws_stock.get_all_values()
                    found_row_index = None
                    current_qty = 0
                    for i, row in enumerate(all_rows[1:]):
                        if str(row[1]).strip().upper() == selected_room.strip().upper() and \
                           str(row[4]).strip().upper() == f_code.strip().upper():
                            found_row_index = i + 2
                            current_qty = int(row[5]) if str(row[5]).isdigit() else 0
                            break
                    if found_row_index:
                        new_total = current_qty + f_qty if trans_type == "Stock In (+)" else current_qty - f_qty
                        if new_total < 0:
                            st.error("Insufficient Stock!")
                        else:
                            ws_stock.update_cell(found_row_index, 6, new_total)
                            st.success(f"Updated: {f_code} total is now {new_total}")
                    elif trans_type == "Stock In (+)":
                        ws_stock.append_row([str(datetime.date.today()), selected_room, category, f_supp, f_code, f_qty])
                        st.success(f"New Item {f_code} added!")
                    else:
                        st.error("Item not found for Stock Out.")
                    
                    st.cache_data.clear()
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

    st.divider()
    st.subheader("Current Inventory Status")
    st.dataframe(df_stock_raw, use_container_width=True, hide_index=True)

# ---------------- ATTENDANCE ----------------
elif app_mode == "Attendance":
    st.title("Staff Attendance")
    staff_names = ["Pradip Ramtel", "Niru Mishra", "Yogesh Khatri", "Aavash Bogati", "Sahanshila Shrestha", "Prakash Karki"]
    selected_staff = st.selectbox("Staff Name", staff_names)
    ws_at = sh.worksheet("Attendance")
    
    c1, c2 = st.columns(2)
    if c1.button("Punch IN", use_container_width=True):
        now = datetime.datetime.now()
        status = "Late" if now.time() > datetime.time(11, 0) else "On Time"
        ws_at.append_row([str(datetime.date.today()), selected_staff, now.strftime("%I:%M %p"), "", status])
        st.toast(f"Clocked In: {now.strftime('%I:%M %p')}")
        st.cache_data.clear()
        st.rerun()

    if c2.button("Punch OUT", use_container_width=True):
        all_records = ws_at.get_all_records()
        for i, row in enumerate(all_records):
            if str(row.get('Staff Name')) == selected_staff and not str(row.get('Out time')):
                ws_at.update_cell(i + 2, 4, datetime.datetime.now().strftime("%I:%M %p"))
                ws_at.update_cell(i + 2, 5, "Completed")
                st.toast("Clocked Out Successfully!")
                st.cache_data.clear()
                st.rerun()
                breakसिटमा गएर 'In' भएको छ कि छैन हेर त।")
            
        except Exception as e:
            st.error(f"केही गडबड भयो: {e}")
