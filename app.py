import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime

# --- 1. PAGE SETUP & KMC LOGO ---
st.set_page_config(page_title=" Freezer Manager", layout="wide")

# Centering the Logo at the top
LOGO_URL = "https://cdn-prod.mybharats.in/organization/DL-ns-d9cbe78f-d9b2-4e20-baf0-e0747653f0bd_kmclogo.jpg"

col_l, col_m, col_r = st.columns([2, 2, 2])
with col_m:
    st.image(LOGO_URL, width=350) 

st.markdown("<h1 style='text-align: center;'> Freezer Management System</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; font-weight: bold;'>Department of Biochemistry | Kasturba Medical College, Manipal</p>", unsafe_allow_html=True)
st.markdown("---")

# --- 2. DATABASE CONNECTION ---
url = "https://fhfegywetoavcfwbteye.supabase.co"
key = "sb_publishable_phs0oKRBj7KBwt4NauMAFw_BttBSqCe"

@st.cache_resource
def init_connection():
    return create_client(url, key)

conn = init_connection()

# Optimized: No hard caching here to prevent "data loss" on code edits
def get_users():
    try:
        res = conn.table("users").select("*").execute()
        return pd.DataFrame(res.data)
    except:
        return pd.DataFrame(columns=["userid", "password", "guide_name", "last_date"])

