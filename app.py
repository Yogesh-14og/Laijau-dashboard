import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import time as t
from datetime import datetime, time
import pytz

st.set_page_config(page_title="Laijau Dashboard v2.0", layout="wide")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

@st.cache_resource
def get_gspread_client():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_info = st.secrets["google_sheets"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_info, scope)
    return gspread.authorize(creds)

client = get_gspread_client()
sheet_id = st.secrets["spreadsheet_id"]

def login_ui():
    st.markdown("""
    <style>
    [data-testid="stVerticalBlock"] > div:has(div.stFrame) {
        background-color: blue; 
        padding: 1rem;
        border-radius: 15px;
        border: 1px solid #333;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    }
    .stTitle {
        font-size: 3.5rem !important;
        font-weight: 800 !important;
        color: #FFFFFF;
    }
    </style>
    """, unsafe_allow_html=True)
    col1, col2 = st.columns([1.5, 1], gap="medium")
    with col1:
        st.title("LAIJAU.COM")
        st.subheader("Welcome to the **Ultimate Sales & Inventory** Dashboard")
        st.info("**Tip:** Always log out after your session to keep the data secure.")
        st.write("---")
    with col2:
        with st.container(border=True):
            st.header("Admin Login")
            st.write("Enter credentials to unlock")
            user = st.text_input("Username", placeholder="e.g. admin", key="login_user")
            pw = st.text_input("Password", type="password", placeholder="••••••••", key="login_pw")
            access_code = st.text_input("System Access Code", type="password", placeholder="Enter Access Code", key="login_access")
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Unlock Dashboard", use_container_width=True):
                if not user or not pw or not access_code:
                    st.warning("Please fill all the fields!")
                else:
                    try:
                        s_user = str(st.secrets["passwords"]["admin_user"])
                        s_pw = str(st.secrets["passwords"]["admin_password"])
                        s_codes = [str(c) for c in st.secrets["employee_codes"]["codes"]]
                        u_match = (user == s_user)
                        p_match = (pw == s_pw)
                        a_match = (str(access_code) in s_codes)
                        if u_match and p_match and a_match:
                            st.session_state.logged_in = True
                            st.success("Access Granted! Loading...")
                            t.sleep(1)
                            st.rerun()
                        else:
                            st.error("Invalid Credentials!")
                            if not u_match: st.toast("Check Username ")
                            if not p_match: st.toast("Check Password ")
                            if not a_match: st.toast("Check Access Code ")         
                    except Exception as e:
                        st.error(f"Configuration Error: {e}")
                        st.info("Tip: Make sure .streamlit/secrets.toml is saved and formatted correctly.")

if not st.session_state.logged_in:
    login_ui()
    st.stop()

# 🌟 गुगललाई बचाउन मुख्य डाटा लोड फंक्सन
def load_all_data_from_google():
    if not sheet_id:
        return pd.DataFrame(), pd.DataFrame()
    sh = client.open_by_key(sheet_id)
    try:
        sales_dfs = []
        for i in range(2):
            ws = sh.get_worksheet(i)
            data = ws.get_all_records()
            if data:
                tdf = pd.DataFrame(data)
                tdf["Showroom"] = "New Showroom" if i == 0 else "Old Showroom"
                sales_dfs.append(tdf)
        df_sales = pd.concat(sales_dfs, ignore_index=True) if sales_dfs else pd.DataFrame()
        for col in ["Cash", "Online", "Total"]:
            if col in df_sales.columns:
                df_sales[col] = pd.to_numeric(df_sales[col], errors="coerce").fillna(0)
        df_sales["Date"] = pd.to_datetime(df_sales["Date"].astype(str) + " 2026", errors='coerce')
        df_sales = df_sales.dropna(subset=["Date"]).sort_values("Date")
        
        ws_stock = sh.get_worksheet(2)
        df_stock = pd.DataFrame(ws_stock.get_all_records())
        return df_sales, df_stock
    except Exception as e:
        st.error(f"Initial Cloud Load Error: {e}")
        return pd.DataFrame(), pd.DataFrame()

