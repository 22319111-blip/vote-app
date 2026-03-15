import streamlit as st
import pandas as pd
import os

# إعدادات الصفحة
st.set_page_config(page_title="نظام قصي أبوصايمة الرقمي", layout="wide")

DATA_FILE = 'Halhul_Ultimate_Perfect.csv'

# دالة تحميل البيانات
def load_data():
    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE)
        if 'حالة التصويت' not in df.columns:
            df['حالة التصويت'] = 'لم يصوت'
        return df
    return pd.DataFrame(columns=['الاسم الرباعي', 'اسم العائلة', 'اسم المركز', 'حالة التصويت'])

# نظام الدخول
if 'auth' not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔑 تسجيل الدخول")
    u = st.text_input("اسم المستخدم")
    p = st.text_input("كلمة المرور", type="password")
    if st.button("دخول"):
        if u == "qusai" and p == "851998":
            st.session_state.auth = True
            st.rerun()
        else:
            st.error("البيانات خاطئة")
else:
    df = load_data()
    st.sidebar.title(f"مرحباً قصي")
    menu = st.sidebar.radio("القائمة", ["غرفة العمليات", "البحث", "المتبقين", "خروج"])

    if menu == "خروج":
        st.session_state.auth = False
        st.rerun()

    elif menu == "غرفة العمليات":
        st.header("📝 تسجيل التصويت الميداني")
        center = st.selectbox("اختر المركز", ["الكل"] + list(df['اسم المركز'].unique()))
        m_df = df if center == "الكل" else df[df['اسم المركز'] == center]
        
        search = st.text_input("بحث بالاسم")
        if search:
            m_df = m_df[m_df['الاسم الرباعي'].str.contains(search, na=False)]
        
        edited = st.data_editor(m_df[['الاسم الرباعي', 'اسم العائلة', 'حالة التصويت']].head(200), use_container_width=True)
        
        if st.button("💾 حفظ البيانات"):
            df.update(edited)
            df.to_csv(DATA_FILE, index=False, encoding='utf-8-sig')
            st.success("تم التحديث والحفظ بنجاح!")

    elif menu == "البحث":
        name = st.text_input("ابحث عن ناخب")
        if name:
            st.table(df[df['الاسم الرباعي'].str.contains(name, na=False)].head(20))

    elif menu == "المتبقين":
        fams = st.multiselect("اختر العائلات", sorted(df['اسم العائلة'].unique().tolist()))
        if fams:
            res = df[(df['اسم العائلة'].isin(fams)) & (df['حالة التصويت'] == 'لم يصوت')]
            st.warning(f"متبقي {len(res)} لم يصوتوا")
            st.dataframe(res[['الاسم الرباعي', 'اسم المركز']])