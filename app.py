import streamlit as st
import pandas as pd
import json
import os
import plotly.express as px
import re
from io import BytesIO
from datetime import datetime

# --- 1. إعدادات الهوية البصرية ---
st.set_page_config(page_title="نظام الأستاذ قصي الانتخابي", layout="wide", initial_sidebar_state="expanded")

DATA_FILE = 'Halhul_Ultimate_Perfect.csv'
USERS_FILE = 'users.json'

# --- 2. محرك التطهير والتوحيد الذكي للأسماء ---
def clean_logic(name):
    if not isinstance(name, str): return ""
    name = name.strip()
    # توحيد الهمزات والتاء المربوطة
    name = re.sub(r'[أإآ]', 'ا', name)
    name = re.sub(r'ة\b', 'ه', name)
    # حذف ال التعريف من البداية
    name = re.sub(r'^ال', '', name)
    # توحيد "أبو" وإزالة المسافات بعدها
    name = re.sub(r'^ابو\s+', 'ابو', name)
    name = re.sub(r'^أبو\s+', 'ابو', name)
    # إزالة المسافات الزائدة في المنتصف
    name = " ".join(name.split())
    return name

# --- 3. إدارة البيانات ---
def load_data():
    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE)
        if 'حالة التصويت' not in df.columns: df['حالة التصويت'] = 'لم يصوت'
        # عمود مخفي للربط الإحصائي
        df['family_unified'] = df['اسم العائلة'].apply(clean_logic)
        return df
    return pd.DataFrame(columns=['الاسم الرباعي', 'اسم العائلة', 'اسم المركز', 'حالة التصويت'])

def save_data(df):
    temp_df = df.copy()
    if 'family_unified' in temp_df.columns: temp_df = temp_df.drop(columns=['family_unified'])
    temp_df.to_csv(DATA_FILE, index=False, encoding='utf-8-sig')

def load_users():
    if not os.path.exists(USERS_FILE):
        return {"qusai": {"pass": "851998", "role": "owner", "is_temp": False, "families": ["الكل"]}}
    with open(USERS_FILE, 'r', encoding='utf-8') as f: return json.load(f)

def save_users(u):
    with open(USERS_FILE, 'w', encoding='utf-8') as f: json.dump(u, f, ensure_ascii=False, indent=4)

# --- 4. نظام الدخول والأمن ---
if 'auth' not in st.session_state: st.session_state.update({'auth': False, 'user': '', 'role': '', 'is_temp': False})
users = load_users()

if not st.session_state.auth:
    st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>🏛️ نظام الأستاذ قصي الانتخابي</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        u = st.text_input("اسم المستخدم")
        p = st.text_input("كلمة المرور", type="password")
        if st.button("دخول للنظام المركزي", use_container_width=True):
            if u in users and users[u]['pass'] == p:
                st.session_state.update({'auth': True, 'user': u, 'role': users[u]['role'], 'is_temp': users[u].get('is_temp', False)})
                st.rerun()
            else: st.error("⚠️ بيانات الدخول غير صحيحة")
