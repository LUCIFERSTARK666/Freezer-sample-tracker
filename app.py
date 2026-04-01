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
st.markdown("<p style='text-align: center; font-weight: bold;'>Department of Biochemistry | Kasturba Medical College, Manipal</p>", unsafe_allow_html=True)
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
        return pd.DataFrame(columns=["userid", "password", "guide_name", "last_date"])

def get_samples():
    try:
        res = conn.table("samples").select("*").execute()
        return pd.DataFrame(res.data)
    except:
        return pd.DataFrame()

user_df = get_users()
USER_LIST = user_df['userid'].tolist() if not user_df.empty else []

# --- 4. SIDEBAR AUTHENTICATION & STATUS ---
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
                if days_left > 30:
                    st.sidebar.metric("Storage Days Left", f"{days_left} Days")
                elif 0 <= days_left <= 30:
                    st.sidebar.warning(f"⚠️ Only {days_left} days remaining!")
                else:
                    st.sidebar.error(f"❌ Storage Expired ({abs(days_left)} days ago)")
            except:
                st.sidebar.info("Expiry date pending.")

        # --- TABS ---
        if is_admin:
            tab1, tab2, tab3, tab4 = st.tabs(["📥 Log Sample", "📋 Master Log", "📊 Analytics", "👤 Admin Panel"])
        else:
            tab1, tab2 = st.tabs(["📥 Log Sample", "📋 My History"])

        # --- TAB 1: LOG SAMPLE ---
        with tab1:
            st.subheader("New Freezer Entry")
            f_type = st.selectbox("1. Freezer Type", ["-80 Freezer", "-20 Freezer"])
            u_name = st.selectbox("2. Unit Name", ["PhCBI", "Panasonic"] if f_type == "-80 Freezer" else ["ElanPro White", "ElanPro Grey"])
            with st.form("entry_form", clear_on_submit=True):
                st.markdown("##### Details")
                c_a, c_b = st.columns(2)
                u_email = c_a.text_input("Your Email ID")
                u_phone = c_b.text_input("Your Phone Number")
                b_guide = st.text_input("Guide Name (Biochemistry)")
                s_type = st.text_input("Sample Type")
                box_id = st.text_input("Box ID / Label (Required)")
                count = st.number_input("Total Number of Boxes", min_value=1, step=1)
                if st.form_submit_button("Submit"):
                    if box_id and b_guide:
                        log_data = {"timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "userid": selected_user, "email": u_email, "phone": u_phone, "biochem_guide": b_guide, "freezer": f_type, "unit": u_name, "sample_type": s_type, "box_id": box_id, "box_count": int(count)}
                        conn.table("samples").insert(log_data).execute()
                        st.cache_resource.clear()
                        st.success("Entry Saved Successfully!")
                        st.rerun()
                    else: st.error("Missing required fields.")

        # --- TAB 2: MASTER LOG ---
        with tab2:
            df_samples = get_samples()
            if not df_samples.empty:
                view_df = df_samples if is_admin else df_samples[df_samples['userid'] == selected_user]
                if is_admin:
                    sq = st.text_input("Search Logs", "").lower()
                    if sq: view_df = view_df[view_df['userid'].astype(str).str.lower().contains(sq) | view_df['box_id'].astype(str).str.lower().contains(sq)]
                st.dataframe(view_df.drop(columns=['id'], errors='ignore').sort_values('timestamp', ascending=False), use_container_width=True)
                csv = view_df.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Download CSV", csv, "freezer_log.csv", "text/csv")
                
                if is_admin:
                    st.markdown("---")
                    st.subheader("⚙️ Manage Entries (Admin Only)")
                    manage_opts = [f"{r['userid']} | {r['box_id']} | {r['timestamp']}" for _, r in view_df.iterrows()]
                    selected_manage = st.selectbox("Select entry to modify/delete", ["Select"] + manage_opts)
                    if selected_manage != "Select":
                        target_row = view_df.iloc[manage_opts.index(selected_manage) - 1]
                        c_edit, c_del = st.columns([2, 1])
                        with c_edit:
                            with st.form("edit_form"):
                                e_box = st.text_input("Box ID", value=target_row['box_id'])
                                e_count = st.number_input("Count", value=int(target_row['box_count']), min_value=1)
                                e_phone = st.text_input("Phone", value=target_row.get('phone', ""))
                                e_guide = st.text_input("Guide Name", value=target_row.get('biochem_guide', ""))
                                if st.form_submit_button("Update Everything"):
                                    conn.table("samples").update({"box_id": e_box, "box_count": e_count, "phone": e_phone, "biochem_guide": e_guide}).eq("id", target_row['id']).execute()
                                    st.cache_resource.clear()
                                    st.rerun()
                        with c_del:
                            if st.button("🗑️ Delete Entry Permanently"):
                                conn.table("samples").delete().eq("id", target_row['id']).execute()
                                st.cache_resource.clear()
                                st.rerun()
            else: st.info("No data available.")

        # --- TAB 3: ANALYTICS (SUBSET FEATURE ADDED) ---
        if is_admin:
            with tab3:
                all_d = get_samples()
                if not all_d.empty:
                    m1, m2, m3 = st.columns(3)
                    c_80 = int(all_d[all_d['freezer'] == "-80 Freezer"]['box_count'].sum())
                    c_20 = int(all_d[all_d['freezer'] == "-20 Freezer"]['box_count'].sum())
                    m1.metric("Boxes (-80°C)", c_80)
                    m2.metric("Boxes (-20°C)", c_20)
                    m3.metric("Grand Total", c_80 + c_20)
                    
                    st.markdown("---")
                    col_l, col_r = st.columns(2)
                    
                    with col_l:
                        st.markdown("#### 🧊 -80°C Subset Analysis")
                        df_80 = all_d[all_d['freezer'] == "-80 Freezer"]
                        if not df_80.empty:
                            st.write("Usage by Unit Name")
                            st.bar_chart(df_80.groupby('unit')['box_count'].sum())
                            st.write("Usage by User")
                            st.bar_chart(df_80.groupby('userid')['box_count'].sum())
                    
                    with col_r:
                        st.markdown("#### ❄️ -20°C Subset Analysis")
                        df_20 = all_d[all_d['freezer'] == "-20 Freezer"]
                        if not df_20.empty:
                            st.write("Usage by Unit Name")
                            st.bar_chart(df_20.groupby('unit')['box_count'].sum())
                            st.write("Usage by User")
                            st.bar_chart(df_20.groupby('userid')['box_count'].sum())
                else:
                    st.info("No data available.")

        # --- TAB 4: ADMIN PANEL ---
        if is_admin:
            with tab4:
                st.subheader("👤 User Management")
                c_add, c_manage = st.columns(2)
                with c_add:
                    st.markdown("##### Authorize New Student")
                    with st.form("auth"):
                        n_id, n_pw, n_gd, n_ex = st.text_input("User ID"), st.text_input("Pass"), st.text_input("Guide"), st.date_input("Expiry")
                        if st.form_submit_button("Authorize"):
                            conn.table("users").upsert({"userid": n_id, "password": n_pw, "guide_name": n_gd, "last_date": str(n_ex)}).execute()
                            st.cache_resource.clear()
                            st.rerun()
                
                with c_manage:
                    st.markdown("##### Manage Existing Student")
                    student_list = [u for u in USER_LIST if u != "Admin"]
                    to_manage = st.selectbox("Select Student to Update/Remove", ["Select"] + student_list)
                    
                    if to_manage != "Select":
                        curr_student = user_df[user_df['userid'] == to_manage].iloc[0]
                        st.info(f"Current Expiry: {curr_student['last_date']}")
                        new_expiry = st.date_input("Set New Storage Expiry Date", key="extend_date")
                        
                        col_up, col_rm = st.columns(2)
                        if col_up.button("📅 Update Expiry Date"):
                            conn.table("users").update({"last_date": str(new_expiry)}).eq("userid", to_manage).execute()
                            st.cache_resource.clear()
                            st.success(f"Expiry Updated for {to_manage}!")
                            st.rerun()
                            
                        if col_rm.button("🗑️ Remove User Access"):
                            conn.table("users").delete().eq("userid", to_manage).execute()
                            st.cache_resource.clear()
                            st.rerun()

                st.markdown("---")
                st.write("**Currently Authorized Users:**")
                st.table(user_df[['userid', 'guide_name', 'last_date']])

    else: st.sidebar.error("Invalid credentials.")
else: st.info("Please login in the sidebar.")

# --- 5. HELP SYSTEM ---
st.sidebar.markdown("---")
for _ in range(15): st.sidebar.write("")
with st.sidebar.popover("Help"):
    h_uid = st.text_input("Enter User ID", key="h_uid")
    if h_uid:
        subj = urllib.parse.quote(f"Freezer storage issue _ {h_uid}")
        body = urllib.parse.quote(f"Hello Team,\n\nI am facing an issue. My User ID is {h_uid}.\n")
        st.markdown(f'<a href="mailto:biochem@manipal.edu?subject={subj}&body={body}" style="display:block;padding:10px;background:#4f8bf9;color:white;text-align:center;border-radius:5px;text-decoration:none;">📧 Support Email</a>', unsafe_allow_html=True)
