import streamlit as st
import pandas as pd
import plotly.express as px
import json
import os
import re
from io import BytesIO

# =========================================================
# 1. الإعدادات الأساسية
# =========================================================
st.set_page_config(page_title="نظام إدارة الحملات - الأستاذ قصي", layout="wide")

USERS_FILE = 'system_users.json' 
# الرادار الذكي للبحث عن ملفك أياً كان اسمه
POSSIBLE_FILES = ['Halhul_Ultimate_Perfect.csv.xlsx', 'حلحول (1).xlsx - حَلْحُول.csv', 'data.csv', 'data.xlsx']

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ''
    st.session_state.role = ''
    st.session_state.client = ''
    st.session_state.centers = []
    st.session_state.families = []

# =========================================================
# 2. خوارزميات معالجة البيانات
# =========================================================
def clean_family_name(text):
    if not isinstance(text, str) or not text.strip(): return "غير محدد"
    t = text.strip()
    t = re.sub(r'[أإآ]', 'ا', t) 
    t = re.sub(r'ة\b', 'ه', t)   
    if t.startswith('ال'): t = t[2:] 
    return t.strip()

def process_master_file():
    target_file = None
    for f in POSSIBLE_FILES:
        if os.path.exists(f):
            target_file = f
            break
            
    if not target_file:
        st.error("⚠️ لم يتم العثور على ملف البيانات الأساسي! تأكد من وجوده بجانب الكود.")
        return pd.DataFrame()

    df = pd.DataFrame()
    try:
        if target_file.endswith('.xlsx') or target_file.endswith('.csv.xlsx'):
            df = pd.read_excel(target_file, dtype=str)
    except:
        pass
        
    if df.empty:
        try:
            df = pd.read_csv(target_file, dtype=str, encoding='utf-8')
        except:
            try:
                df = pd.read_csv(target_file, dtype=str, encoding='utf-8-sig')
            except Exception as e:
                st.error(f"⚠️ فشلت قراءة الملف: {e}")
                return pd.DataFrame()

    if 'مركز التسجيل والاقتراع' not in df.columns and 'اسم المركز' in df.columns:
        df.rename(columns={'اسم المركز': 'مركز التسجيل والاقتراع'}, inplace=True)
    if 'رمز الناخب' not in df.columns:
        df['رمز الناخب'] = 'غير متوفر'

    cols_to_fill = ['الاسم الاول', 'اسم الاب', 'اسم الجد', 'اسم العائلة']
    for c in cols_to_fill:
        if c not in df.columns: df[c] = ''
        
    df['الاسم الرباعي'] = df['الاسم الاول'].fillna('') + " " + \
                        df['اسم الاب'].fillna('') + " " + \
                        df['اسم الجد'].fillna('') + " " + \
                        df['اسم العائلة'].fillna('')
    df['الاسم الرباعي'] = df['الاسم الرباعي'].str.replace(r'\s+', ' ', regex=True).str.strip()
    
    df['عائلة_موحدة'] = df['اسم العائلة'].apply(clean_family_name)
    df['حالة التصويت'] = 'لم يصوت'
    
    return df

def get_client_data(client_name):
    fname = f"data_{client_name}.csv"
    if os.path.exists(fname):
        try:
            return pd.read_csv(fname, dtype=str, encoding='utf-8-sig')
        except:
            return pd.read_csv(fname, dtype=str)
    else:
        df = process_master_file()
        if not df.empty:
            df.to_csv(fname, index=False, encoding='utf-8-sig')
        return df

def save_client_data(df, client_name):
    df.to_csv(f"data_{client_name}.csv", index=False, encoding='utf-8-sig')

