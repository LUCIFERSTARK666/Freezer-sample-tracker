import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime
import urllib.parse

# --- 1. PAGE SETUP & KMC LOGO ---
st.set_page_config(page_title="Freezer Manager", layout="wide")

LOGO_URL = "https://cdn-prod.mybharats.in/organization/DL-ns-d9cbe78f-d9b2-4e20-baf0-e0747653f0bd_kmclogo.jpg"
col_l, col_m, col_r = st.columns([2, 2, 2])
with col_m:
    st.image(LOGO_URL, width=350)

st.markdown("<h1 style='text-align: center;'>Freezer Management System</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; font-weight: bold;'>Department of Biochemistry | KMC Manipal</p>", unsafe_allow_html=True)
st.markdown("---")

# --- 2. DATABASE CONNECTION ---
url = "https://fhfegywetoavcfwbteye.supabase.co"
key = "sb_publishable_phs0oKRBj7KBwt4NauMAFw_BttBSqCe"

@st.cache_resource
def init_connection():
    return create_client(url, key)

conn = init_connection()

# --- 3. DATA FETCHING ---
def get_users():
    try:
        res = conn.table("users").select("*").execute()
        return pd.DataFrame(res.data)
    except:
        return pd.DataFrame(columns=["userid", "password", "guide_name", "last_date", "name", "email", "phone"])

def get_samples():
    try:
        res = conn.table("samples").select("*").execute()
        return pd.DataFrame(res.data)
    except:
        return pd.DataFrame()

user_df = get_users()
USER_LIST = user_df['userid'].tolist() if not user_df.empty else []

