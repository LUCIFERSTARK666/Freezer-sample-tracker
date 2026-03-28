import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime
import urllib.parse

# --- 1. PAGE SETUP & KMC LOGO ---
st.set_page_config(page_title="Freezer Manager", layout="wide")

LOGO_URL = "https://cdn-prod.mybharats.in/organization/DL-ns-d9cbe78f-d9b2-4e20-baf0-e0747653f0bd_kmclogo.jpg"
c1, c2, c3 = st.columns([2, 2, 2])
with c2: st.image(LOGO_URL, width=350)

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

# --- 3. DATA FETCHING (PULLING THE HIDDEN ID) ---
def get_users():
    try:
        res = conn.table("users").select("*").execute()
        return pd.DataFrame(res.data)
    except:
        return pd.DataFrame(columns=["userid", "password", "guide_name", "last_date"])

def get_samples():
    try:
        # CRITICAL: We select 'id' to ensure we can delete accurately
        res = conn.table("samples").select("*").execute()
        df = pd.DataFrame(res.data)
        return df
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
                u_email = st.text_input("Your Email ID")
                b_guide = st.text_input("Guide Name (Biochemistry)")
                s_type = st.text_input("Sample Type")
                box_id = st.text_input("Box ID / Label (Required)")
                count = st.number_input("Total Number of Boxes", min_value=1, step=1)

                if st.form_submit_button("Submit to Cloud"):
                    if box_id and b_guide:
                        log_data = {
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "userid": selected_user, "email": u_email,
                            "biochem_guide": b_guide, "freezer": f_type, "unit": u_name,
                            "sample_type": s_type, "box_id": box_id, "box_count": int(count)
                        }
                        conn.table("samples").insert(log_data).execute()
                        st.cache_resource.clear()
                        st.success("Entry Saved!")
                        st.rerun()

        # --- TAB 2: MASTER LOG (THE GUARANTEED DELETE FIX) ---
        with tab2:
            df_samples = get_samples()
            if not df_samples.empty:
                view_df = df_samples if is_admin else df_samples[df_samples['userid'] == selected_user]
                
                # Search Bar
                if is_admin:
                    search_q = st.text_input("Search Logs", "").lower()
                    if search_q:
                        view_df = view_df[view_df['userid'].str.lower().contains(search_q) | view_df['box_id'].str.lower().contains(search_q)]
                
                st.dataframe(view_df.drop(columns=['id'], errors='ignore'), use_container_width=True)
                
                # Download
                csv = view_df.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Download CSV", csv, "freezer_log.csv", "text/csv")

                # ADMIN DUAL MANAGE (Using the hidden 'id' column)
                if is_admin:
                    st.markdown("---")
                    st.subheader("⚙️ Manage Entries")
                    manage_opts = [f"{r['userid']} | {r['box_id']} | {r['timestamp']}" for _, r in view_df.iterrows()]
                    selected_manage = st.selectbox("Select entry to modify/delete", ["Select"] + manage_opts)
                    
                    if selected_manage != "Select":
                        target_row = view_df.iloc[manage_opts.index(selected_manage) - 1]
                        
                        c_edit, c_del = st.columns([2, 1])
                        with c_edit:
                            with st.form("edit_form_final"):
                                e_box = st.text_input("New Box ID", value=target_row['box_id'])
                                e_count = st.number_input("New Count", value=int(target_row['box_count']), min_value=1)
                                if st.form_submit_button("Update Details"):
                                    # Update using the unique 'id'
                                    conn.table("samples").update({"box_id": e_box, "box_count": e_count}).eq("id", target_row['id']).execute()
                                    st.cache_resource.clear()
                                    st.rerun()
                        with c_del:
                            if st.button("🗑️ Delete Permanently"):
                                # Delete using the unique 'id'
                                conn.table("samples").delete().eq("id", target_row['id']).execute()
                                st.cache_resource.clear()
                                st.rerun()
            else: st.info("No data found.")

        # --- TAB 3: ANALYTICS (TOTALS & CHARTS) ---
        if is_admin:
            with tab3:
                st.subheader("📊 Totals & Distribution")
                all_d = get_samples()
                if not all_d.empty:
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Boxes (-80°C)", int(all_d[all_d['freezer'] == "-80 Freezer"]['box_count'].sum()))
                    m2.metric("Boxes (-20°C)", int(all_d[all_d['freezer'] == "-20 Freezer"]['box_count'].sum()))
                    m3.metric("Grand Total", int(all_d['box_count'].sum()))
                    
                    st.bar_chart(all_d.groupby('userid')['box_count'].sum())
                    st.bar_chart(all_d.groupby('freezer')['box_count'].sum())

        # --- TAB 4: ADMIN PANEL (USER AUTH) ---
        if is_admin:
            with tab4:
                st.subheader("👤 User Access")
                c_add, c_rem = st.columns(2)
                with c_add:
                    with st.form("auth"):
                        n_id, n_pw, n_gd, n_ex = st.text_input("User ID"), st.text_input("Pass"), st.text_input("Guide"), st.date_input("Expiry")
                        if st.form_submit_button("Authorize"):
                            conn.table("users").upsert({"userid": n_id, "password": n_pw, "guide_name": n_gd, "last_date": str(n_ex)}).execute()
                            st.cache_resource.clear()
                            st.rerun()
                with c_rem:
                    to_rem = st.selectbox("Select User", ["Select"] + [u for u in USER_LIST if u != "Admin"])
                    if to_rem != "Select" and st.button("Confirm Removal"):
                        conn.table("users").delete().eq("userid", to_rem).execute()
                        st.cache_resource.clear()
                        st.rerun()
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
        st.markdown(f'<a href="mailto:biochem@manipal.edu?subject={subj}&body={body}" style="display:block;padding:10px;background:#4f8bf9;color:white;text-align:center;border-radius:5px;text-decoration:none;">📧 Email Support</a>', unsafe_allow_html=True)
