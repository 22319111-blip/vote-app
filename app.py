import streamlit as st
import pandas as pd
import json
import os
import re
from io import BytesIO

# =========================================================
# 1. إعدادات المنصة وتهيئة الجلسة (مهم جداً لتفادي الأخطاء)
# =========================================================
st.set_page_config(page_title="منصة الأستاذ قصي الانتخابية", layout="wide")

if 'auth' not in st.session_state:
    st.session_state.update({'auth': False, 'user': '', 'client': '', 'role': '', 'is_temp': False})

USERS_FILE = 'clients_users.json'
MASTER_DATA = 'Halhul_Ultimate_Perfect.csv'

# =========================================================
# 2. حماية النظام الأساسي (تأمين الأعمدة والملفات)
# =========================================================
# تأمين وجود الملف الأم بأعمدته الأساسية لمنع خطأ KeyError
if not os.path.exists(MASTER_DATA):
    dummy_df = pd.DataFrame({
        "الاسم الرباعي": ["تجربة ١", "تجربة ٢"],
        "اسم العائلة": ["عائلة أ", "عائلة ب"],
        "اسم المركز": ["مدرسة ١", "مدرسة ٢"],
        "حالة التصويت": ["لم يصوت", "لم يصوت"]
    })
    dummy_df.to_csv(MASTER_DATA, index=False, encoding='utf-8-sig')

# =========================================================
# 3. محرك الدوال الذكي
# =========================================================
def clean_logic(name):
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
    filename = f"data_{client_name}.csv"
    if os.path.exists(filename):
        df = pd.read_csv(filename)
    else:
        df = pd.read_csv(MASTER_DATA)
        if 'حالة التصويت' not in df.columns:
            df['حالة التصويت'] = 'لم يصوت'
        df.to_csv(filename, index=False, encoding='utf-8-sig')
    
    # توحيد اسم العائلة إذا كان العمود موجوداً
    if not df.empty and 'اسم العائلة' in df.columns:
        df['family_unified'] = df['اسم العائلة'].apply(clean_logic)
    elif not df.empty:
        df['family_unified'] = 'غير محدد'
        
    return df

def save_client_data(df, client_name):
    filename = f"data_{client_name}.csv"
    temp = df.copy()
    if 'family_unified' in temp.columns:
        temp = temp.drop(columns=['family_unified'])
    temp.to_csv(filename, index=False, encoding='utf-8-sig')

# =========================================================
# 4. نظام تسجيل الدخول
# =========================================================
users_db = load_users()

if not st.session_state.auth:
    st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>🏛️ منصة الأستاذ قصي للحلول الانتخابية</h1>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1.5, 1])
    with c2:
        u_in = st.text_input("اسم المستخدم")
        p_in = st.text_input("كلمة المرور", type="password")
        if st.button("دخول آمن", use_container_width=True):
            if u_in in users_db and users_db[u_in]['pass'] == p_in:
                st.session_state.update({
                    'auth': True, 'user': u_in, 'role': users_db[u_in]['role'],
                    'client': users_db[u_in]['client_name'], 'is_temp': users_db[u_in].get('is_temp', False)
                })
                st.rerun()
            else:
                st.error("⚠️ بيانات الدخول غير صحيحة")