def get_samples():
    try:
        res = conn.table("samples").select("*").execute()
        df = pd.DataFrame(res.data)
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df
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
        
        # --- STORAGE STATUS FOR STUDENTS ---
        if not is_admin:
            u_row = user_data.iloc[0]
            st.sidebar.markdown("---")
            st.sidebar.subheader("Storage Status")
            st.sidebar.write(f"**Primary Guide:** {u_row['guide_name']}")
            try:
                expiry_str = str(u_row['last_date']).strip()
                expiry_date = datetime.strptime(expiry_str, "%Y-%m-%d").date()
                today = datetime.now().date()
                days_left = (expiry_date - today).days
                if days_left > 30:
                    st.sidebar.metric("Storage Days Left", f"{days_left} Days")
                elif 0 <= days_left <= 30:
                    st.sidebar.warning(f"⚠️ Only {days_left} days remaining!")
                else:
                    st.sidebar.error(f"❌ Storage Expired ({abs(days_left)} days ago)")
            except:
                st.sidebar.info("Expiry date pending.")

        # --- TABS SETUP ---
        if is_admin:
            tab1, tab2, tab3, tab4 = st.tabs(["📥 Log Sample", "📋 Master Log", "📊 Analytics", "⚙️ Admin Panel"])
        else:
            tab1, tab2 = st.tabs(["📥 Log Sample", "📋 My History"])

        # --- TAB 1: LOG SAMPLE ---
        with tab1:
            st.subheader("New Freezer Entry")
            col1, col2 = st.columns(2)
            with col1:
                f_type = st.selectbox("1. Freezer Type", ["-80 Freezer", "-20 Freezer"])
            with col2:
                u_opts = ["PhCBI", "Panasonic"] if f_type == "-80 Freezer" else ["ElanPro White (Vertical)", "ElanPro Grey (Horizontal)"]
                u_name = st.selectbox("2. Unit Name", u_opts)

            with st.form("entry_form", clear_on_submit=True):
                st.markdown("##### Details")
                col_a, col_b = st.columns(2)
                u_email = col_a.text_input("Your Email ID")
                u_phone = col_b.text_input("Your Phone Number")
                b_guide = st.text_input("Guide Name (Biochemistry)")
                s_type = st.text_input("Sample Type")
                box_id = st.text_input("Box ID / Label (Required)")
                count = st.number_input("Total Number of Boxes", min_value=1, step=1)

                if st.form_submit_button("Submit to Cloud"):
                    if box_id and b_guide:
                        log_data = {
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                            "userid": selected_user, "email": u_email, "phone": u_phone,
                            "biochem_guide": b_guide, "freezer": f_type, "unit": u_name,
                            "sample_type": s_type, "box_id": box_id, "box_count": int(count)
                        }
                        conn.table("samples").insert(log_data).execute()
                        st.cache_resource.clear()
                        st.success(f"Successfully Saved to {u_name}!")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("Missing required fields (Box ID & Guide Name).")

        # --- TAB 2: MASTER LOG (SEARCH, EDIT, DELETE) ---
        with tab2:
            st.subheader("📋 Freezer Records")
            df_samples = get_samples()
            
            if not df_samples.empty:
                if is_admin:
                    search_query = st.text_input("🔍 Search Master Log (User ID or Box ID)", "").lower()
                    view_df = df_samples
                    if search_query:
                        mask = (view_df['userid'].astype(str).str.lower().str.contains(search_query) | 
                                view_df['box_id'].astype(str).str.lower().str.contains(search_query))
                        view_df = view_df[mask]
                else:
                    view_df = df_samples[df_samples['userid'] == selected_user]
                
                st.dataframe(view_df.sort_values('timestamp', ascending=False), use_container_width=True)
                
                # CSV Export
                csv = view_df.to_csv(index=False).encode('utf-8')
                st.download_button(label="📥 Download Data as CSV", data=csv, file_name="freezer_log.csv", mime="text/csv")
                
                # Admin Management Section
                if is_admin and not view_df.empty:
                    st.markdown("---")
                    st.subheader("✏️ Manage Selected Entry")
                    edit_opts = [f"{r['userid']} | {r['box_id']} | {r['timestamp']}" for _, r in view_df.iterrows()]
                    selected_manage = st.selectbox("Choose an entry to Edit or Delete", ["Select"] + edit_opts)
                    
                    if selected_manage != "Select":
                        idx = edit_opts.index(selected_manage)
                        target_row = view_df.iloc[idx - 1]
                        
                        c_edit, c_del = st.columns([2, 1])
                        with c_edit:
                            with st.form("admin_edit_form"):
                                st.write("**Update Details**")
                                e_box = st.text_input("New Box ID", value=target_row['box_id'])
                                e_count = st.number_input("New Box Count", value=int(target_row['box_count']), min_value=1)
                                if st.form_submit_button("Save Changes"):
                                    conn.table("samples").update({"box_id": e_box, "box_count": e_count}).eq("timestamp", target_row['timestamp']).eq("userid", target_row['userid']).execute()
                                    st.cache_resource.clear()
                                    st.success("Updated!")
                                    st.rerun()
                        with c_del:
                            st.write("**Remove Record**")
                            if st.button("🗑️ Delete Permanently"):
                                conn.table("samples").delete().eq("timestamp", target_row['timestamp']).eq("userid", target_row['userid']).execute()
                                st.cache_resource.clear()
                                st.warning("Entry Deleted!")
                                st.rerun()
            else:
                st.info("No records found in the database.")
                if st.button("🔄 Force Refresh Database Connection"):
                    st.cache_resource.clear()
                    st.rerun()

        # --- TAB 3: ANALYTICS (ADMIN ONLY) ---
        if is_admin:
            with tab3:
                st.subheader("📊 Storage Visual Analytics")
                all_s = get_samples()
                if not all_s.empty:
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Boxes (-80°C)", int(all_s[all_s['freezer'] == "-80 Freezer"]['box_count'].sum()))
                    m2.metric("Boxes (-20°C)", int(all_s[all_s['freezer'] == "-20 Freezer"]['box_count'].sum()))
                    m3.metric("Grand Total Boxes", int(all_s['box_count'].sum()))
                    
                    st.markdown("---")
                    chart_col1, chart_col2 = st.columns(2)
                    with chart_col1:
                        st.write("**Occupancy by Freezer Type**")
                        st.bar_chart(all_s.groupby('freezer')['box_count'].sum())
                    with chart_col2:
                        st.write("**Distribution by User ID**")
                        st.bar_chart(all_s.groupby('userid')['box_count'].sum())
                else:
                    st.info("Add samples to view analytics.")

        # --- TAB 4: ADMIN PANEL (USER MANAGEMENT) ---
        if is_admin:
            with tab4:
                st.subheader("⚙️ User & Access Management")
                col_l, col_r = st.columns(2)
                with col_l:
                    st.subheader("Add / Update Student")
                    with st.form("add_user_form"):
                        n_id, n_pw, n_gd, n_ex = st.text_input("User ID"), st.text_input("Pass"), st.text_input("Guide Name"), st.date_input("Expiry")
                        if st.form_submit_button("Authorize"):
                            conn.table("users").upsert({"userid": n_id, "password": n_pw, "guide_name": n_gd, "last_date": str(n_ex)}).execute()
                            st.cache_resource.clear()
                            st.rerun()
                with col_r:
                    st.subheader("De-authorize Student")
                    student_list = [u for u in USER_LIST if u != "Admin"]
                    user_to_del = st.selectbox("Select Student to Remove", ["Select"] + student_list)
                    if user_to_del != "Select" and st.button("Confirm Removal"):
                        conn.table("users").delete().eq("userid", user_to_del).execute()
                        st.cache_resource.clear()
                        st.rerun()
                
                st.markdown("---")
                st.write("**Currently Authorized Users:**")
                st.table(user_df[['userid', 'guide_name', 'last_date']])

    else:
        st.sidebar.error("Invalid credentials.")
else:
    st.info("👋 Welcome. Please select your User ID in the sidebar to begin.")

# --- 4. STICKY HELP BUTTON (SIDEBAR BOTTOM) ---
st.sidebar.markdown("---")
for _ in range(15): st.sidebar.write("") # Spacer to push button down

with st.sidebar.popover("Help & Support"):
    st.markdown("### System Support")
    h_id = st.text_input("Enter your User ID", placeholder="PhD_User_01", key="help_id_input")
    if h_id:
        h_email = "biochem@manipal.edu"
        body = f"Hello%20Team,%0A%0AI%20am%20facing%20the%20following%20issue:%0A%0A---%0AUser%20ID:%20{h_id}%0A---"
        st.markdown(f'<a href="mailto:{h_email}?subject=Freezer%20Support&body={body}" style="display:inline-block;padding:0.5em 1em;color:white;background-color:#4f8bf9;border-radius:0.5rem;text-decoration:none;font-weight:bold;width:100%;text-align:center;">📧 Email Biochemistry Dept</a>', unsafe_allow_html=True)
    else:
        st.caption("Provide your ID to enable the support link.")