else:
    df = load_data()
    user_info = users[st.session_state.user]

    # --- القائمة الجانبية ---
    st.sidebar.markdown(f"### 👤 مرحباً أستاذ {st.session_state.user}")
    
    menu_list = ["📊 إحصائيات الحسم", "🔍 استكشاف العائلات", "📝 تسجيل الأصوات", "📑 التقارير والطباعة"]
    if st.session_state.role == "owner": menu_list.append("⚙️ إدارة الطاقم والأمن")
    
    menu = st.sidebar.radio("انتقل إلى:", menu_list + ["🚪 خروج"])

    if menu == "🚪 خروج":
        st.session_state.auth = False
        st.rerun()

    # --- 1. إحصائيات الحسم (Targeting) ---
    elif menu == "📊 إحصائيات الحسم":
        st.header("📊 لوحة مراقبة نسبة الحسم")
        
        target = st.number_input("حدد هدفك من الأصوات للفوز:", value=1000)
        voted_total = len(df[df['حالة التصويت'] == 'تم التصويت'])
        
        c1, c2, c3 = st.columns(3)
        c1.metric("الأصوات المحصودة", voted_total)
        c2.metric("المتبقي للهدف", max(0, target - voted_total))
        c3.progress(min(1.0, voted_total/target), text=f"نسبة الإنجاز: {(voted_total/target)*100:.1f}%")
        
        st.divider()
        st.subheader("🚩 عائلات في منطقة الخطر (التزام أقل من 30%)")
        f_stats = df.groupby('family_unified').agg(total=('الاسم الرباعي','count'), done=('حالة التصويت', lambda x: (x=='تم التصويت').sum()))
        f_stats['النسبة'] = (f_stats['done'] / f_stats['total'] * 100).round(1)
        danger = f_stats[f_stats['النسبة'] < 30].sort_values(by='total', ascending=False)
        st.table(danger.head(10))

    # --- 2. استكشاف العائلات والتحالفات ---
    elif menu == "🔍 استكشاف العائلات":
        st.header("🤝 محاكي التحالفات والوزن العائلي")
        all_unique_fams = sorted(df['family_unified'].unique())
        selected = st.multiselect("اختر العائلات لدراسة وزنها (يتم دمج الأسماء المتشابهة آلياً):", all_unique_fams)
        
        if selected:
            alliance = df[df['family_unified'].isin(selected)]
            st.success(f"الكتلة الناخبة لهذا التحالف: {len(alliance)} صوتاً")
            fig = px.pie(alliance, names='family_unified', title="توزيع القوة داخل التحالف")
            st.plotly_chart(fig, use_container_width=True)

    # --- 3. تسجيل الأصوات (الميدان) ---
    elif menu == "📝 تسجيل الأصوات":
        st.header("📝 غرفة العمليات الميدانية")
        
        # صلاحيات المندوب (يرى عائلاته فقط إذا لم يكن سوبر)
        work_df = df.copy()
        if st.session_state.role == "manager":
            work_df = work_df[work_df['family_unified'].isin([clean_logic(f) for f in user_info['families']])]
        
        search = st.text_input("🔍 ابحث عن اسم أو عائلة (البحث ذكي يتخطى ال التعريف والمسافات)")
        if search:
            s_clean = clean_logic(search)
            work_df = work_df[work_df['الاسم الرباعي'].str.contains(search, na=False) | work_df['family_unified'].str.contains(s_clean, na=False)]
        
        edited = st.data_editor(work_df[['الاسم الرباعي', 'اسم العائلة', 'حالة التصويت']], use_container_width=True)
        if st.button("💾 حفظ التعديلات الآن"):
            df.update(edited)
            save_data(df)
            st.success("✅ تم تحديث قاعدة البيانات بنجاح!")

    # --- 4. التقارير والطباعة (محمية) ---
    elif menu == "📑 التقارير والطباعة":
        st.header("📑 استخراج كشوفات الطباعة")
        if st.session_state.is_temp:
            st.error("🚫 عذراً أستاذ قصي.. هذا الحساب (مؤقت) ولا يملك صلاحية سحب أو طباعة التقارير.")
        else:
            f_center = st.selectbox("اختر المدرسة/المركز", ["الكل"] + sorted(df['اسم المركز'].unique().tolist()))
            report_df = df[df['اسم المركز'] == f_center] if f_center != "الكل" else df
            st.dataframe(report_df.head(100))
            
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                report_df.to_excel(writer, index=False)
            st.download_button("📥 تحميل الكشف للطباعة (Excel)", data=output.getvalue(), file_name=f"kashf_{f_center}.xlsx")

    # --- 5. إدارة الطاقم (حكر للأستاذ قصي) ---
    elif menu == "⚙️ إدارة الطاقم والأمن":
        st.header("⚙️ لوحة التحكم في الصلاحيات")
        with st.expander("➕ إضافة كادر جديد (سوبر مدير أو مندوب)"):
            nu = st.text_input("اسم المستخدم")
            np = st.text_input("كلمة السر")
            nr = st.selectbox("الرتبة", ["سوبر_مدير", "مندوب_عائلة"])
            is_t = st.checkbox("تعيين كحساب مؤقت (يُمنع من الطباعة والتصدير)")
            nf = st.multiselect("العائلات المسؤول عنها (للمناديب فقط)", sorted(df['family_unified'].unique().tolist()), default=["الكل"])
            
            if st.button("اعتماد الحساب"):
                users[nu] = {"pass": np, "role": "super_admin" if nr == "سوبر_مدير" else "manager", "is_temp": is_t, "families": nf}
                save_users(users)
                st.success(f"تم إنشاء حساب {nu} بنجاح!")
                st.rerun()

        st.subheader("👥 الحسابات النشطة حالياً")
        for u_name, u_data in list(users.items()):
            col1, col2, col3, col4 = st.columns([1,1,2,1])
            col1.write(f"**{u_name}**")
            col2.write(u_data['role'])
            col3.write("مؤقت" if u_data.get('is_temp') else "دائم")
            if u_name == "qusai":
                col4.write("🔒 المالك")
            else:
                if col4.button("حذف", key=u_name):
                    del users[u_name]
                    save_users(users)
                    st.rerun()