else:
    # =========================================================
    # 5. الواجهة الرئيسية للزبون
    # =========================================================
    CLIENT = st.session_state.client
    IS_TEMP = st.session_state.is_temp
    df_full = load_client_data(CLIENT)
    
    df_display = df_full.head(100) if IS_TEMP else df_full

    st.sidebar.markdown(f"### 🛡️ نظام: {CLIENT}")
    if IS_TEMP: st.sidebar.error("🚨 حساب تجريبي - رؤية محدودة")
    
    menu = st.sidebar.radio("القائمة:", ["📊 الإحصائيات", "🎯 أهداف الحسم", "📝 الميدان والتسجيل", "📑 التقارير والطباعة", "⚙️ الإدارة", "🚪 تسجيل خروج"])

    if menu == "🚪 تسجيل خروج":
        st.session_state.auth = False
        st.rerun()

    # --- لوحة التحكم الكبرى (Master) ---
    if st.session_state.role == "master":
        st.sidebar.divider()
        st.sidebar.subheader("🛠️ الإدارة العليا (قصي)")
        admin_opt = st.sidebar.selectbox("إدارة القوائم:", ["عرض", "إضافة زبون", "حذف قائمة"])

        if admin_opt == "إضافة زبون":
            with st.form("add_form"):
                nc = st.text_input("اسم القائمة")
                nu = st.text_input("اسم المستخدم")
                np = st.text_input("كلمة المرور")
                it = st.checkbox("حساب تجريبي (رؤية 100 اسم فقط ومنع الطباعة)")
                if st.form_submit_button("تفعيل الزبون"):
                    if nc and nu:
                        users_db[nu] = {"pass": np, "role": "owner", "client_name": nc, "is_temp": it}
                        save_users(users_db)
                        load_client_data(nc)
                        st.success(f"تم تفعيل {nc} بنجاح!")
                    else:
                        st.error("يرجى تعبئة الحقول")

        elif admin_opt == "حذف قائمة":
            targets = [u for u, info in users_db.items() if info['role'] != 'master']
            if targets:
                target_u = st.selectbox("اختر الحساب للحذف النهائي:", targets)
                if st.button("تأكيد تدمير البيانات"):
                    c_del = users_db[target_u]['client_name']
                    if os.path.exists(f"data_{c_del}.csv"): os.remove(f"data_{c_del}.csv")
                    del users_db[target_u]
                    save_users(users_db)
                    st.success("تم المسح الشامل.")
                    st.rerun()
            else:
                st.info("لا يوجد زبائن حالياً.")

    # --- المحتوى التفاعلي ---
    if menu == "📊 الإحصائيات":
        st.header(f"📊 إحصائيات: {CLIENT}")
        if 'حالة التصويت' in df_full.columns:
            voted = len(df_full[df_full['حالة التصويت'] == 'تم التصويت'])
        else:
            voted = 0
            
        c1, c2, c3 = st.columns(3)
        c1.metric("الكتلة الناخبة", len(df_full) if not IS_TEMP else "100 (تجريبي)")
        c2.metric("عدد المصوتين", voted)
        c3.metric("نسبة التصويت", f"{(voted/len(df_full))*100:.1f}%" if len(df_full) > 0 else "0%")
        
        if IS_TEMP:
            st.warning("🔒 التحليلات العائلية محجوبة في النسخة التجريبية.")
        elif 'family_unified' in df_full.columns:
            st.subheader("📌 التزام العائلات")
            stats = df_full.groupby('family_unified').agg(
                total=('الاسم الرباعي','count'), 
                voted=('حالة التصويت', lambda x: (x=='تم التصويت').sum())
            ).reset_index()
            stats['النسبة'] = (stats['voted']/stats['total']*100).round(1)
            st.dataframe(stats.sort_values(by='total', ascending=False), use_container_width=True)

    elif menu == "🎯 أهداف الحسم":
        if IS_TEMP: st.error("🚫 ميزة أهداف الحسم غير متاحة في النسخة التجريبية.")
        else:
            st.header("🎯 محاكي الوصول لبر الأمان")
            target = st.number_input("الرقم المستهدف:", value=1000)
            current = len(df_full[df_full['حالة التصويت'] == 'تم التصويت']) if 'حالة التصويت' in df_full.columns else 0
            st.write(f"بقي لك **{max(0, target - current)}** صوتاً.")
            st.progress(min(1.0, current/target) if target > 0 else 0)

    elif menu == "📝 الميدان والتسجيل":
        st.header("📝 غرفة العمليات الميدانية")
        search = st.text_input("🔍 ابحث عن اسم:")
        work_df = df_display.copy()
        
        if search and 'الاسم الرباعي' in work_df.columns:
            work_df = work_df[work_df['الاسم الرباعي'].str.contains(search, na=False)]
        
        # عرض الأعمدة المتاحة فقط لتجنب أي خطأ
        cols_to_show = [c for c in ['الاسم الرباعي', 'اسم العائلة', 'اسم المركز', 'حالة التصويت'] if c in work_df.columns]
        
        if cols_to_show:
            edited = st.data_editor(work_df[cols_to_show], use_container_width=True)
            if st.button("💾 حفظ"):
                df_full.update(edited)
                save_client_data(df_full, CLIENT)
                st.success("تم الحفظ بنجاح")
        else:
            st.error("الأعمدة المطلوبة غير موجودة في ملف البيانات.")

    elif menu == "📑 التقارير والطباعة":
        if IS_TEMP: 
            st.error("🚫 الطباعة معطلة للحسابات التجريبية.")
        else:
            st.header("📑 التقارير")
            if 'family_unified' in df_full.columns:
                sel_f = st.multiselect("اختر العائلة:", sorted(df_full['family_unified'].astype(str).unique()))
                rep = df_full[df_full['family_unified'].isin(sel_f)] if sel_f else df_full
                
                cols_to_show = [c for c in ['الاسم الرباعي', 'اسم العائلة', 'اسم المركز', 'حالة التصويت'] if c in rep.columns]
                st.dataframe(rep[cols_to_show] if cols_to_show else rep, use_container_width=True)
                
                if not rep.empty:
                    buf = BytesIO()
                    rep.to_excel(buf, index=False)
                    st.download_button("📥 تحميل الكشف (Excel)", buf.getvalue(), f"report_{CLIENT}.xlsx")

    elif menu == "⚙️ الإدارة":
        st.header("⚙️ إدارة القائمة")
        if st.button("🧹 تصفير كل الأصوات"):
            if 'حالة التصويت' in df_full.columns:
                df_full['حالة التصويت'] = 'لم يصوت'
                save_client_data(df_full, CLIENT)
                st.success("تم التصفير.")
                st.rerun()
            else:
                st.warning("عمود حالة التصويت غير موجود بعد.")
