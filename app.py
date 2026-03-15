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
st.set_page_config(page_title="نظام الأستاذ قصي لإدارة الحملات", layout="wide")

if 'auth' not in st.session_state:
    st.session_state.update({'auth': False, 'user': '', 'client': '', 'role': '', 'centers': [], 'families': []})

USERS_FILE = 'clients_users.json'
MASTER_FILE = 'حلحول (1).xlsx - حَلْحُول.csv' 

# =========================================================
# 2. خوارزمية "قصي" لتنظيف العائلات وبناء البيانات
# =========================================================
def normalize_family(text):
    """توحيد العائلات لغايات الإحصاء"""
    if not isinstance(text, str) or not text.strip(): return "غير محدد"
    text = text.strip()
    text = re.sub(r'[أإآ]', 'ا', text)
    text = re.sub(r'ة\b', 'ه', text)
    if text.startswith('ال'): text = text[2:]
    return text.strip()

def process_data(df):
    """بناء قاعدة البيانات من الأعمدة المنفصلة وتضمين رمز الناخب"""
    df = df.copy()
    
    if 'مركز التسجيل والاقتراع' not in df.columns and 'اسم المركز' in df.columns:
        df.rename(columns={'اسم المركز': 'مركز التسجيل والاقتراع'}, inplace=True)
    
    if 'رمز الناخب' not in df.columns:
        df['رمز الناخب'] = 'غير متوفر'

    df['الاسم الرباعي'] = df['الاسم الاول'].fillna('') + " " + \
                        df['اسم الاب'].fillna('') + " " + \
                        df['اسم الجد'].fillna('') + " " + \
                        df['اسم العائلة'].fillna('')
    df['الاسم الرباعي'] = df['الاسم الرباعي'].str.replace(r'\s+', ' ', regex=True).str.strip()
    
    df['عائلة_موحدة'] = df['اسم العائلة'].apply(normalize_family)
    
    if 'حالة التصويت' not in df.columns:
        df['حالة التصويت'] = 'لم يصوت'
    return df

# =========================================================
# 3. نظام الصلاحيات والمستخدمين
# =========================================================
def load_users():
    if not os.path.exists(USERS_FILE):
        default = {"qusai": {"pass": "851998", "role": "super_admin", "client_name": "المركز الرئيسي"}}
        with open(USERS_FILE, 'w', encoding='utf-8') as f: json.dump(default, f, ensure_ascii=False, indent=4)
        return default
    with open(USERS_FILE, 'r', encoding='utf-8') as f: return json.load(f)

def save_users(u_dict):
    with open(USERS_FILE, 'w', encoding='utf-8') as f: json.dump(u_dict, f, ensure_ascii=False, indent=4)

def load_client_data(client_name):
    fname = f"data_{client_name}.csv"
    if os.path.exists(fname): return pd.read_csv(fname, dtype=str)
    
    if os.path.exists(MASTER_FILE):
        try:
            raw = pd.read_csv(MASTER_FILE, dtype=str)
        except:
            raw = pd.read_excel(MASTER_FILE, dtype=str)
        
        df = process_data(raw)
        df.to_csv(fname, index=False, encoding='utf-8-sig')
        return df
    return pd.DataFrame()

def save_client_data(df, client_name):
    df.to_csv(f"data_{client_name}.csv", index=False, encoding='utf-8-sig')

# =========================================================
# 4. واجهة المستخدم (GUI)
# =========================================================
users_db = load_users()

if not st.session_state.auth:
    st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>🏛️ نظام الأستاذ قصي الانتخابي الشامل</h1>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1, 1])
    with c2:
        st.markdown("### تسجيل الدخول")
        u = st.text_input("اسم المستخدم")
        p = st.text_input("كلمة المرور", type="password")
        if st.button("دخول آمن", use_container_width=True):
            if u in users_db and users_db[u]['pass'] == p:
                user_info = users_db[u]
                st.session_state.update({
                    'auth': True, 'user': u, 'role': user_info['role'], 
                    'client': user_info['client_name'],
                    'centers': user_info.get('centers', []),
                    'families': user_info.get('families', [])
                })
                st.rerun()
            else: st.error("⚠️ بيانات الدخول غير صحيحة")

