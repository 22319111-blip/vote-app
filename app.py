import streamlit as st
import pandas as pd
import json
import os
import re
from io import BytesIO

# =========================================================
# 1. إعدادات المنصة وقاموس المدارس الذكي
# =========================================================
st.set_page_config(page_title="منصة الأستاذ قصي الانتخابية", layout="wide")

if 'auth' not in st.session_state:
    st.session_state.update({'auth': False, 'user': '', 'client': '', 'role': '', 'is_temp': False})

USERS_FILE = 'clients_users.json'
MASTER_DATA = 'Halhul_Ultimate_Perfect.csv'

# === القاموس الذكي للمراكز ===
KNOWN_CENTERS = [
    "بنات حلحول الثانوية", "ذكور حلحول الثانوية", "اليرموك الأساسية",
    "بنات محمود السنجق", "القادسية", "الرشيد", "اليرموك",
    "بنات حلحول", "ذكور حلحول", "بلدية حلحول"
]
KNOWN_CENTERS.sort(key=len, reverse=True)

# === فلتر الشظايا ===
SCHOOL_KEYWORDS = [
    'مدرسة', 'ذكور', 'اناث', 'إناث', 'بنات', 'بنين', 'للبنين', 'للبنات', 
    'ثانوية', 'الثانوية', 'اساسية', 'الاساسية', 'أساسية', 'الأساسية', 
    'مختلطة', 'المختلطة', 'اعدادية', 'الاعدادية', 'ابتدائية', 'الابتدائية'
]

def is_school_text(text):
    if 'مدرسة' in text: return True
    return any(c in text for c in KNOWN_CENTERS)

def extract_actual_school(text):
    match = re.search(r'(مدرسة.*?(بنين|بنات|ثانوية|أساسية|اساسية|مختلطة))', text)
    if match: return match.group(1)
    for center in KNOWN_CENTERS:
        if center in text: return center
    return ""

def deep_clean_name(name_text, actual_school=""):
    """دالة التنظيف العميق لإزالة اسم المدرسة وشظاياها"""
    if not isinstance(name_text, str): return ""
    
    if actual_school:
        name_text = name_text.replace(actual_school, ' ')
        
    for c in KNOWN_CENTERS:
        name_text = name_text.replace(c, ' ')
        
    for kw in SCHOOL_KEYWORDS:
        name_text = re.sub(fr'\b{kw}\b', ' ', name_text)
        
    return re.sub(r'\s+', ' ', name_text).strip()

