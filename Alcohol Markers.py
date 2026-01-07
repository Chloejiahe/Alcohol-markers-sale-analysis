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

# --- 板块二：规格支数分析 (修复 ValueError 版本) ---
st.header("2️⃣ 规格支数：哪些规格在增长？")
st.info("💡 系统已自动为您筛选销量前 10 的核心规格进行分析，避免由于规格过多导致图表混乱。")

# 1. 聚合数据
spec_total = filtered_df.groupby('支数')['销量'].sum().sort_values(ascending=False).reset_index()

# 2. 筛选出销量前 10 的规格名
top_10_specs = spec_total.head(10)['支数'].tolist()

# 3. 过滤原始数据，仅保留这前 10 名
spec_data = filtered_df[filtered_df['支数'].isin(top_10_specs)].groupby(['时间轴', '支数'])['销量'].sum().reset_index()

col3, col4 = st.columns(2)

with col3:
    # 限制每行显示 3 个图，并减少垂直间距
    fig_spec_line = px.line(
        spec_data, 
        x='时间轴', 
        y='销量', 
        color='支数', 
        facet_col='支数', 
        facet_col_wrap=3, # 增加每行数量，减少总行数，防止报错
        title="热门规格独立销量趋势",
        height=600 # 增加总高度
    )
    # 自动调整子图标题，防止重叠
    fig_spec_line.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
    st.plotly_chart(fig_spec_line, use_container_width=True)

with col4:
    # 百分比堆叠图，看这些热门规格之间的竞争关系
    fig_spec_area = px.area(
        spec_data, 
        x='时间轴', 
        y='销量', 
        color='支数', 
        groupnorm='percent', 
        title="热门规格市场份额变化 (100%堆叠)"
    )
    st.plotly_chart(fig_spec_area, use_container_width=True)

# 板块三：价格段与销量
st.header("3️⃣ 价格段月度走势")
price_data = filtered_df.groupby(['时间轴', '价格段'])['销量'].sum().reset_index()
fig_price = px.bar(price_data, x='时间轴', y='销量', color='价格段', title="价格段销售结构推移")
st.plotly_chart(fig_price, use_container_width=True)
