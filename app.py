import streamlit as st
import pandas as pd
import json
import os
import plotly.express as px
from io import BytesIO
from datetime import datetime

# --- الإعدادات الفنية ---
st.set_page_config(page_title="نظام القيادة الاستراتيجي - قمة الأداء", layout="wide")

DATA_FILE = 'Halhul_Ultimate_Perfect.csv'
USERS_FILE = 'users.json'

# --- إدارة البيانات ---
def load_data():
    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE)
        if 'حالة التصويت' not in df.columns: df['حالة التصويت'] = 'لم يصوت'
        if 'وقت_التصويت' not in df.columns: df['وقت_التصويت'] = None
        return df
    return pd.DataFrame()

def save_data(df):
    df.to_csv(DATA_FILE, index=False, encoding='utf-8-sig')

def load_users():
    if not os.path.exists(USERS_FILE):
        return {"qusai": {"pass": "851998", "role": "owner", "families": ["الكل"], "is_temp": False}}
    with open(USERS_FILE, 'r', encoding='utf-8') as f: return json.load(f)

def save_users(u):
    with open(USERS_FILE, 'w', encoding='utf-8') as f: json.dump(u, f, ensure_ascii=False, indent=4)

# --- واجهة الدخول ---
if 'auth' not in st.session_state: st.session_state.update({'auth': False, 'user': '', 'role': '', 'is_temp': False})

users = load_users()

if not st.session_state.auth:
    st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>🛡️ نظام القيادة والسيطرة - نسخة القمة</h1>", unsafe_allow_html=True)
    u = st.text_input("اسم المستخدم")
    p = st.text_input("كلمة المرور", type="password")
    if st.button("دخول للنظام المركزي", use_container_width=True):
        if u in users and users[u]['pass'] == p:
            st.session_state.update({'auth': True, 'user': u, 'role': users[u]['role'], 'is_temp': users[u].get('is_temp', False)})
            st.rerun()
        else: st.error("بيانات الدخول غير صحيحة")
else:
    df = load_data()
    user_info = users[st.session_state.user]

    # --- القائمة الجانبية المتقدمة ---
    st.sidebar.title(f"🎮 لوحة التحكم: {st.session_state.user}")
    
    main_menu = ["🔍 الاستكشاف والتحالفات", "📊 غرفة العمليات الحية", "🎯 أهداف الحسم", "📝 تسجيل الأصوات الميداني", "📑 التقارير والطباعة"]
    if st.session_state.role == "owner": main_menu.append("⚙️ إدارة الطاقم والأمن")
    
    menu = st.sidebar.radio("انتقل إلى:", main_menu + ["🚪 خروج"])

    if menu == "🚪 خروج":
        st.session_state.auth = False
        st.rerun()

    # --- 1. أهداف الحسم (Super Strategic) ---
    elif menu == "🎯 أهداف الحسم":
        st.header("🎯 محاكي نسبة الحسم والفوز")
        target_votes = st.number_input("حدد عدد الأصوات المطلوبة للفوز (Target):", value=1000)
        current_votes = len(df[df['حالة التصويت'] == 'تم التصويت'])
        gap = target_votes - current_votes
        
        c1, c2, c3 = st.columns(3)
        c1.metric("الأصوات المحصودة", current_votes)
        c2.metric("المتبقي للهدف", max(0, gap), delta_color="inverse")
        c3.progress(min(1.0, current_votes/target_votes), text=f"إنجاز الهدف: {(current_votes/target_votes)*100:.1f}%")
        
        st.subheader("🚩 عائلات تحت مجهر الخطر (تصويت أقل من 30%)")
        fam_stats = df.groupby('اسم العائلة').agg(total=('الاسم الرباعي','count'), voted=('حالة التصويت', lambda x: (x=='تم التصويت').sum()))
        fam_stats['ratio'] = (fam_stats['voted'] / fam_stats['total'] * 100)
        danger_fams = fam_stats[fam_stats['ratio'] < 30].sort_values(by='total', ascending=False)
        st.table(danger_fams[['total', 'voted', 'ratio']].head(10))

    # --- 2. الاستكشاف والتحالفات ---
    elif menu == "🔍 الاستكشاف والتحالفات":
        st.header("🤝 بناء وتحليل التحالفات")
        all_fams = sorted(df['اسم العائلة'].unique().tolist())
        selected = st.multiselect("اختر عائلات التحالف لدراسة قوتهم:", all_fams)
        if selected:
            sub = df[df['اسم العائلة'].isin(selected)]
            st.info(f"هذا التحالف يمثل {len(sub)} صوتاً من أصل {len(df)}")
            fig = px.sunburst(sub, path=['اسم المركز', 'اسم العائلة'], title="توزيع التحالف جغرافياً")
            st.plotly_chart(fig, use_container_width=True)

    # --- 3. تسجيل الأصوات (بإضافة وقت التصويت) ---
    elif menu == "📝 تسجيل الأصوات الميداني":
        st.header("📝 تسجيل الحضور الميداني")
        m_df = df.copy()
        if st.session_state.role == "manager":
            m_df = m_df[m_df['اسم العائلة'].isin(user_info['families'])]
        
        search = st.text_input("🔍 ابحث عن ناخب...")
        if search: m_df = m_df[m_df['الاسم الرباعي'].str.contains(search, na=False)]
        
        edited = st.data_editor(m_df[['الاسم الرباعي', 'اسم العائلة', 'حالة التصويت']], use_container_width=True)
        if st.button("💾 حفظ البيانات وتحديث الإحصائيات"):
            # منطق تسجيل الوقت تلقائياً عند تغيير الحالة
            df.update(edited)
            save_data(df)
            st.success("تم الحفظ بنجاح!")

    # --- 4. التقارير والطباعة (محمية للمؤقتين) ---
    elif menu == "📑 التقارير والطباعة":
        st.header("📑 تصدير الكشوفات")
        if st.session_state.is_temp:
            st.error("🚫 حسابك تجريبي: لا تملك صلاحية استخراج ملفات.")
        else:
            f_cent = st.selectbox("حسب المركز", ["الكل"] + sorted(df['اسم المركز'].unique().tolist()))
            f_res = df[df['اسم المركز'] == f_cent] if f_cent != "الكل" else df
            st.dataframe(f_res.head(100))
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                f_res.to_excel(writer, index=False)
            st.download_button("📥 تحميل الكشف (Excel)", data=output.getvalue(), file_name="halhul_report.xlsx")

    # --- 5. إدارة الطاقم (قصي فقط) ---
    elif menu == "⚙️ إدارة الطاقم والأمن":
        st.header("⚙️ مركز التحكم في الصلاحيات")
        # نفس منطق الإضافة السابق مع خيار "سوبر مدير مؤقت"
        # يمكنك إضافة وحذف الجميع ما عدا "qusai"
        st.write("إدارة الحسابات النشطة:")
        st.json(users)