# =========================================================
# 2. الماسح الشامل الموجه بدقة
# =========================================================
def fix_all_shifted_data(df):
    df = df.reset_index(drop=True)
    
    for i in df.index:
        center_raw = str(df.loc[i, 'اسم المركز']).strip()
        first_name = str(df.loc[i, 'الاسم الاول']).strip()
        full_name_raw = str(df.loc[i, 'الاسم الرباعي']).strip()
        
        if center_raw.lower() == 'nan': center_raw = ''
        if first_name.lower() == 'nan': first_name = ''
        if full_name_raw.lower() == 'nan': full_name_raw = ''

        # ==================================================================
        # المرحلة 1: إنقاذ "الاسم الأول" (الماسح العمودي يعمل هنا فقط!)
        # ==================================================================
        if is_school_text(first_name):
            actual_school = extract_actual_school(first_name)
            
            # الماسح العمودي: لأن خلية "الاسم الأول" تحتوي على مدرسة، نستنتج المركز من الجيران إذا لزم الأمر
            if not actual_school:
                prev_school = str(df.loc[i-1, 'اسم المركز']).strip() if i > 0 else ""
                next_school = str(df.loc[i+1, 'اسم المركز']).strip() if i < len(df) - 1 else ""
                if is_school_text(prev_school) and is_school_text(next_school) and prev_school == next_school:
                    actual_school = prev_school
            
            # إذا فشل الماسح العمودي، نبحث في الاسم الرباعي
            if not actual_school:
                found_in_full = extract_actual_school(full_name_raw)
                if found_in_full:
                    actual_school = found_in_full

            # استخلاص النص الذي يأتي "بعد" المدرسة (إن وجد)
            remaining_after_school = deep_clean_name(first_name, actual_school)
            
            # التقاط الكلمة الأولى بعد المدرسة كاسم أول
            if remaining_after_school:
                words = remaining_after_school.split()
                first_name = words[0]
            else:
                first_name = "" 

            df.loc[i, 'الاسم الاول'] = first_name
            if actual_school and not is_school_text(center_raw):
                center_raw = actual_school

        # ==================================================================
        # المرحلة 2: تنظيف المركز والاسم الرباعي 
        # ==================================================================
        # هنا تم إزالة الماسح العمودي بناءً على توجيهك (يعمل فقط للاسم الأول)
        if is_school_text(center_raw) or is_school_text(full_name_raw):
            actual_school = extract_actual_school(center_raw)
            if not actual_school: actual_school = extract_actual_school(full_name_raw)

            remaining_text = deep_clean_name(center_raw, actual_school)
            clean_full = deep_clean_name(full_name_raw, actual_school)

            # إذا كان الاسم الأول فارغاً وهناك نص متبقي
            if remaining_text and not first_name:
                first_name = remaining_text.split()[0]
                df.loc[i, 'الاسم الاول'] = first_name

            if remaining_text: 
                words = remaining_text.split()
                if len(words) >= 4:
                    df.loc[i, 'الاسم الرباعي'] = remaining_text
                else:
                    if first_name and not remaining_text.startswith(first_name):
                        df.loc[i, 'الاسم الرباعي'] = f"{first_name} {remaining_text}".strip()
                    else:
                        df.loc[i, 'الاسم الرباعي'] = remaining_text
            else:
                if clean_full and not first_name:
                    first_name = clean_full.split()[0]
                    df.loc[i, 'الاسم الاول'] = first_name
                    
                words_full = clean_full.split()
                if len(words_full) >= 4:
                    df.loc[i, 'الاسم الرباعي'] = clean_full
                elif len(words_full) > 0 and len(words_full) <= 3:
                    if first_name and not clean_full.startswith(first_name):
                        df.loc[i, 'الاسم الرباعي'] = f"{first_name} {clean_full}".strip()
                    else:
                        df.loc[i, 'الاسم الرباعي'] = clean_full

            df.loc[i, 'اسم المركز'] = actual_school if actual_school else 'غير محدد'

        # ==================================================================
        # المرحلة 3: زحف كامل (لا مدرسة ولا اسم مركز معروف)
        # ==================================================================
        elif center_raw and not is_school_text(center_raw) and center_raw != 'غير محدد':
            words = center_raw.split()
            if len(words) >= 4:
                df.loc[i, 'الاسم الرباعي'] = center_raw
            else:
                if first_name and not center_raw.startswith(first_name):
                    df.loc[i, 'الاسم الرباعي'] = f"{first_name} {center_raw}".strip()
                else:
                    df.loc[i, 'الاسم الرباعي'] = center_raw
            
            df.loc[i, 'اسم المركز'] = 'غير محدد'

    return df

def extract_and_clean_family(full_name):
    if pd.isna(full_name) or not isinstance(full_name, str) or not full_name.strip(): return "غير محدد"
    
    clean_name = re.sub(r'\s+', ' ', full_name.strip())
    words = clean_name.split()
    
    if len(words) == 1: fam = words[0]
    else:
        prefixes = ['ابو', 'أبو', 'عبد', 'بن', 'بني', 'آل', 'الحاج', 'حاج', 'ام', 'أم']
        if words[-2] in prefixes: fam = f"{words[-2]} {words[-1]}"
        else: fam = words[-1]
            
    fam = re.sub(r'[أإآ]', 'ا', fam)
    fam = re.sub(r'ة\b', 'ه', fam)
    fam = re.sub(r'^ال', '', fam)
    fam = re.sub(r'\s+ال', ' ', fam)
    fam = re.sub(r'\s+', ' ', fam).strip()
    return fam

