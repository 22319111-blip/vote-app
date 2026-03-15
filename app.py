import streamlit as st
import pandas as pd
import json
import os
import re
from io import BytesIO
from datetime import datetime

# =========================================================
# 1. إعدادات الهوية والبيئة
# =========================================================
st.set_page_config(page_title="منصة الأستاذ قصي الانتخابية", layout="wide")

USERS_FILE = 'clients_users.json'
MASTER_DATA = 'Halhul_Ultimate_Perfect.csv' 

# =========================================================
# 2. محرك الذكاء البرمجي (Logic Functions)
# =========================================================

def clean_logic(name):
    """محرك تطهير الأسماء لتوحيد العائلات"""
    if not isinstance(name, str): return ""
    name = name.strip()
    name = re.sub(r'[أإآ]', 'ا', name)
    name = re.sub(r'ة\b', 'ه', name)
    name = re.sub(r'^ال', '', name)
    name = re.sub(r'^ابو\s+', 'ابو', name)
    name = re.sub(r'^أبو\s+', 'ابو', name)
    return " ".join(name.split())

def load_users():
    if not os.path.exists(USERS_FILE):
        # حساب المالك الافتراضي (قصي)
        default = {"qusai": {"pass": "851998", "role": "master", "client_name": "الإدارة العامة", "is_temp": False}}
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(default, f, ensure_ascii=False, indent=4)
        return default
    with open(USERS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_users(u_dict):
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(u_dict, f, ensure_ascii=False, indent=4)

def load_client_data(client_name):
    """تحميل بيانات الزبون أو توليدها تلقائياً من الماستر"""
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
# 3. نظام الدخول وإدارة الجلسة
# =========================================================
if 'auth' not in st.session_state:
    st.session_state.update({'auth': False, 'user': '', 'client': '', 'role': '', 'is_temp': False})

users_db = load_users()

if not st.session_state.auth:
    st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>🏛️ منصة الأستاذ قصي للحلول الانتخابية</h1>", unsafe_allow_html=True)
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
            else: st.error("⚠️ بيانات الدخول غير صحيحة")
else:
    # --- إعداد بيئة الزبون الحالي ---
    CLIENT = st.session_state.client
    IS_TEMP = st.session_state.is_temp
    df_full = load_client_data(CLIENT)
    
    # منطق الرؤية المحدودة (النسخة التجريبية)
    df_display = df_full.head(100) if IS_TEMP else df_full

    st.sidebar.markdown(f"### 🛡️ نظام: {CLIENT}")
    if IS_TEMP: st.sidebar.error("🚨 نسخة تجريبية محدودة")
    
    menu = st.sidebar.radio("القائمة الرئيسية:", ["📊 الإحصائيات", "🎯 أهداف الحسم", "📝 تسجيل الأصوات", "📑 التقارير والطباعة", "⚙️ الإدارة", "🚪 خروج"])

    if menu == "🚪 خروج":
        st.session_state.auth = False
        st.rerun()

    # --- لوحة تحكم الأستاذ قصي (Master) ---
    if st.session_state.role == "master":
        st.sidebar.divider()
        st.sidebar.subheader("🛠️ الإدارة العليا (قصي)")
        admin_opt = st.sidebar.selectbox("إدارة القوائم:", ["نظرة عامة", "إضافة زبون جديد", "حذف قائمة نهائياً"])

        if admin_opt == "إضافة زبون جديد":
            st.header("➕ تفعيل نظام لقائمة جديدة")
            with st.form("add_form"):
                nc = st.text_input("اسم القائمة/المرشح")
                nu = st.text_input("اسم المستخدم للدخول")
                np = st.text_input("كلمة المرور")
                it = st.checkbox("تفعيل كنسخة تجريبية (رؤية أول 100 اسم فقط)")
                if st.form_submit_button("إنشاء النظام وتوليد البيانات"):
                    if nc and nu:
                        users_db[nu] = {"pass": np, "role": "owner", "client_name": nc, "is_temp": it}
                        save_users(users_db)
                        load_client_data(nc) # إنشاء الملف فوراً
                        st.success(f"تم إنشاء نظام {nc} بنجاح!")
                    else: st.error("يرجى ملء كافة الحقول")

        elif admin_opt == "حذف قائمة نهائياً":
            st.header("🗑️ حذف قائمة وتدمير بياناتها")
            st.error("⚠️ تحذير: سيتم حذف الحساب وملف الـ CSV الخاص به نهائياً.")
            targets = [u for u, info in users_db.items() if info['role'] != 'master']
            target_u = st.selectbox("اختر الحساب المراد حذفه:", targets)
            if st.button("تأكيد الحذف النهائي الشامل"):
                client_to_del = users_db[target_u]['client_name']
                if os.path.exists(f"data_{client_to_del}.csv"): os.remove(f"data_{client_to_del}.csv")
                del users_db[target_u]
                save_users(users_db)
                st.success(f"تم مسح القائمة '{client_to_del}' من النظام تماماً.")
                st.rerun()

    # --- صفحات المحتوى ---
    if df_full.empty:
        st.error(f"الملف الماستر {MASTER_DATA} غير موجود. يرجى رفعه أولاً.")
    else:
        if menu == "📊 الإحصائيات":
            st.header(f"📊 إحصائيات: {CLIENT}")
            voted = len(df_full[df_full['حالة التصويت'] == 'تم التصويت'])
            
            c1, c2, c3 = st.columns(3)
            c1.metric("الكتلة الناخبة", len(df_full) if not IS_TEMP else "100 (تجريبي)")
            c2.metric("عدد المصوتين", voted)
            c3.metric("نسبة الإنجاز", f"{(voted/len(df_full))*100:.1f}%")
            
            if IS_TEMP:
                st.warning("🔒 التحليلات العائلية محجوبة في النسخة التجريبية.")
            else:
                st.subheader("📌 ترتيب العائلات ومعدل الالتزام")
                stats = df_full.groupby('family_unified').agg(total=('الاسم الرباعي','count'), voted=('حالة التصويت', lambda x: (x=='تم التصويت').sum())).reset_index()
                stats['النسبة'] = (stats['voted']/stats['total']*100).round(1)
                st.dataframe(stats.sort_values(by='total', ascending=False), use_container_width=True)

        elif menu == "🎯 أهداف الحسم":
            if IS_TEMP:
                st.error("🚫 محاكي الحسم متاح في النسخة الكاملة فقط.")
            else:
                st.header("🎯 محاكي الوصول لبر الأمان")
                target = st.number_input("الرقم المستهدف للفوز:", value=1000)
                current = len(df_full[df_full['حالة التصويت'] == 'تم التصويت'])
                st.write(f"بقي لك **{max(0, target - current)}** صوتاً للفوز.")
                st.progress(min(1.0, current/target) if target > 0 else 0)

        elif menu == "📝 تسجيل الأصوات":
            st.header("📝 غرفة العمليات الميدانية")
            if IS_TEMP: st.info("💡 النسخة التجريبية تعرض أول 100 اسم فقط.")
            
            search = st.text_input("🔍 ابحث (الاسم أو العائلة):")
            work_df = df_display.copy()
            if search:
                clean_s = clean_logic(search)
                work_df = work_df[work_df['الاسم الرباعي'].str.contains(search, na=False) | work_df['family_unified'].str.contains(clean_s, na=False)]
            
            edited = st.data_editor(work_df[['الاسم الرباعي', 'اسم العائلة', 'اسم المركز', 'حالة التصويت']], use_container_width=True)
            if st.button("💾 حفظ التحديثات"):
                df_full.update(edited)
                save_client_data(df_full, CLIENT)
                st.success("✅ تم الحفظ بنجاح")

        elif menu == "📑 التقارير والطباعة":
            st.header("📑 استخراج الكشوفات")
            if IS_TEMP:
                st.error("🚫 وظيفة الطباعة معطلة في النسخة التجريبية.")
            else:
                col1, col2 = st.columns(2)
                with col1: sel_f = st.multiselect("فلتر حسب العائلة:", sorted(df_full['family_unified'].unique()))
                with col2: sel_c = st.selectbox("فلتر حسب المدرسة:", ["الكل"] + sorted(df_full['اسم المركز'].unique().tolist()))
                
                rep = df_full.copy()
                if sel_f: rep = rep[rep['family_unified'].isin(sel_f)]
                if sel_c != "الكل": rep = rep[rep['اسم المركز'] == sel_c]
                
                st.dataframe(rep[['الاسم الرباعي', 'اسم العائلة', 'اسم المركز', 'حالة التصويت']], use_container_width=True)
                if not rep.empty:
                    buf = BytesIO(); rep.to_excel(buf, index=False)
                    st.download_button("📥 تحميل الكشف (Excel)", buf.getvalue(), f"report_{CLIENT}.xlsx")

        elif menu == "⚙️ الإدارة":
            st.header("⚙️ إدارة بيانات القائمة")
            if st.button("🧹 تصفير كافة الأصوات (بدء يوم الانتخابات)"):
                df_full['حالة التصويت'] = 'لم يصوت'
                save_client_data(df_full, CLIENT)
                st.success("تم تصفير كافة الأصوات بنجاح.")
                st.rerun()
