import streamlit as st
import pandas as pd
import plotly.express as px

# --- 1. 页面配置 ---
st.set_page_config(page_title="酒精笔深度分析看板", layout="wide")
st.title("📊 酒精笔市场趋势深度看板")
st.markdown("---")

# --- 2. 数据读取与预处理 ---
@st.cache_data
def load_data():
    file_path = "酒精笔销量数据.xlsx" 
    try:
        # 读取数据并自动去除列名空格
        df = pd.read_excel(file_path, engine='openpyxl')
        df.columns = [c.strip() for c in df.columns]
        
        # 核心清洗：确保月份是可排序的 
        # 数据中 month(month) 为 202311 这种格式
        df['month(month)'] = df['month(month)'].astype(str)
        df = df.sort_values('month(month)')
        
        # 处理 8+ 缺失值
        df['是否8+'] = df['是否8+'].fillna('否')
        
        # 统一将月份转换为易读格式 (可选，如 23-11)
        df['时间'] = df['month(month)'].apply(lambda x: f"{x[:4]}-{x[4:]}")
        
        return df[df['目标分类'] == '酒精笔'] if '目标分类' in df.columns else df
    except Exception as e:
        st.error(f"数据处理出错: {e}")
        return pd.DataFrame()

df = load_data()

# --- 3. 侧边栏控制 ---
st.sidebar.header("数据过滤选项")
# 允许用户选择特定的年份进行对比，避免横轴过长
years = sorted(list(set(df['month(month)'].str[:4])))
selected_years = st.sidebar.multiselect("选择分析年份", years, default=years)

# 过滤年份
df = df[df['month(month)'].str[:4].isin(selected_years)]

# --- 4. 深度分析板块 ---

# 板块一：笔尖趋势对比 (分年龄段展示)
st.header("1️⃣ 笔尖类型销量演变趋势对比")
st.info("通过分左右两图展示 8+ 与非 8+ 市场的差异，方便观察时间点和销量的绝对值对比。")

col1, col2 = st.columns(2)

# 8+ 市场数据
data_8plus = df[df['是否8+'] == '是'].groupby(['时间', '笔头类型'])['销量'].sum().reset_index()
# 非 8+ 市场数据
data_non_8plus = df[df['是否8+'] == '否'].groupby(['时间', '笔头类型'])['销量'].sum().reset_index()

with col1:
    st.subheader("年龄段：8+")
    fig1 = px.line(data_8plus, x='时间', y='销量', color='笔头类型', 
                  markers=True, title="8+ 市场笔尖趋势")
    st.plotly_chart(fig1, use_container_width=True)

with col2:
    st.subheader("年龄段：非 8+")
    fig2 = px.line(data_non_8plus, x='时间', y='销量', color='笔头类型', 
                  markers=True, title="非 8+ 市场笔尖趋势")
    st.plotly_chart(fig2, use_container_width=True)

st.markdown("---")

# 板块二：价格段分析 (堆叠对比图)
st.header("2️⃣ 各价格段销量占比与分布")
col3, col4 = st.columns([1, 2])

with col3:
    st.subheader("价格段总体构成")
    fig3 = px.pie(df, values='销量', names='价格段', hole=0.4, title="各价格段总销量占比")
    st.plotly_chart(fig3, use_container_width=True)

with col4:
    st.subheader("价格段随时间变化")
    # 观察不同价格段在不同时间的波动
    price_trend = df.groupby(['时间', '价格段'])['销量'].sum().reset_index()
    fig4 = px.bar(price_trend, x='时间', y='销量', color='价格段', 
                 title="时间轴上的价格段推移", barmode='stack')
    st.plotly_chart(fig4, use_container_width=True)

st.markdown("---")

# 板块三：规格（支数）分析
st.header("3️⃣ 规格支数销量矩阵")
st.info("展示不同规格在不同月份的销量热度。")

# 使用面积图展示支数的消长情况
spec_data = df.groupby(['时间', '支数'])['销量'].sum().reset_index()
fig5 = px.area(spec_data, x='时间', y='销量', color='支数',
              title="不同支数规格的销量市场占有趋势")
st.plotly_chart(fig5, use_container_width=True)

# 增加热力图：快速看出哪个时间点哪个规格最火
st.subheader("各规格月度销量热力矩阵")
heatmap_data = df.pivot_table(index='支数', columns='时间', values='销量', aggfunc='sum').fillna(0)
fig6 = px.imshow(heatmap_data, labels=dict(x="月份", y="支数规格", color="销量"),
                aspect="auto", color_continuous_scale='Viridis')
st.plotly_chart(fig6, use_container_width=True)
