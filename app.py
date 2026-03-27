import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime

# --- 1. PAGE SETUP & KMC LOGO ---
st.set_page_config(page_title="Freezer Manager", layout="wide")
LOGO_URL = "https://cdn-prod.mybharats.in/organization/DL-ns-d9cbe78f-d9b2-4e20-baf0-e0747653f0bd_kmclogo.jpg"

col1, col2, col3 = st.columns([2, 2, 2])
with col2:
    st.image(LOGO_URL, width=350) 

st.markdown("<h1 style='text-align: center;'>Freezer Management System</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; font-weight: bold;'>Department of Biochemistry | Kasturba Medical College, Manipal</p>", unsafe_allow_html=True)
st.markdown("---")

# --- 2. DATABASE CONNECTION ---
url = "https://fhfegywetoavcfwbteye.supabase.co"
key = "sb_publishable_phs0oKRBj7KBwt4NauMAFw_BttBSqCe"

@st.cache_resource
def init_connection():
    return create_client(url, key)

conn = init_connection()

def get_users():
    try:
        res = conn.table("users").select("*").execute()
        return pd.DataFrame(res.data)
    except:
        return pd.DataFrame(columns=["userid", "password", "guide_name", "last_date"])

def get_samples():
    try:
        res = conn.table("samples").select("*").execute()
        return pd.DataFrame(res.data)
    except:
        return pd.DataFrame()

user_df = get_users()
USER_LIST = user_df['userid'].tolist() if not user_df.empty else []

# --- 3. SIDEBAR AUTHENTICATION ---
st.sidebar.header("Authentication")
selected_user = st.sidebar.selectbox("Select User ID", ["Select"] + USER_LIST)
input_pass = st.sidebar.text_input("Enter Password", type="password")