# 🌟 डाटालाई सेसन स्टेटमा राख्ने ताकि पटक-पटक गुगलबाट डाउनलोड गर्नुनपरोस् (Anti-429 Logic)
if "sales_data" not in st.session_state or "stock_data" not in st.session_state:
    with st.spinner("Fetching data securely from Google Sheets..."):
        df_sales_raw, df_stock_raw = load_all_data_from_google()
        st.session_state.sales_data = df_sales_raw
        st.session_state.stock_data = df_stock_raw
else:
    df_sales_raw = st.session_state.sales_data
    df_stock_raw = st.session_state.stock_data

with st.sidebar:
    st.markdown("""
        <div style='text-align: center; padding: 10px; background-color: #1E1E1E; border-radius: 10px; margin-bottom: 20px; border: 1px solid #333;'>
            <h1 style='color: #00CC96; margin: 0;'>Laijau.com</h1>
                <h2 style='color: #888; margin: 0;'>Sales & Inventory Dashboard</h2>
                <p style='color: #888; font-size: 12px; margin: 0;'>Business Analytics v2.0</p>
            </div>
        """, unsafe_allow_html=True)
    st.markdown("<h3 class='sidebar-nav' style='color: #F8FAFC;'>Navigation</h3>", unsafe_allow_html=True)
    app_mode = st.radio("Select Module", ["Sales Dashboard", "Stock Management", "Attendance"])
    st.divider()
    
    # 🔄 जतिबेला इच्छा लाग्छ, म्यानुअल रिफ्रेस गर्न साइडबारमा बटन
    if st.button("🔄 Force Refresh Cloud Data", use_container_width=True):
        del st.session_state.sales_data
        del st.session_state.stock_data
        st.rerun()

    st.markdown("### System Status")
    st.success("🟢 System Online")
    refresh = st.checkbox("Auto-refresh (Live Mode)")
    if st.button("Logout", use_container_width=True):
        if "sales_data" in st.session_state: del st.session_state.sales_data
        if "stock_data" in st.session_state: del st.session_state.stock_data
        st.session_state.logged_in = False
        st.rerun()
        st.markdown("---")
        st.caption(f"Logged in as: Admin | {datetime.date.today().strftime('%Y-%m-%d')}")  

if app_mode == "Sales Dashboard":
    st.title("Sales Analysis")    
    with st.expander("Filters", expanded=True):
        showroom_filter = st.selectbox(
            "Select Showroom View", 
            ["Both", "New Showroom", "Old Showroom"],
            index=0  
        )
    df_f = df_sales_raw.copy()
    if showroom_filter != "Both":
        df_f = df_f[df_f["Showroom"] == showroom_filter]
    if not df_f.empty:
        m1, m2, m3 = st.columns(3)
        best_day_row = df_f.loc[df_f['Total'].idxmax()]
        best_day_val = best_day_row['Date'].strftime('%b %d')
        best_day_amt = best_day_row['Total']        
        m1.metric("Total Revenue", f"Rs {df_f['Total'].sum():,.0f}")
        m2.metric("Best Sales Day", f"{best_day_val}", f"Rs {best_day_amt:,.0f}")
        m3.metric("Avg Sale/Order", f"Rs {df_f['Total'].mean():,.0f}")
        st.subheader("Daily Sales Trend")
        daily_sales = df_f.groupby('Date')['Total'].sum().reset_index()
        fig_daily = px.area(daily_sales, x="Date", y="Total", 
                            title="Daily Revenue Fluctuations (2026)",
                            labels={"Total": "Revenue (Rs)", "Date": "Day"},
                            template="plotly_dark",
                            line_shape="spline",
                            color_discrete_sequence=["#7839D6"]) 
        st.plotly_chart(fig_daily, use_container_width=True)
        st.subheader("Monthly Sales Trend")
        df_f['Month'] = df_f['Date'].dt.strftime('%B')
        monthly_sales = df_f.groupby('Month')['Total'].sum().reset_index()
        month_order = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
        monthly_sales['Month'] = pd.Categorical(monthly_sales['Month'], categories=month_order, ordered=True)
        monthly_sales = monthly_sales.sort_values('Month')
        fig_month = px.line(monthly_sales, x="Month", y="Total", markers=True, title="Revenue Growth (2026)", template="plotly_dark")
        st.plotly_chart(fig_month, use_container_width=True)
        st.subheader("Payment Mode Analysis")
        c1, c2 = st.columns([2, 1])
        with c1:
            pay_sums = pd.DataFrame({"Method": ["Cash", "Online"], "Amount": [df_f["Cash"].sum(), df_f["Online"].sum()]})
            fig_pay = px.pie(pay_sums, values="Amount", names="Method", hole=0.5, color_discrete_map={'Cash':'#EF553B', 'Online':'#00CC96'})
            st.plotly_chart(fig_pay, use_container_width=True)
        with c2:
            st.info(f"Online Pay: { (df_f['Online'].sum() / df_f['Total'].sum())*100:.1f}%")
            st.success(f"Cash Pay: { (df_f['Cash'].sum() / df_f['Total'].sum())*100:.1f}%")