# --- 4. SIDEBAR AUTHENTICATION ---
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
            st.sidebar.write(f"**Guide:** {u_row['guide_name']}")
            try:
                expiry_date = datetime.strptime(str(u_row['last_date']).strip(), "%Y-%m-%d").date()
                days_left = (expiry_date - datetime.now().date()).days
                if days_left > 30: st.sidebar.metric("Days Left", f"{days_left}")
                elif 0 <= days_left <= 30: st.sidebar.warning(f"⚠️ {days_left} days left!")
                else: st.sidebar.error(f"❌ Expired")
            except: st.sidebar.info("Date pending.")

        # --- TABS ---
        if is_admin:
            tab1, tab2, tab3, tab4 = st.tabs(["📥 Log Sample", "📋 Master Log", "📊 Analytics", "👤 Admin Panel"])
        else:
            tab1, tab2 = st.tabs(["📥 Log Sample", "📋 My History"])

        # --- TAB 1: LOG SAMPLE ---
        with tab1:
            st.subheader("New Freezer Entry")
            f_type = st.selectbox("Freezer Type", ["-80 Freezer", "-20 Freezer"])
            u_name = st.selectbox("Unit", ["PhCBI", "Panasonic"] if f_type == "-80 Freezer" else ["ElanPro White", "ElanPro Grey"])
            with st.form("entry_form", clear_on_submit=True):
                c_a, c_b = st.columns(2)
                u_email = c_a.text_input("Email")
                u_phone = c_b.text_input("Phone")
                box_id = st.text_input("Box ID (Required)")
                count = st.number_input("Total Boxes", min_value=1, step=1)
                if st.form_submit_button("Submit"):
                    if box_id:
                        log_data = {"timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "userid": selected_user, "email": u_email, "phone": u_phone, "freezer": f_type, "unit": u_name, "box_id": box_id, "box_count": int(count)}
                        conn.table("samples").insert(log_data).execute()
                        st.cache_resource.clear()
                        st.success("Saved!")
                        st.rerun()

        # --- TAB 2: MASTER LOG ---
        with tab2:
            df_samples = get_samples()
            if not df_samples.empty:
                view_df = df_samples if is_admin else df_samples[df_samples['userid'] == selected_user]
                st.dataframe(view_df.drop(columns=['id'], errors='ignore').sort_values('timestamp', ascending=False), use_container_width=True)
                
                if is_admin:
                    st.markdown("---")
                    manage_opts = [f"{r['userid']} | {r['box_id']}" for _, r in view_df.iterrows()]
                    selected_manage = st.selectbox("Manage Entry", ["Select"] + manage_opts)
                    if selected_manage != "Select":
                        target_row = view_df.iloc[manage_opts.index(selected_manage) - 1]
                        if st.button("🗑️ Delete Permanently"):
                            conn.table("samples").delete().eq("id", target_row['id']).execute()
                            st.cache_resource.clear()
                            st.rerun()

        # --- TAB 3: ANALYTICS ---
        if is_admin:
            with tab3:
                all_d = get_samples()
                if not all_d.empty:
                    m1, m2 = st.columns(2)
                    m1.metric("Total Boxes (-80°C)", int(all_d[all_d['freezer'] == "-80 Freezer"]['box_count'].sum()))
                    m2.metric("Total Boxes (-20°C)", int(all_d[all_d['freezer'] == "-20 Freezer"]['box_count'].sum()))
                    
                    st.markdown("---")
                    with st.expander("🚨 EMERGENCY BROADCAST"):
                        if 'email' in user_df.columns:
                            emails = user_df[user_df['userid'] != 'Admin']['email'].dropna().unique().tolist()
                            e_list = ",".join(emails)
                            if e_list:
                                subj = urllib.parse.quote("URGENT: Freezer Emergency")
                                body = urllib.parse.quote("Please check your samples immediately.")
                                link = f"mailto:biochem@manipal.edu?bcc={e_list}&subject={subj}&body={body}"
                                st.markdown(f'<a href="{link}" target="_blank" style="display:block;padding:12px;background:#FF4B4B;color:white;text-align:center;border-radius:10px;text-decoration:none;">Draft Broadcast Email to {len(emails)} Users</a>', unsafe_allow_html=True)
                        else: st.warning("Database update required (Run SQL).")

        # --- TAB 4: ADMIN PANEL ---
        if is_admin:
            with tab4:
                st.subheader("Authorize Student")
                with st.form("auth_new"):
                    c1, c2 = st.columns(2)
                    n_id = c1.text_input("New User ID")
                    n_name = c2.text_input("Student Name")
                    n_email = c1.text_input("Student Email")
                    n_phone = c2.text_input("Student Phone")
                    n_pw = c1.text_input("Password")
                    n_gd = c2.text_input("Guide")
                    n_ex = st.date_input("Expiry")
                    if st.form_submit_button("Authorize"):
                        if n_id and n_name:
                            # Payload with safety for new columns
                            auth_payload = {"userid": n_id, "password": n_pw, "guide_name": n_gd, "last_date": str(n_ex), "name": n_name, "email": n_email, "phone": n_phone}
                            conn.table("users").upsert(auth_payload).execute()
                            st.cache_resource.clear()
                            st.success(f"Added {n_name}")
                            st.rerun()

                st.markdown("---")
                st.subheader("Manage Users")
                student_list = [u for u in USER_LIST if u != "Admin"]
                to_manage = st.selectbox("Select Student", ["Select"] + student_list)
                if to_manage != "Select":
                    # Fix: Corrected variable name mismatch (to_manage instead of to_rem)
                    if st.button("🗑️ Remove Access"):
                        conn.table("users").delete().eq("userid", to_manage).execute()
                        st.cache_resource.clear()
                        st.rerun()

                # Table display check
                cols = [c for c in ['userid', 'name', 'last_date'] if c in user_df.columns]
                st.table(user_df[cols])

    else: st.sidebar.error("Invalid credentials.")
else: st.info("Please login.")

# --- HELP ---
st.sidebar.markdown("---")
with st.sidebar.popover("Help"):
    h_uid = st.text_input("User ID", key="h_uid")
    if h_uid:
        subj = urllib.parse.quote(f"Freezer Issue - {h_uid}")
        st.markdown(f'<a href="mailto:biochem@manipal.edu?cc=vinutha.bhat@manipal.edu&subject={subj}" style="display:block;padding:10px;background:#4f8bf9;color:white;text-align:center;border-radius:5px;text-decoration:none;">📧 Email Support</a>', unsafe_allow_html=True)