def load_users():
    if not os.path.exists(USERS_FILE):
        default = {"qusai": {"pass": "851998", "role": "master", "client_name": "الإدارة العامة", "is_temp": False}}
        with open(USERS_FILE, 'w', encoding='utf-8') as f: json.dump(default, f, ensure_ascii=False, indent=4)
        return default
    with open(USERS_FILE, 'r', encoding='utf-8') as f: return json.load(f)

def save_users(u_dict):
    with open(USERS_FILE, 'w', encoding='utf-8') as f: json.dump(u_dict, f, ensure_ascii=False, indent=4)

def load_client_data(client_name):
    filename = f"data_{client_name}.csv"
    try:
        if os.path.exists(filename): df = pd.read_csv(filename, dtype=str, keep_default_na=False)
        else:
            if not os.path.exists(MASTER_DATA):
                dummy = pd.DataFrame({"الاسم الاول": ["أحمد"], "الاسم الرباعي": ["أحمد محمد علي"], "اسم المركز": ["مدرسة ١"], "حالة التصويت": ["لم يصوت"]})
                dummy.to_csv(MASTER_DATA, index=False, encoding='utf-8-sig')
            df = pd.read_csv(MASTER_DATA, dtype=str, keep_default_na=False)
            if 'حالة التصويت' not in df.columns: df['حالة التصويت'] = 'لم يصوت'
            df.to_csv(filename, index=False, encoding='utf-8-sig')
        
        if not df.empty and 'اسم المركز' in df.columns and 'الاسم الاول' in df.columns:
            df = fix_all_shifted_data(df)
            
        if not df.empty and 'الاسم الرباعي' in df.columns:
            df['family_unified'] = df['الاسم الرباعي'].apply(extract_and_clean_family)
            if 'اسم العائلة' not in df.columns: df['اسم العائلة'] = df['family_unified']
                
        return df
    except Exception as e:
        st.error(f"⚠️ خطأ في قراءة الملف: {e}")
        return pd.DataFrame()

def save_client_data(df, client_name):
    filename = f"data_{client_name}.csv"
    temp = df.copy()
    if 'family_unified' in temp.columns: temp = temp.drop(columns=['family_unified'])
    temp.to_csv(filename, index=False, encoding='utf-8-sig')

# =========================================================
# 3. نظام تسجيل الدخول
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
                st.session_state.update({'auth': True, 'user': u_in, 'role': users_db[u_in]['role'], 'client': users_db[u_in]['client_name'], 'is_temp': users_db[u_in].get('is_temp', False)})
                st.rerun()
            else: st.error("⚠️ بيانات الدخول غير صحيحة")
