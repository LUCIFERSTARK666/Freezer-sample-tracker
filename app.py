import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
from datetime import datetime

# --- 1. PAGE SETUP ---
st.set_page_config(page_title="Biochemistry Freezer Manager", layout="centered")
st.title("Freezer Management System")

# --- 2. DATABASE CONNECTION ---
conn = st.connection(from supabase import create_client
url = "https://fhfegywetoavcfwbteye.supabase.co"
key = "sb_publishable_phs0oKRBj7KBwt4NauMAFw_BttBSqCe"
conn = create_client(url, key))

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

# Load live data
user_df = get_users()
USER_LIST = user_df['userid'].tolist() if not user_df.empty else []

# --- 3. LOGIN INTERFACE ---
st.sidebar.header("Lab Authentication")
selected_user = st.sidebar.selectbox("Select User ID", ["Select"] + USER_LIST)
input_pass = st.sidebar.text_input("Enter Password", type="password")

ADMIN_ID = "Admin"
ADMIN_PASS = "Biochem000"

if selected_user != "Select" and input_pass:
    is_admin = (selected_user == ADMIN_ID and input_pass == ADMIN_PASS)
    user_data = user_df[user_df['userid'] == selected_user]
    is_valid_user = not user_data.empty and str(user_data.iloc[0]['password']) == input_pass

    if is_admin or is_valid_user:
        st.sidebar.success(f"Verified: {selected_user}")
        
        # --- NEW: DAYS REMAINING LOGIC ---
        if not is_admin:
            u_row = user_data.iloc[0]
            st.sidebar.markdown("---")
            st.sidebar.write(f"**Primary Guide:** {u_row['guide_name']}")
            try:
                # Calculates days between today and the 'last_date' in Supabase
                expiry = datetime.strptime(str(u_row['last_date']).strip(), "%Y-%m-%d")
                days_left = (expiry - datetime.now()).days
                
                if days_left > 0:
                    st.sidebar.metric("Storage Days Left", f"{days_left} Days")
                else:
                    st.sidebar.error("⚠️ Storage Period Expired")
            except:
                st.sidebar.warning("Expiry date format error.")

        # Tabs
        if is_admin:
            tab1, tab2, tab3 = st.tabs(["📥 Log Sample", "📋 Master Log", "⚙️ Admin Panel"])
        else:
            tab1, tab2 = st.tabs(["📥 Log Sample", "📋 My History"])

        # --- TAB 1: LOG SAMPLE ---
        with tab1:
            st.subheader("New Freezer Entry")
            with st.form("entry_form", clear_on_submit=True):
                st.markdown("##### 👤 Investigator & Guide Details")
                col_a, col_b = st.columns(2)
                u_email = col_a.text_input("Your Email ID")
                u_phone = col_b.text_input("Your Phone Number")
                b_guide = st.text_input("Guide Name (Biochemistry)")

                st.markdown("---")
                st.markdown("##### ❄️ Storage Information")
                f_type = st.selectbox("Freezer Type", ["-80 Freezer", "-20 Freezer"])
                
                # --- NEW: UPDATED FREEZER MODELS ---
                if f_type == "-80 Freezer":
                    u_opts = ["PhCBI", "Panasonic"]
                else:
                    u_opts = ["Elanpro Horizontal", "Elanpro Vertical"]
                
                u_name = st.selectbox("Unit Name", u_opts)
                
                s_type = st.text_input("Sample Type (e.g., Serum, Plasma)")
                col_c, col_d = st.columns(2)
                box_id = col_c.text_input("Box ID (Required)")
                count = col_d.number_input("Total Number of Boxes", min_value=1, step=1)

                if st.form_submit_button("Submit to Cloud"):
                    if box_id and b_guide:
                        log_data = {
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                            "userid": selected_user, "email": u_email, "phone": u_phone,
                            "biochem_guide": b_guide, "freezer": f_type, "unit": u_name,
                            "sample_type": s_type, "box_id": box_id, "box_count": int(count)
                        }
                        conn.table("samples").insert(log_data).execute()
                        st.success("Entry Secured in Database!")
                        st.balloons()
                    else:
                        st.error("Box ID and Guide Name are required.")

        # --- TAB 2: VIEW RECORDS ---
        with tab2:
            df_samples = get_samples()
            if not df_samples.empty:
                if is_admin:
                    st.dataframe(df_samples, use_container_width=True)
                    csv = df_samples.to_csv(index=False).encode('utf-8')
                    st.download_button("📥 Download Master Log", csv, "master_log.csv", "text/csv")
                else:
                    my_df = df_samples[df_samples['userid'] == selected_user]
                    st.dataframe(my_df, use_container_width=True)

        # --- TAB 3: ADMIN PANEL ---
        if is_admin:
            with tab3:
                st.subheader("User Management")
                with st.form("add_user"):
                    n_id = st.text_input("New Student User ID")
                    n_pw = st.text_input("Set Password")
                    n_gd = st.text_input("Primary Guide Name")
                    n_ex = st.date_input("Storage Expiry Date")
                    if st.form_submit_button("Authorize Student"):
                        user_payload = {
                            "userid": n_id, "password": n_pw, 
                            "guide_name": n_gd, "last_date": str(n_ex)
                        }
                        conn.table("users").upsert(user_payload).execute()
                        st.success(f"Student {n_id} added.")
                        st.rerun()
                
                st.markdown("---")
                st.table(user_df[['userid', 'guide_name', 'last_date']])
    else:
        st.error("Wrong Password.")
else:
    st.info("Please log in to enter freezer data.")
