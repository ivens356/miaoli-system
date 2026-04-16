import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
from datetime import datetime

# 1. 初始化資料庫
def init_db():
    conn = sqlite3.connect('service_data.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS daily_service_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            service_date TEXT, roles TEXT, categories TEXT, service_count INTEGER,
            content TEXT, personnel TEXT, investment_amt REAL, loan_amt REAL,
            telemarketing_count INTEGER, attendees INTEGER
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# 2. 設定網頁排版
st.set_page_config(page_title="工作報表管理系統", layout="wide")
st.title("📊 工策會與榮指員 - 服務統計與管理系統")

# 建立分頁
tab1, tab2, tab3 = st.tabs(["📝 每日線上回報", "📈 年度/月度儀表板", "⚙️ 資料後台管理"])

# --- 分頁 1：每日線上回報表單 ---
with tab1:
    with st.form("service_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            service_date = st.date_input("1. 服務日期 (必填)")
            roles = st.multiselect("2. 角色選擇 (必填)", ["工策會中心", "榮指員"])
            categories = st.multiselect("3. 服務類別 (必填)", [
                "辦理講座研討會(場)", "企業訪視(家)", "投資協助(家)", "輔導轉介(家)", 
                "專家診斷(家)", "提供諮詢(家)", "協調聯繫(家/通)", "跨業交流會(場)", 
                "提供資訊(件)", "企業服務志工(班)", "其他交辦事項(件)"
            ])
            service_count = st.number_input("4. 服務-家/班數 (必填)", min_value=0, step=1)
            content = st.text_area("5. 服務內容 (必填)")
            
        with col2:
            personnel = st.text_input("6. 服務人員")
            investment_amt = st.number_input("7. 投資金額(萬元)", min_value=0.0)
            loan_amt = st.number_input("8. 青創及企業貸款金額(萬元)", min_value=0.0)
            tele_count = st.number_input("9. 電訪企業(家)", min_value=0, step=1)
            attendees = st.number_input("10. 參加活動人數(人)", min_value=0, step=1)
            
        submitted = st.form_submit_button("送出報表")
        
        if submitted:
            if not roles or not categories or not content:
                st.error("請確保『角色』、『類別』與『服務內容』皆已填寫！")
            else:
                conn = sqlite3.connect('service_data.db')
                c = conn.cursor()
                c.execute('''
                    INSERT INTO daily_service_logs 
                    (service_date, roles, categories, service_count, content, personnel, investment_amt, loan_amt, telemarketing_count, attendees)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (str(service_date), ",".join(roles), ",".join(categories), service_count, 
                      content, personnel, investment_amt, loan_amt, tele_count, attendees))
                conn.commit()
                conn.close()
                st.success("✅ 資料新增成功！")

# --- 分頁 2：儀表板 (分裂統計邏輯範例) ---
with tab2:
    st.subheader("視覺化服務統計")
    
    conn = sqlite3.connect('service_data.db')
    df = pd.read_sql_query("SELECT * FROM daily_service_logs", conn)
    conn.close()
    
    if not df.empty:
        # 自動抓取日期，拆解為年、月、日
        df['service_date'] = pd.to_datetime(df['service_date'])
        df['Year'] = df['service_date'].dt.year
        df['Month'] = df['service_date'].dt.strftime('%Y-%m') # 格式：2026-04
        
        # 處理複選欄位 (Split & Explode 邏輯)
        # 把以逗號分隔的字串拆成陣列，然後展開，這樣一筆 "工策會,榮指員" 的資料就會變成兩筆，方便獨立統計
        df_roles_expanded = df.assign(roles=df['roles'].str.split(',')).explode('roles')
        df_cat_expanded = df_roles_expanded.assign(categories=df_roles_expanded['categories'].str.split(',')).explode('categories')

        colA, colB = st.columns(2)
        
        with colA:
            st.markdown("#### 工策會中心 vs 榮指員 (每月服務總數)")
            # 群組化統計
            monthly_trend = df_roles_expanded.groupby(['Month', 'roles'])['service_count'].sum().reset_index()
            fig1 = px.line(monthly_trend, x='Month', y='service_count', color='roles', markers=True, template='plotly_white')
            st.plotly_chart(fig1, use_container_width=True)
            
        with colB:
            st.markdown("#### 各服務類別統計 (案件數柱狀圖)")
            cat_stats = df_cat_expanded.groupby('categories')['service_count'].sum().reset_index()
            # 排序讓圖表更美觀
            cat_stats = cat_stats.sort_values(by='service_count', ascending=True)
            fig2 = px.bar(cat_stats, x='service_count', y='categories', orientation='h', color='categories', template='plotly_white')
            fig2.update_layout(showlegend=False)
            st.plotly_chart(fig2, use_container_width=True)
            
    else:
        st.info("目前尚無資料可供分析，請先輸入資料。")

# --- 分頁 3：資料後台管理 (增刪改查) ---
with tab3:
    st.subheader("資料維護與下載")
    if not df.empty:
        # 使用 Streamlit 內建的資料編輯器，允許直接在畫面上修改或刪除
        edited_df = st.data_editor(df, num_rows="dynamic", key="data_editor")
        
        # 提供 CSV 下載
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="下載完整資料 (CSV)",
            data=csv,
            file_name=f"工作統計報表_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
        )