else:
    # =========================================================
    # 4. الواجهة الرئيسية
    # =========================================================
    CLIENT = st.session_state.client
    IS_TEMP = st.session_state.is_temp
    df_full = load_client_data(CLIENT)
    
    if df_full.empty:
        st.warning("ملف البيانات فارغ أو غير موجود.")
        st.stop()
        
    df_display = df_full.head(100) if IS_TEMP else df_full

    st.sidebar.markdown(f"### 🛡️ نظام: {CLIENT}")
    if IS_TEMP: st.sidebar.error("🚨 حساب تجريبي - رؤية محدودة")
    
    menu = st.sidebar.radio("القائمة:", ["📊 الإحصائيات", "🎯 أهداف الحسم", "📝 الميدان والتسجيل", "📑 التقارير والطباعة", "⚙️ الإدارة", "🚪 تسجيل خروج"])

    if menu == "🚪 تسجيل خروج":
        st.session_state.auth = False
        st.rerun()

    # --- إدارة قصي العليا ---
    if st.session_state.role == "master":
        st.sidebar.divider()
        st.sidebar.subheader("🛠️ الإدارة العليا (قصي)")
        admin_opt = st.sidebar.selectbox("إدارة القوائم:", ["عرض", "إضافة زبون", "حذف قائمة"])

        if admin_opt == "إضافة زبون":
            with st.form("add_form"):
                nc = st.text_input("اسم القائمة")
                nu = st.text_input("اسم المستخدم")
                np = st.text_input("كلمة المرور")
                it = st.checkbox("حساب تجريبي (رؤية 100 اسم فقط)")
                if st.form_submit_button("تفعيل الزبون"):
                    if nc and nu:
                        users_db[nu] = {"pass": np, "role": "owner", "client_name": nc, "is_temp": it}
                        save_users(users_db)
                        load_client_data(nc)
                        st.success(f"تم تفعيل {nc} بنجاح!")
                        st.rerun()

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

    # --- الشاشات ---
    if menu == "📊 الإحصائيات":
        st.header(f"📊 إحصائيات: {CLIENT}")
        if 'حالة التصويت' in df_full.columns: voted = len(df_full[df_full['حالة التصويت'] == 'تم التصويت'])
        else: voted = 0
            
        c1, c2, c3 = st.columns(3)
        c1.metric("الكتلة الناخبة", len(df_full) if not IS_TEMP else "100 (تجريبي)")
        c2.metric("عدد المصوتين", voted)
        c3.metric("نسبة التصويت", f"{(voted/len(df_full))*100:.1f}%" if len(df_full) > 0 else "0%")
        
        if IS_TEMP: st.warning("🔒 التحليلات العائلية محجوبة في النسخة التجريبية.")
        elif 'family_unified' in df_full.columns:
            st.subheader("📌 التزام العائلات (مستخرج آلياً ومصحح)")
            stats = df_full.groupby('family_unified').agg(total=('الاسم الرباعي','count'), voted=('حالة التصويت', lambda x: (x=='تم التصويت').sum())).reset_index()
            stats.rename(columns={'family_unified': 'اسم العائلة', 'total': 'العدد الكلي', 'voted': 'المصوتون'}, inplace=True)
            stats['نسبة الحضور %'] = (stats['المصوتون']/stats['العدد الكلي']*100).round(1)
            st.dataframe(stats.sort_values(by='العدد الكلي', ascending=False), use_container_width=True)

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
        search = st.text_input("🔍 ابحث عن اسم (الاسم الرباعي):")
        work_df = df_display.copy()
        
        if search and 'الاسم الرباعي' in work_df.columns:
            clean_search = re.sub(r'\s+', ' ', search.strip())
            work_df = work_df[work_df['الاسم الرباعي'].str.replace(r'\s+', ' ', regex=True).str.contains(clean_search, na=False)]
        
        cols_to_show = [c for c in ['الاسم الرباعي', 'اسم العائلة', 'اسم المركز', 'حالة التصويت'] if c in work_df.columns]
        
        if cols_to_show:
            edited = st.data_editor(work_df[cols_to_show], use_container_width=True)
            if st.button("💾 حفظ البيانات"):
                df_full.update(edited)
                save_client_data(df_full, CLIENT)
                st.success("تم الحفظ بنجاح!")

    elif menu == "📑 التقارير والطباعة":
        if IS_TEMP: st.error("🚫 الطباعة معطلة للحسابات التجريبية.")
        else:
            st.header("📑 التقارير والكشوفات")
            unvoted_only = st.checkbox("🚨 عرض الذين لم يصوتوا فقط (لساعات الحسم)", value=False)
            rep = df_full.copy()
            if unvoted_only and 'حالة التصويت' in rep.columns: rep = rep[rep['حالة التصويت'] != 'تم التصويت']
                
            if 'family_unified' in rep.columns:
                sel_f = st.multiselect("فلترة حسب العائلة:", sorted(df_full['family_unified'].astype(str).unique()))
                if sel_f: rep = rep[rep['family_unified'].isin(sel_f)]
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
                st.success("تم التصفير بنجاح.")
                st.rerun()