elif app_mode == "Stock Management":
    st.title("Stock Inventory Control")
    if 'selected_room' not in st.session_state:
        st.session_state.selected_room = "Old Showroom"
        
    nepal_tz = pytz.timezone('Asia/Kathmandu')
    today_nepal = datetime.now(nepal_tz).strftime("%Y-%m-%d")
    
    sh = client.open_by_key(sheet_id)
    ws_stock = sh.worksheet("stock")
    ws_supp = sh.worksheet("Suppliers")
    supp_df = pd.DataFrame(ws_supp.get_all_records())
    
    selected_room = st.radio("Select Showroom", ["Old Showroom", "New Showroom"], 
                             index=0 if st.session_state.selected_room == "Old Showroom" else 1,
                             horizontal=True)
    st.session_state.selected_room = selected_room
    trans_type = st.radio("Action", ["Stock In (+)", "Stock Out (-)"], index=0, horizontal=True)
    
    with st.form("stock_form", clear_on_submit=True):
        st.subheader(f"Inventory Entry: {selected_room}")
        c1, c2, c3 = st.columns(3)    
        
        f_code = c2.text_input("Scan Barcode / Item Code").strip().upper()                
        f_supp = ""  
        
        if f_code and not supp_df.empty:
            prefix_to_match = f_code[:2]
            try:
                supp_df.columns = [str(c).strip() for c in supp_df.columns]
                match = supp_df[supp_df['Prefix'].astype(str).str.strip() == prefix_to_match]
                if not match.empty:
                    f_supp = match.iloc[0]['Supplier']
            except Exception as e:
                pass
                
        all_categories = sorted(list(set(supp_df['Category'].tolist()))) if not supp_df.empty else []
        f_cat = c1.selectbox("Select Category", all_categories)
        f_qty = c3.number_input("Quantity", min_value=1, step=1)
        
        if f_code:
            if f_supp:
                st.info(f"✅ Supplier: **{f_supp}**")
            else:
                st.caption(f"ℹ️ Code-Only Entry mode.")

        submitted = st.form_submit_button("Submit Transaction")        
        
    if submitted: 
        if not f_code:
            st.warning("Item code empty!")
        else:
            with st.spinner("Updating Cloud Inventory Safely..."):
                try:                
                    found_row_index = None
                    current_qty = 0
                    found_df_idx = None
                    
                    if not df_stock_raw.empty:
                        df_stock_raw.columns = [str(c).strip() for c in df_stock_raw.columns]
                        
                        for idx, row in df_stock_raw.iterrows():
                            if str(row.get('Showroom', '')).strip().upper() == selected_room.strip().upper() and \
                               str(row.get('Item Code', '')).strip().upper() == f_code:
                                found_row_index = idx + 2  
                                current_qty = int(row.get('Qty', 0)) if str(row.get('Qty', 0)).isdigit() else 0
                                found_df_idx = idx
                                break

                    # 🔄 पुराना सामान भए प्लस/माइनस गर्ने (फिचर जस्ताको त्यस्तै)
                    if found_row_index:
                        new_total = current_qty + f_qty if trans_type == "Stock In (+)" else current_qty - f_qty
                        if new_total < 0:
                            st.error(f"⚠️ Insufficient Stock! Available is only {current_qty}")
                        else:
                            # १. गुगल शीटमा विना कचकच सिधै एउटा सेल मात्र अपडेट हान्ने
                            ws_stock.update_cell(found_row_index, 6, new_total)
                            ws_stock.update_cell(found_row_index, 3, f_cat)
                            if f_supp:
                                ws_stock.update_cell(found_row_index, 4, f_supp)
                            
                            # 🌟 म्याजिक: गुगलबाट फेरि डाउनलोड नगर्ने, मेमोरीमै भ्यालु अपडेट गरिदिने (No Read Request!)
                            st.session_state.stock_data.at[found_df_idx, 'Qty'] = new_total
                            st.session_state.stock_data.at[found_df_idx, 'Category'] = f_cat
                            if f_supp:
                                st.session_state.stock_data.at[found_df_idx, 'Supplier'] = f_supp
                                
                            st.success(f"🔥 Stock Updated! {f_code} total is now {new_total}")
                            t.sleep(1)
                            st.rerun()
                            
                    # 🆕 नयाँ सामान भए एपेन्ड गर्ने
                    elif trans_type == "Stock In (+)":
                        ws_stock.append_row([today_nepal, selected_room, f_cat, f_supp, f_code, f_qty])
                        
                        # मेमोरीको डाटाफ्रेममा पनि नयाँ रो थपिदिने
                        new_row_df = pd.DataFrame([{
                            "Date": today_nepal, "Showroom": selected_room, "Category": f_cat, 
                            "Supplier": f_supp, "Item Code": f_code, "Qty": f_qty
                        }])
                        st.session_state.stock_data = pd.concat([st.session_state.stock_data, new_row_df], ignore_index=True)
                        
                        st.success(f"✓ New Item Registered: {f_code}")
                        t.sleep(1)
                        st.rerun()
                    else:
                        st.error("❌ Item not found for Stock Out.")
                        
                except Exception as e:
                    st.error(f"Error: {e}")
                    
    st.divider()
    st.subheader("Live Inventory View")
    
    if not df_stock_raw.empty:
        df_stock_raw.columns = [str(c).strip() for c in df_stock_raw.columns]
        if 'Showroom' in df_stock_raw.columns:
            filtered_df = df_stock_raw[df_stock_raw['Showroom'] == selected_room]
            st.dataframe(filtered_df, use_container_width=True, hide_index=True)

