import streamlit as st
import pandas as pd
import json
import os
import re
from io import BytesIO

# =========================================================
# 1. الإعدادات الأساسية (تأكد من وجود الملف بهذا الاسم)
# =========================================================
st.set_page_config(page_title="منصة الأستاذ قصي الانتخابية", layout="wide")

USERS_FILE = 'clients_users.json'
MASTER_DATA = 'Halhul_Ultimate_Perfect.csv' # الاسم الذي أكدت عليه

# =========================================================
# 2. محرك الدوال (Logic)
# =========================================================

def clean_logic(name):
    """توحيد العائلات لضمان دقة الإحصائيات"""
    if not isinstance(name, str): return ""
    name = name.strip()
    name = re.sub(r'[أإآ]', 'ا', name)
    name = re.sub(r'ة\b', 'ه', name)
    name = re.sub(r'^ال', '', name)
    name = re.sub(r'^ابو\s+', 'ابو', name)
    name = re.sub(r'^أبو\s+', 'ابو', name)
    return " ".join(name.split())

def load_users():
    """تحميل حسابات المشتركين"""
    if not os.path.exists(USERS_FILE):
        default_admin = {"qusai": {"pass": "851998", "role": "master", "client_name": "الادارة العامة", "is_temp": False}}
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(default_admin, f, ensure_ascii=False, indent=4)
        return default_admin
    with open(USERS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_users(u_dict):
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(u_dict, f, ensure_ascii=False, indent=4)

def load_client_data(client_name):
    """تحميل بيانات الزبون أو إنشاء ملف جديد من الماستر"""
    filename = f"data_{client_name}.csv"
    if os.path.exists(filename):
        df = pd.read_csv(filename)
    else:
        if os.path.exists(MASTER_DATA):
            df = pd.read_csv(MASTER_DATA)
            df['حالة التصويت'] = 'لم يصوت'
            df.to_csv(filename, index=False, encoding='utf-8-sig')
        else:
            return pd.DataFrame()
    
    if not df.empty and 'اسم العائلة' in df.columns:
        df['family_unified'] = df['اسم العائلة'].apply(clean_logic)
    return df

def save_client_data(df, client_name):
    filename = f"data_{client_name}.csv"
    temp = df.copy()
    if 'family_unified' in temp.columns:
        temp = temp.drop(columns=['family_unified'])
    temp.to_csv(filename, index=False, encoding='utf-8-sig')

# =========================================================
# 3. التحقق الأولي (لمنع الشاشة الحمراء)
# =========================================================
if not os.path.exists(MASTER_DATA):
    st.error(f"⚠️ تنبيه للأستاذ قصي: الملف '{MASTER_DATA}' غير موجود في المجلد. يرجى رفعه ليتمكن النظام من العمل.")
    st.stop()

# =========================================================
# 4. نظام الدخول
# =========================================================
if 'auth' not in st.session_state:
    st.session_state.update({'auth': False, 'user': '', 'client': '', 'role': '', 'is_temp': False})

users_db = load_users()

if not st.session_state.auth:
    st.markdown("<h1 style='text-align: center;'>🏛️ منصة الأستاذ قصي الانتخابية</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        u_in = st.text_input("اسم المستخدم")
        p_in = st.text_input("كلمة المرور", type="password")
        if st.button("دخول آمن", use_container_width=True):
            if u_in in users_db and users_db[u_in]['pass'] == p_in:
                st.session_state.update({
                    'auth': True, 'user': u_in, 'role': users_db[u_in]['role'],
                    'client': users_db[u_in]['client_name'], 'is_temp': users_db[u_in].get('is_temp', False)
                })
                st.rerun()
            else: st.error("⚠️ بيانات خاطئة")
else:
    # --- واجهة النظام الرئيسية ---
    CLIENT = st.session_state.client
    IS_TEMP = st.session_state.is_temp
    df_full = load_client_data(CLIENT)
    
    # تحديد مستوى الرؤية (نسخة تجريبية vs كاملة)
    df_display = df_full.head(100) if IS_TEMP else df_full

    st.sidebar.title(f"🛡️ نظام {CLIENT}")
    if IS_TEMP: st.sidebar.error("🚨 نسخة تجريبية")
    
    menu = st.sidebar.radio("القائمة:", ["📊 الإحصائيات", "🎯 أهداف الحسم", "📝 تسجيل الأصوات", "📑 التقارير والطباعة", "⚙️ الإدارة", "🚪 خروج"])

    if menu == "🚪 خروج":
        st.session_state.auth = False
        st.rerun()

    # --- لوحة التحكم (Master - قصي) ---
    if st.session_state.role == "master":
        st.sidebar.divider()
        st.sidebar.subheader("🛠️ تحكم المالك")
        admin_opt = st.sidebar.selectbox("إدارة القوائم:", ["عرض", "إضافة زبون", "حذف قائمة"])

        if admin_opt == "إضافة زبون":
            with st.form("add"):
                nc = st.text_input("اسم القائمة")
                nu = st.text_input("اسم المستخدم")
                np = st.text_input("كلمة المرور")
                it = st.checkbox("نسخة تجريبية (رؤية محدودة)")
                if st.form_submit_button("تفعيل"):
                    users_db[nu] = {"pass": np, "role": "owner", "client_name": nc, "is_temp": it}
                    save_users(users_db)
                    load_client_data(nc)
                    st.success("تم تفعيل الزبون")

        elif admin_opt == "حذف قائمة":
            targets = [u for u, info in users_db.items() if info['role'] != 'master']
            target_u = st.selectbox("اختر الحساب للحذف:", targets)
            if st.button("تأكيد الحذف الشامل"):
                c_del = users_db[target_u]['client_name']
                if os.path.exists(f"data_{c_del}.csv"): os.remove(f"data_{c_del}.csv")
                del users_db[target_u]
                save_users(users_db)
                st.rerun()

    # --- المحتوى ---
    if menu == "📊 الإحصائيات":
        st.header(f"📊 إحصائيات: {CLIENT}")
        voted = len(df_full[df_full['حالة التصويت'] == 'تم التصويت'])
        st.columns(3)[0].metric("الكتلة الناخبة", len(df_full) if not IS_TEMP else "100 (تجريبي)")
        st.columns(3)[1].metric("المصوتين", voted)
        st.columns(3)[2].metric("النسبة", f"{(voted/len(df_full))*100:.1f}%")
        
        if not IS_TEMP:
            st.subheader("📌 التزام العائلات")
            stats = df_full.groupby('family_unified').agg(total=('الاسم الرباعي','count'), voted=('حالة التصويت', lambda x: (x=='تم التصويت').sum())).reset_index()
            st.dataframe(stats.sort_values(by='total', ascending=False), use_container_width=True)

    elif menu == "📝 تسجيل الأصوات":
        st.header("📝 الميدان")
        search = st.text_input("🔍 ابحث:")
        work_df = df_display.copy()
        if search:
            work_df = work_df[work_df['الاسم الرباعي'].str.contains(search, na=False)]
        
        edited = st.data_editor(work_df[['الاسم الرباعي', 'اسم العائلة', 'حالة التصويت']], use_container_width=True)
        if st.button("💾 حفظ"):
            df_full.update(edited)
            save_client_data(df_full, CLIENT)
            st.success("تم الحفظ")

    elif menu == "📑 التقارير والطباعة":
        if IS_TEMP: st.error("🚫 وظيفة الطباعة محجوبة في النسخة التجريبية.")
        else:
            st.header("📑 التقارير")
            sel_f = st.multiselect("اختر العائلة:", sorted(df_full['family_unified'].unique()))
            rep = df_full[df_full['family_unified'].isin(sel_f)] if sel_f else df_full
            st.dataframe(rep[['الاسم الرباعي', 'اسم العائلة', 'حالة التصويت']])
            buf = BytesIO(); rep.to_excel(buf, index=False)
            st.download_button("📥 تحميل Excel", buf.getvalue(), f"{CLIENT}.xlsx")

    elif menu == "⚙️ الإدارة":
        if st.button("🧹 تصفير الأصوات"):
            df_full['حالة التصويت'] = 'لم يصوت'
            save_client_data(df_full, CLIENT)
            st.success("تم تصفير البيانات")