else:
    ROLE = st.session_state.role
    CLIENT = st.session_state.client
    
    # ---------------------------------------------------------
    # 1. شاشة السوبر مدير
    # ---------------------------------------------------------
    if ROLE == "super_admin":
        st.title("👑 لوحة تحكم النظام (الأستاذ قصي)")
        
        tab1, tab2 = st.tabs(["➕ إضافة قائمة جديدة", "🗑️ إدارة وحذف القوائم"])
        
        with tab1:
            with st.form("add_list"):
                st.subheader("إنشاء حساب قائمة انتخابية (زبون جديد)")
                list_name = st.text_input("اسم القائمة (مثال: قائمة الوفاء)")
                u_name = st.text_input("اسم مستخدم مدير القائمة")
                u_pass = st.text_input("كلمة المرور لمدير القائمة")
                
                if st.form_submit_button("اعتماد وإنشاء"):
                    if list_name and u_name and u_pass:
                        if u_name in users_db: st.error("اسم المستخدم موجود مسبقاً!")
                        else:
                            users_db[u_name] = {"pass": u_pass, "role": "list_admin", "client_name": list_name}
                            save_users(users_db)
                            load_client_data(list_name)
                            st.success(f"تم إنشاء حساب ({list_name}) بنجاح!")
                    else: st.warning("يرجى تعبئة كافة الحقول.")
        
        with tab2:
            st.subheader("إلغاء تفعيل وحذف زبون (في حال عدم السداد)")
            clients_to_delete = [k for k, v in users_db.items() if v['role'] == 'list_admin']
            
            if clients_to_delete:
                del_user = st.selectbox("اختر اسم المستخدم للزبون المراد حذفه:", [""] + clients_to_delete)
                if st.button("🚨 حذف نهائي وتدمير البيانات", type="primary"):
                    if del_user:
                        client_to_remove = users_db[del_user]['client_name']
                        users_to_del = [k for k, v in users_db.items() if v['client_name'] == client_to_remove and k != 'qusai']
                        for k in users_to_del: del users_db[k]
                        save_users(users_db)
                        
                        if os.path.exists(f"data_{client_to_remove}.csv"):
                            os.remove(f"data_{client_to_remove}.csv")
                            
                        st.success(f"تم حذف الزبون ({client_to_remove}) وتدمير بياناته بالكامل!")
                        st.rerun()
            else:
                st.info("لا يوجد زبائن حالياً.")
                
            st.divider()
            st.write("📋 القوائم المسجلة حالياً بالنظام:")
            lists_data = [{"المستخدم": k, "القائمة": v['client_name']} for k, v in users_db.items() if v['role'] == 'list_admin']
            if lists_data: st.table(pd.DataFrame(lists_data))

        if st.button("🚪 تسجيل خروج"):
            st.session_state.auth = False
            st.rerun()

    # ---------------------------------------------------------
    # 2. شاشة مدير القائمة
    # ---------------------------------------------------------
    elif ROLE == "list_admin":
        df = load_client_data(CLIENT)
        if df.empty:
            st.error("لا يوجد بيانات. يرجى التأكد من الملف الرئيسي.")
            st.stop()
            
        st.sidebar.title(f"🛡️ قائمة: {CLIENT}")
        menu = st.sidebar.radio("القائمة:", [
            "🚀 الداشبورد", 
            "👥 المناديب والمشرفين", 
            "📝 الميدان (ساعات الحسم)", 
            "📑 التقارير وطباعة الكشوفات",
            "⚙️ إعدادات (تصفير النظام)",
            "🚪 خروج"
        ])

        if menu == "🚀 الداشبورد":
            st.title("🚀 لوحة القيادة المركزية")
            total = len(df)
            voted = len(df[df['حالة التصويت'] == 'تم التصويت'])
            
            c1, c2, c3 = st.columns(3)
            c1.metric("الكتلة الناخبة (الإجمالي)", f"{total:,}")
            c2.metric("من صوتوا", f"{voted:,}")
            c3.metric("نسبة التصويت الإجمالية", f"{(voted/total)*100:.1f}%" if total > 0 else "0%")

            col1, col2 = st.columns([2, 1])
            with col1:
                st.subheader("📈 أعلى العائلات التزاماً")
                stats = df.groupby('عائلة_موحدة').agg(
                    العدد=('الاسم الرباعي', 'count'),
                    صوتوا=('حالة التصويت', lambda x: (x == 'تم التصويت').sum())
                ).reset_index().sort_values(by='العدد', ascending=False).head(15)
                fig = px.bar(stats, x='عائلة_موحدة', y=['العدد', 'صوتوا'], barmode='group')
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                st.subheader("🎯 الموقف العام")
                fig2 = px.pie(values=[voted, total-voted], names=['صوتوا', 'لم يصوتوا'], hole=0.5, color_discrete_sequence=['#10B981', '#EF4444'])
                st.plotly_chart(fig2, use_container_width=True)

        elif menu == "👥 المناديب والمشرفين":
            st.title("👥 توزيع المهام الميدانية")
            
            all_centers = sorted(df['مركز التسجيل والاقتراع'].dropna().unique())
            all_families = sorted(df['عائلة_موحدة'].dropna().unique())
            
            with st.form("add_delegate"):
                d_user = st.text_input("اسم مستخدم المندوب")
                d_pass = st.text_input("كلمة مرور المندوب")
                d_centers = st.multiselect("اختر المدارس المخصصة (اختياري):", all_centers)
                d_families = st.multiselect("اختر العائلات المخصصة (اختياري):", all_families)
                
                if st.form_submit_button("إضافة المندوب"):
                    if d_user and d_pass:
                        if d_user in users_db: st.error("المستخدم موجود مسبقاً!")
                        else:
                            users_db[d_user] = {
                                "pass": d_pass, "role": "delegate", "client_name": CLIENT,
                                "centers": d_centers, "families": d_families
                            }
                            save_users(users_db)
                            st.success(f"تم إنشاء حساب المندوب ({d_user}) بنجاح!")
                    else: st.warning("أدخل اليوزر والباسورد.")
            
            st.divider()
            st.subheader("📋 المناديب المسجلين حالياً")
            d_data = [{"المندوب": k, "المدارس": ", ".join(v.get('centers',[])), "العائلات": ", ".join(v.get('families',[]))} 
                      for k, v in users_db.items() if v['role'] == 'delegate' and v['client_name'] == CLIENT]
            if d_data: st.table(pd.DataFrame(d_data))

        elif menu == "📝 الميدان (ساعات الحسم)":
            st.title("📝 تحديث الميدان والبحث السريع")
            
            col1, col2 = st.columns([3, 1])
            with col1:
                search = st.text_input("🔍 ابحث برمز الناخب، الاسم، أو العائلة:")
            with col2:
                unvoted_only = st.checkbox("🚨 إخفاء من صوتوا (لساعات الحسم)", value=False)
                
            work_df = df.copy()
            if unvoted_only:
                work_df = work_df[work_df['حالة التصويت'] == 'لم يصوت']
                
            if search:
                work_df = work_df[work_df['الاسم الرباعي'].str.contains(search, na=False) | 
                                 work_df['عائلة_موحدة'].str.contains(search, na=False) |
                                 work_df['رمز الناخب'].str.contains(search, na=False)]
                
            st.write(f"عدد النتائج: {len(work_df)}")
            
            edited = st.data_editor(
                work_df[['رمز الناخب', 'الاسم الرباعي', 'اسم العائلة', 'مركز التسجيل والاقتراع', 'حالة التصويت']],
                column_config={"حالة التصويت": st.column_config.SelectboxColumn(options=["لم يصوت", "تم التصويت"])},
                use_container_width=True
            )
            
            if st.button("💾 حفظ البيانات"):
                df.update(edited)
                save_client_data(df, CLIENT)
                st.success("تم الحفظ بنجاح!")

        # -------------------------------------------------------------
        # التحديث الجديد: قسم التقارير المفصل والمقسم إلى تابين
        # -------------------------------------------------------------
        elif menu == "📑 التقارير وطباعة الكشوفات":
            st.title("📑 استخراج وطباعة الكشوفات")
            
            tab_single, tab_multi = st.tabs(["📋 تقرير عائلة مخصص", "🎛️ تقرير مجمع (فلاتر متعددة)"])
            
            # --- التاب الأول: تقرير العائلة المخصص ---
            with tab_single:
                st.subheader("إصدار كشف سريع مخصص لعائلة واحدة")
                all_unified_families = sorted(df['عائلة_موحدة'].unique())
                selected_single_fam = st.selectbox("اختر العائلة المطلوبة:", [""] + all_unified_families)
                
                if selected_single_fam:
                    fam_df = df[df['عائلة_موحدة'] == selected_single_fam]
                    voted_count = len(fam_df[fam_df['حالة التصويت'] == 'تم التصويت'])
                    
                    st.info(f"📊 **إحصائيات عائلة {selected_single_fam}:** إجمالي الناخبين ({len(fam_df)}) | صوّت ({voted_count}) | متبقي ({len(fam_df) - voted_count})")
                    
                    st.dataframe(fam_df[['رمز الناخب', 'الاسم الرباعي', 'اسم العائلة', 'مركز التسجيل والاقتراع', 'حالة التصويت']], use_container_width=True)
                    
                    # زر تحميل الكشف باسم العائلة
                    buf_single = BytesIO()
                    fam_df.to_excel(buf_single, index=False)
                    st.download_button("📥 تحميل كشف العائلة (Excel)", buf_single.getvalue(), f"Report_{selected_single_fam}.xlsx")

            # --- التاب الثاني: التقرير المجمع ---
            with tab_multi:
                st.subheader("إصدار كشوفات مجمعة للمدارس أو العائلات")
                col1, col2, col3 = st.columns(3)
                with col1:
                    f_fam = st.multiselect("تصفية بأسماء العائلات:", sorted(df['عائلة_موحدة'].unique()))
                with col2:
                    f_cen = st.multiselect("تصفية بأسماء المدارس:", sorted(df['مركز التسجيل والاقتراع'].unique()))
                with col3:
                    f_stat = st.selectbox("حالة التصويت:", ["الكل", "لم يصوت", "تم التصويت"])
                    
                rep_df = df.copy()
                if f_fam: rep_df = rep_df[rep_df['عائلة_موحدة'].isin(f_fam)]
                if f_cen: rep_df = rep_df[rep_df['مركز التسجيل والاقتراع'].isin(f_cen)]
                if f_stat != "الكل": rep_df = rep_df[rep_df['حالة التصويت'] == f_stat]
                
                st.write(f"📊 إجمالي الأسماء في هذا الكشف: **{len(rep_df)}** ناخب")
                st.dataframe(rep_df[['رمز الناخب', 'الاسم الرباعي', 'اسم العائلة', 'مركز التسجيل والاقتراع', 'حالة التصويت']], use_container_width=True)
                
                if not rep_df.empty:
                    buf_multi = BytesIO()
                    rep_df.to_excel(buf_multi, index=False)
                    st.download_button("📥 تحميل التقرير المجمع (Excel)", buf_multi.getvalue(), f"Report_{CLIENT}_Custom.xlsx")

        elif menu == "⚙️ إعدادات (تصفير النظام)":
            st.title("⚙️ الإعدادات الخطرة")
            st.warning("⚠️ تحذير: هذا الزر يقوم بمسح كافة عمليات التصويت التجريبية وإعادتها إلى الصفر. يستخدم فقط في ليلة الانتخابات لبدء يوم جديد بصفحة بيضاء.")
            
            if st.button("🔄 تصفير الميدان بالكامل (مسح الأصوات)"):
                df['حالة التصويت'] = 'لم يصوت'
                save_client_data(df, CLIENT)
                st.success("✅ تم تصفير جميع الأصوات! النظام جاهز ليوم الانتخابات الحقيقي.")
                st.rerun()

        elif menu == "🚪 خروج":
            st.session_state.auth = False
            st.rerun()

    # ---------------------------------------------------------
    # 3. شاشة المندوب الميداني
    # ---------------------------------------------------------
    elif ROLE == "delegate":
        df = load_client_data(CLIENT)
        assigned_centers = st.session_state.centers
        assigned_families = st.session_state.families
        
        if not assigned_centers and not assigned_families:
            st.warning("لم يتم تعيين أي مدارس أو عائلات لك. يرجى مراجعة مدير القائمة.")
            if st.button("تسجيل خروج"):
                st.session_state.auth = False
                st.rerun()
            st.stop()
            
        mask = pd.Series(False, index=df.index)
        if assigned_centers: mask = mask | df['مركز التسجيل والاقتراع'].isin(assigned_centers)
        if assigned_families: mask = mask | df['عائلة_موحدة'].isin(assigned_families)
            
        delegate_df = df[mask].copy()
        
        st.sidebar.title("📍 ميدان المندوب")
        st.sidebar.write(f"المستخدم: **{st.session_state.user}**")
        if st.sidebar.button("🚪 تسجيل خروج"):
            st.session_state.auth = False
            st.rerun()
            
        st.title(f"📝 قائمة الناخبين المخصصة لك")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            search = st.text_input("🔍 ابحث برمز الناخب أو الاسم:")
        with col2:
            unvoted_only = st.checkbox("🚨 إخفاء من صوتوا", value=False)
            
        if unvoted_only:
            delegate_df = delegate_df[delegate_df['حالة التصويت'] == 'لم يصوت']
            
        if search:
            delegate_df = delegate_df[delegate_df['الاسم الرباعي'].str.contains(search, na=False) | 
                                      delegate_df['رمز الناخب'].str.contains(search, na=False)]
            
        st.write(f"الأسماء المعروضة: {len(delegate_df)}")
        
        edited = st.data_editor(
            delegate_df[['رمز الناخب', 'الاسم الرباعي', 'مركز التسجيل والاقتراع', 'حالة التصويت']],
            column_config={
                "حالة التصويت": st.column_config.SelectboxColumn(options=["لم يصوت", "تم التصويت"]),
                "رمز الناخب": st.column_config.Column(disabled=True),
                "الاسم الرباعي": st.column_config.Column(disabled=True),
                "مركز التسجيل والاقتراع": st.column_config.Column(disabled=True)
            },
            use_container_width=True
        )
        
        if st.button("💾 حفظ التحديثات للغرفة المركزية"):
            df.update(edited)
            save_client_data(df, CLIENT)
            st.success("✅ تم رفع البيانات للمدير بنجاح!")