if selected_user != "Select" and input_pass:
    is_admin = (selected_user == "Admin" and input_pass == "Biochem000")
    user_data = user_df[user_df['userid'] == selected_user]
    is_valid_user = not user_data.empty and str(user_data.iloc[0]['password']) == input_pass

    if is_admin or is_valid_user:
        st.sidebar.success(f"Verified: {selected_user}")
        
        if not is_admin:
            u_row = user_data.iloc[0]
            st.sidebar.markdown("---")
            st.sidebar.subheader("Storage Status")
            st.sidebar.write(f"**Primary Guide:** {u_row['guide_name']}")
            try:
                expiry_date = datetime.strptime(str(u_row['last_date']).strip(), "%Y-%m-%d").date()
                days_left = (expiry_date - datetime.now().date()).days
                if days_left > 30: st.sidebar.metric("Storage Days Left", f"{days_left} Days")
                elif 0 <= days_left <= 30: st.sidebar.warning(f"⚠️ Only {days_left} days remaining!")
                else: st.sidebar.error(f"❌ Expired ({abs(days_left)} days ago)")
            except: st.sidebar.info("Expiry pending.")

        if is_admin:
            tab1, tab2, tab3 = st.tabs(["📥 Log Sample", "📋 Master Log", "⚙️ Admin Panel"])
        else:
            tab1, tab2 = st.tabs(["📥 Log Sample", "📋 My History"])

        # --- TAB 1 & 2 (Logic remains same) ---
        with tab1:
            st.subheader("New Freezer Entry")
            f_type = st.selectbox("1. Freezer Type", ["-80 Freezer", "-20 Freezer"])
            u_opts = ["PhCBI", "Panasonic"] if f_type == "-80 Freezer" else ["ElanPro White (Vertical)", "ElanPro Grey (Horizontal)"]
            u_name = st.selectbox("2. Unit Name", u_opts)
            with st.form("entry_form", clear_on_submit=True):
                col_a, col_b = st.columns(2)
                u_email, u_phone = col_a.text_input("Email ID"), col_b.text_input("Phone Number")
                b_guide, s_type = st.text_input("Guide Name"), st.text_input("Sample Type")
                col_c, col_d = st.columns(2)
                box_id, count = col_c.text_input("Box ID (Required)"), col_d.number_input("Total Boxes", min_value=1, step=1)
                if st.form_submit_button("Submit"):
                    if box_id and b_guide:
                        conn.table("samples").insert({"timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),"userid": selected_user, "email": u_email, "phone": u_phone,"biochem_guide": b_guide, "freezer": f_type, "unit": u_name,"sample_type": s_type, "box_id": box_id, "box_count": int(count)}).execute()
                        st.success("Entry Logged!")
                        st.rerun()

        with tab2:
            all_samples = get_samples()
            if not all_samples.empty:
                view_df = all_samples if is_admin else all_samples[all_samples['userid'] == selected_user]
                st.dataframe(view_df.sort_values('timestamp', ascending=False), use_container_width=True)
                if is_admin:
                    st.markdown("---")
                    st.subheader("✏️ Manage Individual Entry")
                    edit_opts = [f"{r['userid']} | {r['box_id']} | {r['timestamp']}" for _, r in view_df.iterrows()]
                    to_manage = st.selectbox("Select entry", ["Select"] + edit_opts)
                    if to_manage != "Select":
                        row = view_df.iloc[edit_options.index(to_manage) - 1]
                        c1, c2 = st.columns([2, 1])
                        with c1:
                            with st.form("edit_form"):
                                e_box, e_count = st.text_input("New Box ID", value=str(row['box_id'])), st.number_input("New Count", value=int(row['box_count']))
                                if st.form_submit_button("Save Changes"):
                                    conn.table("samples").update({"box_id": e_box, "box_count": e_count}).eq("timestamp", str(row['timestamp'])).eq("userid", row['userid']).execute()
                                    st.rerun()
                        with c2:
                            if st.button("🗑️ Delete Entry"):
                                conn.table("samples").delete().eq("timestamp", str(row['timestamp'])).eq("userid", row['userid']).execute()
                                st.rerun()
            else: st.info("No data available.")

        # --- TAB 3: ADMIN PANEL ---
        if is_admin:
            with tab3:
                st.markdown("""<style>div[data-testid="stMetric"] {background-color: #f0f2f6; border: 1px solid #dfe1e5; padding: 15px; border-radius: 10px; text-align: center;}</style>""", unsafe_allow_html=True)
                all_s = get_samples()
                if not all_s.empty:
                    latest = all_s.sort_values('timestamp').groupby('userid').tail(1)
                    c1, c2, c3 = st.columns(3)
                    c1.metric("-80°C Boxes", int(latest[latest['freezer'] == "-80 Freezer"]['box_count'].sum()))
                    c2.metric("-20°C Boxes", int(latest[latest['freezer'] == "-20 Freezer"]['box_count'].sum()))
                    c3.metric("Grand Total", int(latest['box_count'].sum()))
                
                st.markdown("---")
                col_left, col_right = st.columns(2)
                with col_left:
                    st.subheader("Add Student")
                    with st.form("add_u"):
                        n_id, n_pw, n_gd, n_ex = st.text_input("User ID"), st.text_input("Password"), st.text_input("Guide"), st.date_input("Expiry")
                        if st.form_submit_button("Authorize"):
                            conn.table("users").upsert({"userid": n_id, "password": n_pw, "guide_name": n_gd, "last_date": str(n_ex)}).execute()
                            st.rerun()
                with col_right:
                    st.subheader("Remove Student")
                    to_del = st.selectbox("Select Student", ["Select"] + [u for u in USER_LIST if u != "Admin"])
                    if to_del != "Select" and st.button("Confirm Removal"):
                        conn.table("users").delete().eq("userid", to_del).execute()
                        st.rerun()

                # --- STEALTH PURGE FEATURE ---
                st.markdown("<br><br><br>", unsafe_allow_html=True)
                # This period "." is the secret button
                if st.button(".", help="Advanced Settings"):
                    st.warning("🚨 Master Log Purge Tool Activated")
                    step1 = st.checkbox("First Confirmation: I understand this clears ALL sample data.")
                    if step1:
                        step2 = st.checkbox("Second Confirmation: I have downloaded a backup CSV.")
                        if step2:
                            if st.button("🔥 PERMANENTLY WIPE DATABASE"):
                                conn.table("samples").delete().neq("userid", "null").execute()
                                st.error("Database Cleared.")
                                st.rerun()
    else: st.sidebar.error("Invalid credentials.")
else: st.info("Please log in.")
