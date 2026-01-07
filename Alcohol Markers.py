import streamlit as st
import pandas as pd
import plotly.express as px

# --- 1. 页面配置 ---
st.set_page_config(page_title="酒精笔销量深度看板", layout="wide")
st.title("📊 酒精笔市场趋势监测看板 (优化版)")
st.markdown("---")

# --- 2. 数据处理 ---
@st.cache_data
def load_data():
    file_path = "酒精笔销量数据.xlsx" 
    try:
        df = pd.read_excel(file_path, engine='openpyxl')
        df.columns = [c.strip() for c in df.columns] # 去空格
        
        # 强制排序时间轴
        df['month(month)'] = df['month(month)'].astype(str)
        df = df.sort_values('month(month)')
        df['时间轴'] = df['month(month)'].apply(lambda x: f"{x[:4]}-{x[4:]}")
        
        df['是否8+'] = df['是否8+'].fillna('否')
        if '目标分类' in df.columns:
            df = df[df['目标分类'] == '酒精笔']
        return df
    except Exception as e:
        st.error(f"数据加载出错: {e}")
        return pd.DataFrame()

df = load_data()

# --- 3. 增强版侧边栏 ---
st.sidebar.header("🎛️ 全局筛选")
years = sorted(list(set(df['month(month)'].str[:4])))
selected_years = st.sidebar.multiselect("1. 选择年份", years, default=years)

# 核心修改：筛选器增加“全部”逻辑
age_options = ["全部", "是", "否"]
selected_age = st.sidebar.selectbox("2. 受众群体 (是否8+)", age_options, index=0)

# 执行过滤
filtered_df = df[df['month(month)'].str[:4].isin(selected_years)]
if selected_age != "全部":
    filtered_df = filtered_df[filtered_df['是否8+'] == selected_age]

# --- 4. 看板布局 ---

# 板块一：笔尖类型趋势 (分栏对比)
st.header("1️⃣ 笔尖类型：不同市场销量起伏对比")
if selected_age == "全部":
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("8+ 市场")
        d1 = filtered_df[filtered_df['是否8+'] == '是'].groupby(['时间轴', '笔头类型'])['销量'].sum().reset_index()
        st.plotly_chart(px.line(d1, x='时间轴', y='销量', color='笔头类型', markers=True), use_container_width=True)
    with col2:
        st.subheader("非 8+ 市场")
        d2 = filtered_df[filtered_df['是否8+'] == '否'].groupby(['时间轴', '笔头类型'])['销量'].sum().reset_index()
        st.plotly_chart(px.line(d2, x='时间轴', y='销量', color='笔头类型', markers=True), use_container_width=True)
else:
    d3 = filtered_df.groupby(['时间轴', '笔头类型'])['销量'].sum().reset_index()
    st.plotly_chart(px.line(d3, x='时间轴', y='销量', color='笔头类型', markers=True), use_container_width=True)

st.markdown("---")

# 板块二：支数分析 (替换热度矩阵)
st.header("2️⃣ 规格支数：哪些规格在增长？")
st.write("左图看绝对销量波动，右图看各规格的市场占比份额（是否由于大规格取代了小规格）。")

# 准备数据
spec_data = filtered_df.groupby(['时间轴', '支数'])['销量'].sum().reset_index()

col3, col4 = st.columns(2)

with col3:
    # 使用分面折线图，把不同支数分开，避免线条交织
    fig_spec_line = px.line(spec_data, x='时间轴', y='销量', color='支数', 
                            facet_col='支数', facet_col_wrap=2, # 每行显示两个小图
                            title="各规格销量独立趋势 (分图查看)")
    st.plotly_chart(fig_spec_line, use_container_width=True)

with col4:
    # 百分比堆叠面积图，看份额变化
    fig_spec_area = px.area(spec_data, x='时间轴', y='销量', color='支数', 
                            groupnorm='percent', title="各规格市场份额占比变化 (100%堆叠)")
    st.plotly_chart(fig_spec_area, use_container_width=True)

st.markdown("---")

# 板块三：价格段与销量
st.header("3️⃣ 价格段月度走势")
price_data = filtered_df.groupby(['时间轴', '价格段'])['销量'].sum().reset_index()
fig_price = px.bar(price_data, x='时间轴', y='销量', color='价格段', title="价格段销售结构推移")
st.plotly_chart(fig_price, use_container_width=True)