# =========================================================
# 3. إدارة المستخدمين (الصلاحيات)
# =========================================================
def init_users_db():
    if not os.path.exists(USERS_FILE):
        db = {
            "qusai": {"pass": "851998", "role": "super_admin", "client": "المركز الرئيسي", "centers": [], "families": []}
        }
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(db, f, ensure_ascii=False, indent=4)
        return db
    with open(USERS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_users_db(db):
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(db, f, ensure_ascii=False, indent=4)

users_db = init_users_db()

# =========================================================
# 4. شاشة تسجيل الدخول
# =========================================================
if not st.session_state.logged_in:
    st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>🏛️ منصة إدارة الحملات الانتخابية</h1>", unsafe_allow_html=True)
    st.write("")
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        with st.form("login_form"):
            st.subheader("تسجيل الدخول")
            user_input = st.text_input("اسم المستخدم")
            pass_input = st.text_input("كلمة المرور", type="password")
            submitted = st.form_submit_button("دخول آمن", use_container_width=True)
            
            if submitted:
                if user_input in users_db and users_db[user_input]['pass'] == pass_input:
                    info = users_db[user_input]
                    st.session_state.logged_in = True
                    st.session_state.username = user_input
                    st.session_state.role = info['role']
                    st.session_state.client = info['client']
                    st.session_state.centers = info.get('centers', [])
                    st.session_state.families = info.get('families', [])
                    st.rerun()
                else:
                    st.error("⚠️ بيانات الدخول غير صحيحة!")

# =========================================================
# 5. لوحات التحكم (الأنظمة)
# =========================================================
else:
    ROLE = st.session_state.role
    CLIENT = st.session_state.client
    USERNAME = st.session_state.username

    # ---------------------------------------------------------
    # أ) السوبر مدير (الأستاذ قصي)
    # ---------------------------------------------------------
    if ROLE == "super_admin":
        st.title("👑 لوحة تحكم النظام المركزية")
        t1, t2 = st.tabs(["➕ إنشاء قائمة لزبون", "🗑️ إدارة الزبائن"])
        
        with t1:
            st.subheader("إضافة زبون (قائمة انتخابية جديدة)")
            with st.form("new_client"):
                new_list = st.text_input("اسم القائمة (مثال: الوفاء)")
                new_user = st.text_input("يوزر مدير القائمة")
                new_pass = st.text_input("رقم سري لمدير القائمة")
                if st.form_submit_button("تفعيل الزبون"):
                    if new_list and new_user and new_pass:
                        if new_user in users_db:
                            st.error("هذا اليوزر مستخدم من قبل!")
                        else:
                            users_db[new_user] = {"pass": new_pass, "role": "list_admin", "client": new_list}
                            save_users_db(users_db)
                            df = get_client_data(new_list)
                            if not df.empty:
                                st.success(f"تم إنشاء حساب القائمة ({new_list}) بنجاح! سجل خروج وادخل بحساب الزبون لترى الداشبورد.")
                            else:
                                del users_db[new_user]
                                save_users_db(users_db)
                    else:
                        st.warning("أكمل جميع الحقول.")
        
        with t2:
            st.subheader("حذف الزبائن والمناديب")
            client_users = [k for k, v in users_db.items() if v['role'] == 'list_admin']
            if client_users:
                to_delete = st.selectbox("اختر يوزر الزبون المراد حذفه نهائياً:", [""] + client_users)
                if st.button("🚨 تدمير بيانات الزبون", type="primary"):
                    if to_delete:
                        c_name = users_db[to_delete]['client']
                        users_to_del = [k for k, v in users_db.items() if v['client'] == c_name and k != 'qusai']
                        for k in users_to_del: del users_db[k]
                        save_users_db(users_db)
                        if os.path.exists(f"data_{c_name}.csv"): os.remove(f"data_{c_name}.csv")
                        st.success(f"تم حذف الزبون {c_name} وكل بياناته!")
                        st.rerun()
            st.divider()
            st.write("📋 القوائم الحالية:")
            st.json({k: v['client'] for k, v in users_db.items() if v['role'] == 'list_admin'})

        if st.button("🚪 تسجيل خروج"):
            st.session_state.logged_in = False
            st.rerun()

    # ---------------------------------------------------------
    # ب) مدير القائمة (الزبون)
    # ---------------------------------------------------------
    elif ROLE == "list_admin":
        df = get_client_data(CLIENT)
        if df.empty:
            st.error("⚠️ لم يتم جلب البيانات. تواصل مع الدعم الفني (قصي).")
            if st.button("تسجيل خروج"):
                st.session_state.logged_in = False
                st.rerun()
            st.stop()
            
        st.sidebar.title(f"🛡️ حملة: {CLIENT}")
        # تمت إضافة القائمة الجديدة هنا
        menu = st.sidebar.radio("القائمة الرئيسية:", ["🚀 الداشبورد", "🤝 محاكي التحالفات والحسم", "👥 المناديب", "📝 الميدان", "📑 التقارير", "⚙️ الإعدادات", "🚪 خروج"])

        if menu == "🚀 الداشبورد":
            st.title("🚀 لوحة القيادة")
            total = len(df)
            voted = len(df[df['حالة التصويت'] == 'تم التصويت'])
            
            c1, c2, c3 = st.columns(3)
            c1.metric("إجمالي الكتلة", f"{total:,}")
            c2.metric("من صوتوا", f"{voted:,}")
            c3.metric("نسبة الحضور", f"{(voted/total)*100:.1f}%" if total > 0 else "0%")

            col1, col2 = st.columns([2, 1])
            with col1:
                st.subheader("📈 التزام العائلات (أعلى 15)")
                stats = df.groupby('عائلة_موحدة').agg(
                    العدد=('الاسم الرباعي', 'count'),
                    صوتوا=('حالة التصويت', lambda x: (x == 'تم التصويت').sum())
                ).reset_index().sort_values(by='العدد', ascending=False).head(15)
                fig = px.bar(stats, x='عائلة_موحدة', y=['العدد', 'صوتوا'], barmode='group')
                st.plotly_chart(fig, use_container_width=True)
            with col2:
                st.subheader("🎯 موقف التصويت")
                fig2 = px.pie(values=[voted, total-voted], names=['صوتوا', 'لم يصوتوا'], hole=0.5, color_discrete_sequence=['#10B981', '#EF4444'])
                st.plotly_chart(fig2, use_container_width=True)

        # ---------------- القسم الجديد: محاكي التحالفات ---------------- #
        elif menu == "🤝 محاكي التحالفات والحسم":
            st.title("🤝 محاكي التحالفات الاستراتيجية وإحصائيات الحسم")
            st.markdown("استخدم هذه الأداة لبناء تحالفات افتراضية بين العائلات ومعرفة فرص اجتياز العتبة الانتخابية وعدد المقاعد المتوقعة.")
            
            st.subheader("1. بناء التحالف العائلي")
            all_fams = sorted(df['عائلة_موحدة'].unique())
            selected_fams = st.multiselect("اختر العائلات لتشكيل التحالف:", all_fams)
            
            commitment = st.slider("نسبة الالتزام المتوقعة لأصوات هذا التحالف (%)", min_value=10, max_value=100, value=75, step=5) / 100.0
            
            if selected_fams:
                alliance_df = df[df['عائلة_موحدة'].isin(selected_fams)]
                total_alliance_voters = len(alliance_df)
                expected_alliance_votes = int(total_alliance_voters * commitment)
                
                c1, c2, c3 = st.columns(3)
                c1.metric("إجمالي أصوات التحالف (ورقياً)", f"{total_alliance_voters:,}")
                c2.metric("الأصوات المتوقعة (بعد الالتزام)", f"{expected_alliance_votes:,}")
                c3.metric("نسبة التحالف من السجل العام", f"{(total_alliance_voters/len(df))*100:.1f}%")
                
                # رسم بياني لحجم العائلات داخل التحالف
                st.markdown("#### 📊 تركيبة التحالف")
                fam_counts = alliance_df['عائلة_موحدة'].value_counts().reset_index()
                fam_counts.columns = ['العائلة', 'العدد']
                fig_fam = px.pie(fam_counts, names='العائلة', values='العدد', hole=0.4, color_discrete_sequence=px.colors.sequential.Teal)
                st.plotly_chart(fig_fam, use_container_width=True)
                
                st.divider()
                st.subheader("2. إحصائيات الحسم وتوقع المقاعد")
                
                col1, col2 = st.columns(2)
                with col1:
                    total_district_voters = st.number_input("عدد المقترعين الفعلي المتوقع في الدائرة يوم الانتخابات:", min_value=1000, value=8000, step=500)
                with col2:
                    total_seats = st.number_input("عدد مقاعد المجلس البلدي:", min_value=5, value=13, step=2)
                    
                threshold_rate = 0.08 # نسبة الحسم 8% المتعارف عليها
                threshold_votes = int(total_district_voters * threshold_rate)
                seat_cost = int(total_district_voters / total_seats)
                
                st.info(f"🚨 عتبة الحسم (8%): **{threshold_votes} صوت** | 🪑 الوزن الانتخابي للمقعد (تقريباً): **{seat_cost} صوت**")
                
                if expected_alliance_votes >= threshold_votes:
                    seats_won = expected_alliance_votes // seat_cost
                    st.success(f"🎉 **مبروك!** هذا التحالف يعبر نسبة الحسم بسهولة. المتوقع حصده: **{seats_won} مقعد/مقاعد** (كحد أدنى).")
                    
                    remainder = expected_alliance_votes % seat_cost
                    progress_to_next = min(remainder / seat_cost, 1.0)
                    st.progress(progress_to_next, text=f"التقدم نحو مقعد إضافي: نحتاج {seat_cost - remainder} صوت إضافي للحصول على مقعد جديد.")
                else:
                    st.error(f"⚠️ **تنبيه:** التحالف بشكله الحالي لا يعبر نسبة الحسم! يحتاج التحالف إلى {threshold_votes - expected_alliance_votes} صوت إضافي للعبور.")
                    progress_to_threshold = min(expected_alliance_votes / threshold_votes, 1.0)
                    st.progress(progress_to_threshold, text="نسبة الاقتراب من عتبة الحسم.")
            else:
                st.info("👈 يرجى اختيار عائلة واحدة أو أكثر للبدء في المحاكاة.")

        # --------------------------------------------------------------- #

        elif menu == "👥 المناديب":
            st.title("👥 إدارة المناديب وتوزيع المهام")
            all_centers = sorted(df['مركز التسجيل والاقتراع'].dropna().unique())
            all_families = sorted(df['عائلة_موحدة'].dropna().unique())
            
            with st.form("add_del"):
                st.write("إضافة مندوب جديد للميدان")
                d_user = st.text_input("يوزر المندوب")
                d_pass = st.text_input("كلمة مرور المندوب")
                d_centers = st.multiselect("المدارس المسؤل عنها (اختياري)", all_centers)
                d_families = st.multiselect("العائلات المسؤل عنها (اختياري)", all_families)
                
                if st.form_submit_button("اعتماد المندوب"):
                    if d_user and d_pass:
                        if d_user in users_db: st.error("اليوزر موجود!")
                        else:
                            users_db[d_user] = {
                                "pass": d_pass, "role": "delegate", "client": CLIENT,
                                "centers": d_centers, "families": d_families
                            }
                            save_users_db(users_db)
                            st.success("تم الإضافة بنجاح!")
                    else: st.warning("اكتب اليوزر والباسورد.")
            
            st.divider()
            st.write("📋 المناديب المسجلين:")
            del_data = [{"المندوب": k, "المدارس": ", ".join(v.get('centers',[])), "العائلات": ", ".join(v.get('families',[]))} 
                        for k, v in users_db.items() if v.get('role') == 'delegate' and v.get('client') == CLIENT]
            if del_data: st.table(pd.DataFrame(del_data))

        elif menu == "📝 الميدان":
            st.title("📝 تحديث الميدان المركزي")
            col1, col2 = st.columns([3, 1])
            with col1: search = st.text_input("🔍 ابحث برمز الناخب، الاسم، أو العائلة:")
            with col2: unvoted_only = st.checkbox("🚨 إخفاء من صوتوا", value=False)
            
            w_df = df.copy()
            if unvoted_only: w_df = w_df[w_df['حالة التصويت'] == 'لم يصوت']
            if search:
                w_df = w_df[w_df['الاسم الرباعي'].str.contains(search, na=False) | 
                            w_df['عائلة_موحدة'].str.contains(search, na=False) |
                            w_df['رمز الناخب'].str.contains(search, na=False)]
            
            st.write(f"النتائج: {len(w_df)}")
            edited = st.data_editor(
                w_df[['رمز الناخب', 'الاسم الرباعي', 'اسم العائلة', 'مركز التسجيل والاقتراع', 'حالة التصويت']],
                column_config={"حالة التصويت": st.column_config.SelectboxColumn(options=["لم يصوت", "تم التصويت"])},
                use_container_width=True
            )
            if st.button("💾 حفظ البيانات"):
                df.update(edited)
                save_client_data(df, CLIENT)
                st.success("تم الحفظ بنجاح!")

        elif menu == "📑 التقارير":
            st.title("📑 استخراج الكشوفات والتقارير")
            t1, t2 = st.tabs(["📋 تقرير لعائلة محددة", "🎛️ تقرير مجمع"])
            
            with t1:
                sel_fam = st.selectbox("اختر العائلة:", [""] + sorted(df['عائلة_موحدة'].unique()))
                if sel_fam:
                    f_df = df[df['عائلة_موحدة'] == sel_fam]
                    st.write(f"إجمالي: {len(f_df)} | صوتوا: {len(f_df[f_df['حالة التصويت'] == 'تم التصويت'])}")
                    st.dataframe(f_df[['رمز الناخب', 'الاسم الرباعي', 'مركز التسجيل والاقتراع', 'حالة التصويت']], use_container_width=True)
                    buf = BytesIO()
                    f_df.to_excel(buf, index=False)
                    st.download_button("📥 تحميل الكشف", buf.getvalue(), f"Report_{sel_fam}.xlsx")
            
            with t2:
                c1, c2, c3 = st.columns(3)
                with c1: f1 = st.multiselect("العائلات:", sorted(df['عائلة_موحدة'].unique()))
                with c2: f2 = st.multiselect("المدارس:", sorted(df['مركز التسجيل والاقتراع'].unique()))
                with c3: f3 = st.selectbox("الحالة:", ["الكل", "لم يصوت", "تم التصويت"])
                
                rep = df.copy()
                if f1: rep = rep[rep['عائلة_موحدة'].isin(f1)]
                if f2: rep = rep[rep['مركز التسجيل والاقتراع'].isin(f2)]
                if f3 != "الكل": rep = rep[rep['حالة التصويت'] == f3]
                
                st.write(f"العدد: {len(rep)}")
                st.dataframe(rep[['رمز الناخب', 'الاسم الرباعي', 'مركز التسجيل والاقتراع', 'حالة التصويت']], use_container_width=True)
                if not rep.empty:
                    buf2 = BytesIO()
                    rep.to_excel(buf2, index=False)
                    st.download_button("📥 تحميل التقرير", buf2.getvalue(), f"Report_Custom.xlsx")

        elif menu == "⚙️ الإعدادات":
            st.title("⚙️ الإعدادات الخطرة (التصفير)")
            st.warning("هذا الزر يقوم بإرجاع جميع الأصوات إلى 'لم يصوت' استعداداً ليوم الانتخابات.")
            if st.button("🔄 تصفير كافة أصوات الميدان"):
                df['حالة التصويت'] = 'لم يصوت'
                save_client_data(df, CLIENT)
                st.success("تم التصفير بنجاح!")
                st.rerun()

        elif menu == "🚪 خروج":
            st.session_state.logged_in = False
            st.rerun()

    # ---------------------------------------------------------
    # ج) المندوب الميداني
    # ---------------------------------------------------------
    elif ROLE == "delegate":
        df = get_client_data(CLIENT)
        my_centers = st.session_state.centers
        my_families = st.session_state.families
        
        if not my_centers and not my_families:
            st.warning("لم يتم تعيين أي مدارس أو عائلات لك. راجع مدير القائمة.")
            if st.button("خروج"):
                st.session_state.logged_in = False
                st.rerun()
            st.stop()
            
        mask = pd.Series(False, index=df.index)
        if my_centers: mask = mask | df['مركز التسجيل والاقتراع'].isin(my_centers)
        if my_families: mask = mask | df['عائلة_موحدة'].isin(my_families)
            
        my_df = df[mask].copy()
        
        st.sidebar.write(f"👤 المندوب: {USERNAME}")
        if st.sidebar.button("🚪 خروج"):
            st.session_state.logged_in = False
            st.rerun()
            
        st.title("📝 الميدان المخصص لك")
        
        c1, c2 = st.columns([3, 1])
        with c1: search = st.text_input("🔍 ابحث برمز الناخب أو الاسم:")
        with c2: unvoted_only = st.checkbox("🚨 إخفاء من صوتوا")
            
        if unvoted_only: my_df = my_df[my_df['حالة التصويت'] == 'لم يصوت']
        if search:
            my_df = my_df[my_df['الاسم الرباعي'].str.contains(search, na=False) | my_df['رمز الناخب'].str.contains(search, na=False)]
            
        st.write(f"الأسماء: {len(my_df)}")
        edited = st.data_editor(
            my_df[['رمز الناخب', 'الاسم الرباعي', 'مركز التسجيل والاقتراع', 'حالة التصويت']],
            column_config={
                "حالة التصويت": st.column_config.SelectboxColumn(options=["لم يصوت", "تم التصويت"]),
                "رمز الناخب": st.column_config.Column(disabled=True),
                "الاسم الرباعي": st.column_config.Column(disabled=True),
                "مركز التسجيل والاقتراع": st.column_config.Column(disabled=True)
            },
            use_container_width=True
        )
        
        if st.button("💾 حفظ ورفع التحديثات"):
            df.update(edited)
            save_client_data(df, CLIENT)
            st.success("✅ تم الرفع للغرفة المركزية!")