elif app_mode == "Attendance":
    st.title("Staff HR Management")
    sh = client.open_by_key(sheet_id)
    ws_emp = sh.worksheet("Employees")
    employee_data = ws_emp.col_values(2)[1:]     
    nepal_tz = pytz.timezone('Asia/Kathmandu')
    now_nepal = datetime.now(nepal_tz)
    today_nepal = now_nepal.date()
    today_str = today_nepal.strftime("%Y-%m-%d")
    selected_staff = st.selectbox("Select Staff Name", employee_data)         
    try:
        ws_at = sh.worksheet(selected_staff)
    except:
        st.error(f"Error: '{selected_staff}''s tab is not founded.")
        st.stop()
    col1, col2 = st.columns(2)    
    if col1.button("Punch In", use_container_width=True):
        deadline = time(11, 0)
        status = "Late" if now_nepal.time() > deadline else "On Time"                
        try:
            punch_in_time = now_nepal.strftime("%I:%M %p")
            ws_at.append_row([today_str, punch_in_time, "", status])
            st.toast(f"Check-in Successful for {selected_staff}")
            st.warning(f"Status: {status} | In: {punch_in_time}")
        except Exception as e:
            st.error(f"Error: {e}")
    if col2.button("Punch Out", use_container_width=True):
        try:
            all_records = ws_at.get_all_records()
            found_row_index = None            
            for i, row in enumerate(reversed(all_records)):
                actual_idx = len(all_records) - i + 1                
                if str(row.get('Out Time', '')).strip() in ["", "None", "nan"]:
                    found_row_index = actual_idx
                    break         
            if found_row_index:
                now_out = now_nepal.strftime("%I:%M %p")
                ws_at.update_cell(found_row_index, 3, now_out) 
                ws_at.update_cell(found_row_index, 4, "Completed")              
                st.toast(f"{selected_staff} Check-out: {now_out}")
                t.sleep(2)
                st.rerun()
            else:
                st.error("Punch-In record is not founded")
        except Exception as e:
            st.error(f"Error during Punch Out: {e}")           
