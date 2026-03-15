import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import os
import re
from io import BytesIO

# =========================================================
# 1. إعدادات النظام واسم قاعدة البيانات
# =========================================================
st.set_page_config(page_title="منصة الأستاذ قصي - غرفة العمليات", layout="wide")

if 'auth' not in st.session_state:
    st.session_state.update({'auth': False, 'user': '', 'client': '', 'role': ''})

# --- هنا قمنا بتعديل اسم قاعدة البيانات حسب طلبك ---
MASTER_FILE = 'Halhul_Ultimate_Perfect.csv.xlsx' 
USERS_FILE = 'clients_users.json'

# =========================================================
# 2. خوارزميات المعالجة والذكاء الاصطناعي (قصي)
# =========================================================
def normalize_family(text):
    """خوارزمية قصي لتوحيد العائلات (حذف ال التعريف، توحيد التاء والهمزة)"""
    if not isinstance(text, str) or not text.strip(): return "غير محدد"
    text = text.strip()
    text = re.sub(r'[أإآ]', 'ا', text)
    text = re.sub(r'ة\b', 'ه', text)
    if text.startswith('ال'): text = text[2:]
    return text

def process_initial_data(df):
    """تجهيز البيانات: بناء الاسم الرباعي وتوحيد العائلات"""
    df = df.copy()
    # بناء الاسم الرباعي من الأعمدة الأربعة
    df['الاسم الرباعي'] = df['الاسم الاول'].fillna('') + " " + \
                        df['اسم الاب'].fillna('') + " " + \
                        df['اسم الجد'].fillna('') + " " + \
                        df['اسم العائلة'].fillna('')
    df['الاسم الرباعي'] = df['الاسم الرباعي'].str.replace(r'\s+', ' ', regex=True).str.strip()
    
    # إنشاء عمود العائلة الموحدة للإحصاء
    df['عائلة_موحدة'] = df['اسم العائلة'].apply(normalize_family)
    
    if 'حالة التصويت' not in df.columns:
        df['حالة التصويت'] = 'لم يصوت'
    return df

# =========================================================
# 3. إدارة الملفات والزبائن
# =========================================================
def load_data(client_name):
    fname = f"data_{client_name}.csv"
    if os.path.exists(fname): 
        return pd.read_csv(fname, dtype=str)
    
    # إذا كان أول مرة، نقرأ من الملف المسمى Halhul_Ultimate_Perfect.csv.xlsx
    if os.path.exists(MASTER_FILE):
        try:
            # نحاول القراءة كإكسل نظراً لللاحقة .xlsx
            raw = pd.read_excel(MASTER_FILE, dtype=str)
        except:
            # إذا فشل، نقرأه كـ CSV (أحياناً تكون التسمية مزدوجة)
            raw = pd.read_csv(MASTER_FILE, dtype=str)
            
        processed = process_initial_data(raw)
        processed.to_csv(fname, index=False, encoding='utf-8-sig')
        return processed
    return pd.DataFrame()

# =========================================================
# 4. واجهة التطبيق والداشبورد
# =========================================================
if not st.session_state.auth:
    st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>🏛️ منصة الأستاذ قصي الانتخابية</h1>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1.2, 1])
    with c2:
        u = st.text_input("اسم المستخدم")
        p = st.text_input("كلمة المرور", type="password")
        if st.button("دخول آمن"):
            if u == "qusai" and p == "851998":
                st.session_state.update({'auth': True, 'user': u, 'role': 'master', 'client': 'حملة_حلحول'})
                st.rerun()
