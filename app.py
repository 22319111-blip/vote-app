import streamlit as st
import pandas as pd
import json
import os
import re
import plotly.express as px
from io import BytesIO
from datetime import datetime

# --- إعدادات النظام ---
st.set_page_config(page_title="منصة الأستاذ قصي الانتخابية", layout="wide")
USERS_FILE = 'clients_users.json'

# --- 1. محرك التطهير الذكي (Smart Normalizer) ---
def clean_logic(name):
    if not isinstance(name, str): return ""
    name = name.strip()
    name = re.sub(r'[أإآ]', 'ا', name)
    name = re.sub(r'ة\b', 'ه', name)
    name = re.sub(r'^ال', '', name)
    name = re.sub(r'^ابو\s+', 'ابو', name)
    name = re.sub(r'^أبو\s+', 'ابو', name)
    return " ".join(name.split())

# --- 2. إدارة المستخدمين (Master) ---
def load_users():
    if not os.path.exists(USERS_FILE):
        return {"qusai": {"pass": "851998", "role": "master", "client_name": "الادارة العامة"}}
    with open(USERS_FILE, 'r', encoding='utf-8') as f: return json.load(f)

def save_users(u):
    with open(USERS_FILE, 'w', encoding='utf-8') as f: json.dump(u, f, ensure_ascii=False, indent=4)

# --- 3. إدارة الجلسة والدخول ---
if 'auth' not in st.session_state: 
    st.session_state.update({'auth': False, 'user': '', 'client': '', 'role': '', 'is_temp': False})

users = load_users()

if not st.session_state.auth:
    st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>🏛️ منصة الأستاذ قصي للحلول الانتخابية</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        u = st.text_input("اسم المستخدم")
        p = st.text_input("كلمة المرور", type="password")
        if st.button("تسجيل الدخول الآمن", use_container_width=True):
            if u in users and users[u]['pass'] == p:
                st.session_state.update({
                    'auth': True, 'user': u, 'role': users[u]['role'], 
                    'client': users[u]['client_name'], 'is_temp': users[u].get('is_temp', False)
                })
                st.rerun()
            else: st.error("⚠️ خطأ في البيانات")
else:
    # --- إعدادات الزبون النشط ---
    CLIENT = st.session_state.client
    DATA_FILE = f"data_{CLIENT}.csv"
    
    def load_client_data():
        if os.path.exists(DATA_FILE):
            df = pd.read_csv(DATA_FILE)
            if 'حالة التصويت' not in df.columns: df['حالة التصويت'] = 'لم يصوت'
            df['family_unified'] = df['اسم العائلة'].apply(clean_logic)
            return df
        return pd.DataFrame()

    def save_client_data(df):
        temp = df.copy()
        if 'family_unified' in temp.columns: temp = temp.drop(columns=['family_unified'])
        temp.to_csv(DATA_FILE, index=False, encoding='utf-8-sig')

    df = load_client_data()
    st.sidebar.title(f"🛡️ نظام {CLIENT}")
    
    # --- لوحة تحكم الأستاذ قصي (Master Only) ---
    if st.session_state.role == "master":
        st.sidebar.divider()
        st.sidebar.subheader("🛠️ الإدارة العامة (قصي)")
        admin_task = st.sidebar.selectbox("العمليات:", ["نظرة عامة", "إضافة زبون جديد", "تصفير بيانات زبون"])
        
        if admin_task == "إضافة زبون جديد":
            with st.expander("فتح اشتراك لمرشح جديد"):
                nc = st.text_input("اسم القائمة/المرشح")
                nu = st.text_input("اسم المستخدم")
                np = st.text_input("كلمة السر")
                if st.button("تفعيل الاشتراك"):
                    users[nu] = {"pass": np, "role": "owner", "client_name": nc, "is_temp": False}
                    save_users(users)
                    st.success(f"تم تفعيل نظام {nc}")

    # --- القائمة الرئيسية للمشترك ---
    menu = st.sidebar.radio("القائمة:", ["📊 الإحصائيات", "🎯 أهداف الحسم", "📝 تسجيل الأصوات", "📑 التقارير والطباعة", "⚙️ الإدارة", "🚪 خروج"])

    if menu == "🚪 خروج":
        st.session_state.auth = False
        st.rerun()

    # --- 📊 الإحصائيات (بمحرك التوحيد) ---
    elif menu == "📊 الإحصائيات":
        st.header(f"📊 إحصائيات: {CLIENT}")
        if not df.empty:
            c1, c2, c3 = st.columns(3)
            c1.metric("إجمالي الناخبين", len(df))
            c2.metric("عدد المصوتين", len(df[df['حالة التصويت'] == 'تم التصويت']))
            c3.metric("النسبة العامة", f"{(len(df[df['حالة التصويت'] == 'تم التصويت'])/len(df))*100:.1f}%")
            
            st.subheader("📌 ترتيب العائلات حسب الالتزام")
            stats = df.groupby('family_unified').agg(total=('الاسم الرباعي','count'), voted=('حالة التصويت', lambda x: (x=='تم التصويت').sum())).reset_index()
            stats['النسبة'] = (stats['voted']/stats['total']*100).round(1)
            st.dataframe(stats.sort_values(by='النسبة', ascending=False), use_container_width=True)

    # --- 📝 تسجيل الأصوات (البحث الذكي) ---
    elif menu == "📝 تسجيل الأصوات":
        st.header("📝 تسجيل الحضور الميداني")
        search = st.text_input("🔍 ابحث (الاسم أو العائلة):")
        m_df = df.copy()
        if search:
            s_clean = clean_logic(search)
            m_df = m_df[m_df['الاسم الرباعي'].str.contains(search, na=False) | m_df['family_unified'].str.contains(s_clean, na=False)]
        
        edited = st.data_editor(m_df[['الاسم الرباعي', 'اسم العائلة', 'اسم المركز', 'حالة التصويت']], use_container_width=True)
        if st.button("💾 حفظ التعديلات"):
            df.update(edited)
            save_client_data(df)
            st.success("✅ تم الحفظ")

    # --- 📑 التقارير (مع فلتر العائلة والمدرسة + حماية المؤقت) ---
    elif menu == "📑 التقارير والطباعة":
        st.header("📑 استخراج كشوفات مخصصة")
        if st.session_state.is_temp:
            st.error("🚫 حساب مؤقت: الطباعة غير متاحة.")
        else:
            sel_f = st.multiselect("اختر العائلات:", sorted(df['family_unified'].unique()))
            sel_c = st.selectbox("اختر المركز:", ["الكل"] + sorted(df['اسم المركز'].unique().tolist()))
            
            rep_df = df.copy()
            if sel_f: rep_df = rep_df[rep_df['family_unified'].isin(sel_f)]
            if sel_c != "الكل": rep_df = rep_df[rep_df['اسم المركز'] == sel_c]
            
            st.dataframe(rep_df[['الاسم الرباعي', 'اسم العائلة', 'اسم المركز', 'حالة التصويت']])
            if not rep_df.empty:
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    rep_df.to_excel(writer, index=False)
                st.download_button("📥 تحميل الكشف (Excel)", data=output.getvalue(), file_name=f"kashf_{CLIENT}.xlsx")

    # --- ⚙️ الإدارة (تصفير الأصوات) ---
    elif menu == "⚙️ الإدارة":
        if st.session_state.role in ['master', 'owner']:
            st.header("⚙️ إدارة النظام")
            if st.button("🧹 تصفير جميع الأصوات لهذا الزبون"):
                df['حالة التصويت'] = 'لم يصوت'
                save_client_data(df)
                st.success("تم تصفير الأصوات.")
                st.rerun()
