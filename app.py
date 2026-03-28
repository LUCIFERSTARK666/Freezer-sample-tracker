import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime

# --- 1. PAGE SETUP & KMC LOGO ---
st.set_page_config(page_title="Biochemistry Freezer Manager", layout="wide")

# Centering the Logo (Restored)
LOGO_URL = "https://cdn-prod.mybharats.in/organization/DL-ns-d9cbe78f-d9b2-4e20-baf0-e0747653f0bd_kmclogo.jpg"
col_l, col_m, col_r = st.columns([2, 2, 2])
with col_m:
    st.image(LOGO_URL, width=350) 

st.markdown("<h1 style='text-align: center;'>Biochemistry Freezer Management System</h1>", unsafe_allow_html=True)
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
        
        # --- STORAGE EXPIRY LOGIC (RESTORED) ---
        if not is_admin:
            u_row = user_data.iloc[0]
            st.sidebar.markdown("---")
            st.sidebar.subheader("Storage Status")
            st.sidebar.write(f"**Primary Guide:** {u_row['guide_name']}")
            try:
                expiry_str = str(u_row['last_date']).strip()
                expiry_date = datetime.strptime(expiry_str, "%Y-%m-%d").date()
                days_left = (expiry_date - datetime.now().date()).days
                if days_left > 30:
                    st.sidebar.metric("Storage Days Left", f"{days_left} Days")
                elif 0 <= days_left <= 30:
                    st.sidebar.warning(f"⚠️ Only {days_left} days remaining!")
                else:
                    st.sidebar.error(f"❌ Storage Expired ({abs(days_left)} days ago)")
            except:
                st.sidebar.info("Expiry date pending.")

        # Tabs Setup
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
                u_email = st.text_input("Your Email ID")
                b_guide = st.text_input("Guide Name (Biochemistry)")
                s_type = st.text_input("Sample Type")
                box_id = st.text_input("Box ID / Label (Required)")
                count = st.number_input("Total Number of Boxes", min_value=1, step=1)

                if st.form_submit_button("Submit to Cloud"):
                    if box_id and b_guide:
                        log_data = {
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                            "userid": selected_user, "email": u_email,
                            "biochem_guide": b_guide, "freezer": f_type, "unit": u_name,
                            "sample_type": s_type, "box_id": box_id, "box_count": int(count)
                        }
                        conn.table("samples").insert(log_data).execute()
                        st.cache_resource.clear()
                        st.success(f"Saved to {u_name}!")
                        st.rerun()
                    else:
                        st.error("Missing required fields.")

        # --- TAB 2: MASTER LOG (SEARCH, EDIT, DELETE ALL RESTORED) ---
        with tab2:
            df_samples = get_samples()
            if not df_samples.empty:
                if is_admin:
                    st.markdown("##### 🔎 Admin Search")
                    search_query = st.text_input("Search by User ID or Box ID", "").lower()
                    view_df = df_samples
                    if search_query:
                        mask = (view_df['userid'].astype(str).str.lower().str.contains(search_query) | 
                                view_df['box_id'].astype(str).str.lower().str.contains(search_query))
                        view_df = view_df[mask]
                else:
                    view_df = df_samples[df_samples['userid'] == selected_user]
                
                st.dataframe(view_df.sort_values('timestamp', ascending=False), use_container_width=True)
                
                # Admin Management (Edit/Delete Logic Restored)
                if is_admin and not view_df.empty:
                    st.markdown("---")
                    st.subheader("✏️ Manage Entry (Admin Only)")
                    edit_options = [f"{r['userid']} | {r['box_id']} | {r['timestamp']}" for _, r in view_df.iterrows()]
                    selected_manage = st.selectbox("Select entry to modify or remove", ["Select"] + edit_options)
                    
                    if selected_manage != "Select":
                        idx = edit_options.index(selected_manage)
                        target_row = view_df.iloc[idx - 1]
                        
                        col_edit, col_del = st.columns([2, 1])
                        with col_edit:
                            with st.form("admin_edit"):
                                e_box = st.text_input("New Box ID", value=target_row['box_id'])
                                e_count = st.number_input("New Count", value=int(target_row['box_count']), min_value=1)
                                if st.form_submit_button("Update"):
                                    conn.table("samples").update({"box_id": e_box, "box_count": e_count}).eq("timestamp", str(target_row['timestamp'])).eq("userid", target_row['userid']).execute()
                                    st.cache_resource.clear()
                                    st.success("Updated!")
                                    st.rerun()
                        with col_del:
                            if st.button("🗑️ Delete Permanently"):
                                conn.table("samples").delete().eq("timestamp", str(target_row['timestamp'])).eq("userid", target_row['userid']).execute()
                                st.cache_resource.clear()
                                st.warning("Deleted!")
                                st.rerun()
            else:
                st.info("No data available.")

        # --- TAB 3: ANALYTICS (RESTORED) ---
        if is_admin:
            with tab3:
                st.subheader("📊 Graphical Analytics")
                all_s = get_samples()
                if not all_s.empty:
                    c1, c2 = st.columns(2)
                    with c1:
                        st.write("**By Freezer**")
                        st.bar_chart(all_s.groupby('freezer')['box_count'].sum())
                    with c2:
                        st.write("**By User**")
                        st.bar_chart(all_s.groupby('userid')['box_count'].sum())

        # --- TAB 4: ADMIN PANEL (RESTORED) ---
        if is_admin:
            with tab4:
                st.subheader("⚙️ User Management")
                st.table(user_df[['userid', 'guide_name', 'last_date']])

    else:
        st.sidebar.error("Invalid credentials.")
else:
    st.info("Please login to begin.")

# --- HELP POPOVER (RESTORED) ---
st.sidebar.markdown("---")
for _ in range(15): st.sidebar.write("") 
with st.sidebar.popover("Help"):
    h_id = st.text_input("User ID", key="h_id")
    if h_id:
        st.markdown(f'<a href="mailto:biochem@manipal.edu?body=User:{h_id}" style="display:block;padding:10px;background:#4f8bf9;color:white;text-align:center;border-radius:5px;text-decoration:none;">📧 Support</a>', unsafe_allow_html=True)