else:
    df = load_data(st.session_state.client)
    st.sidebar.title(f"🛡️ قائمة: {st.session_state.client}")
    menu = st.sidebar.radio("انتقل إلى:", ["🚀 الداشبورد", "📊 إحصاء العائلات", "🤝 التحالفات", "📝 الميدان", "🚪 خروج"])

    if menu == "🚀 الداشبورد":
        st.title("🚀 لوحة القيادة المركزية")
        
        # مؤشرات الحسم
        total = len(df)
        voted = len(df[df['حالة التصويت'] == 'تم التصويت'])
        target = st.sidebar.number_input("الهدف (رقم الحسم):", value=5000)
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("الكتلة الناخبة", f"{total:,}")
        c2.metric("من صوتوا", f"{voted:,}")
        c3.metric("المتبقي للفوز", f"{max(0, target - voted):,}")
        c4.metric("نسبة الإنجاز", f"{(voted/total)*100:.1f}%" if total > 0 else "0%")

        st.divider()
        
        # رسوم بيانية احترافية
        col_a, col_b = st.columns([2, 1])
        
        with col_a:
            st.subheader("📈 أعلى 10 عائلات تصويتاً (قوة الالتزام)")
            stats = df.groupby('عائلة_موحدة').agg(
                العدد=('الاسم الرباعي', 'count'),
                المصوتون=('حالة التصويت', lambda x: (x == 'تم التصويت').sum())
            ).reset_index().sort_values(by='العدد', ascending=False).head(10)
            
            fig = px.bar(stats, x='عائلة_موحدة', y=['العدد', 'المصوتون'], barmode='group',
                         labels={'value': 'عدد الأشخاص', 'عائلة_موحدة': 'العائلة'},
                         color_discrete_sequence=['#1E3A8A', '#10B981'])
            st.plotly_chart(fig, use_container_width=True)

        with col_b:
            st.subheader("🎯 الموقف الحالي")
            fig_pie = px.pie(values=[voted, total-voted], names=['تم التصويت', 'لم يصوت'],
                             hole=0.6, color_discrete_sequence=['#10B981', '#EF4444'])
            st.plotly_chart(fig_pie, use_container_width=True)

    elif menu == "📊 إحصاء العائلات":
        st.title("📊 تفصيل العائلات (قبل الانتخابات)")
        # تجميع شامل لكل العائلات
        full_stats = df.groupby('عائلة_موحدة').agg(
            العدد_الكلي=('الاسم الرباعي', 'count'),
            المصوتون=('حالة التصويت', lambda x: (x == 'تم التصويت').sum())
        ).reset_index().sort_values(by='العدد_الكلي', ascending=False)
        full_stats['النسبة %'] = (full_stats['المصوتون'] / full_stats['العدد_الكلي'] * 100).round(1)
        
        st.dataframe(full_stats, use_container_width=True)

    elif menu == "🤝 التحالفات":
        st.title("🤝 إدارة وتحليل التحالفات")
        st.info("قم بإضافة العائلات التي تشكل تحالفاً واحداً لترى قوتها مجتمعة.")
        
        # واجهة إضافة تحالف
        with st.expander("➕ إنشاء تحالف جديد"):
            all_fams = sorted(df['عائلة_موحدة'].unique())
            a_name = st.text_input("اسم التحالف:")
            selected = st.multiselect("اختر العائلات:", all_fams)
            if st.button("تحليل قوة التحالف"):
                alliance_df = df[df['عائلة_موحدة'].isin(selected)]
                st.success(f"قوة تحالف {a_name}: {len(alliance_df)} صوتاً")

    elif menu == "📝 الميدان":
        st.title("📝 تحديث الميدان (ساعة بساعة)")
        search = st.text_input("🔍 ابحث بالاسم أو العائلة:")
        if search:
            results = df[df['الاسم الرباعي'].str.contains(search, na=False) | df['اسم العائلة'].str.contains(search, na=False)]
            edited = st.data_editor(results[['الاسم الرباعي', 'اسم العائلة', 'مركز التسجيل والاقتراع', 'حالة التصويت']], use_container_width=True)
            if st.button("💾 حفظ التغييرات"):
                df.update(edited)
                df.to_csv(f"data_{st.session_state.client}.csv", index=False, encoding='utf-8-sig')
                st.success("✅ تم تحديث حالة التصويت بنجاح!")

    elif menu == "🚪 خروج":
        st.session_state.auth = False
        st.rerun()
