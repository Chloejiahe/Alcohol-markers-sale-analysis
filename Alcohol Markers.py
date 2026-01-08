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

# --- 板块二：规格支数分析 (分行全宽展示版) ---
st.header("2️⃣ 规格支数：核心规格增长分析")
st.info("💡 系统已自动筛选销量前 10 的规格。现已调整为分行展示，方便您仔细观察每种规格的起伏。")

# 1. 聚合并获取前 10 名
spec_total = filtered_df.groupby('支数')['销量'].sum().sort_values(ascending=False).reset_index()
top_10_specs = spec_total.head(10)['支数'].tolist()
spec_data = filtered_df[filtered_df['支_num' if '支_num' in filtered_df.columns else '支数'].isin(top_10_specs)].groupby(['时间轴', '支数'])['销量'].sum().reset_index()

# 第一行：全宽展示【独立趋势图】
st.subheader("📈 各核心规格独立销量趋势 (分图查看)")
fig_spec_line = px.line(
    spec_data, 
    x='时间轴', 
    y='销量', 
    color='支数', 
    facet_col='支数', 
    facet_col_wrap=2,  # 改为每行只放2个图，让图表变大
    height=800,        # 增加整体高度
    title="各规格月度销量波动"
)
# 优化子图标题：只显示数字（支数），不显示 "支数="
fig_spec_line.for_each_annotation(lambda a: a.update(text=f"规格：{a.text.split('=')[-1]} 支"))
# 隐藏右侧重复的图例，因为子图标题已经标明了
fig_spec_line.update_layout(showlegend=False)
st.plotly_chart(fig_spec_line, use_container_width=True)

st.markdown("---") # 逻辑分割线

# 第二行：全宽展示【市场份额占比图】
st.subheader("📊 核心规格市场份额变化 (各规格间的竞争关系)")
fig_spec_area = px.area(
    spec_data, 
    x='时间轴', 
    y='销量', 
    color='支数', 
    groupnorm='percent', 
    height=500,
    title="100% 堆叠面积图：观察大规格是否在蚕食小规格份额"
)
fig_spec_area.update_layout(xaxis_tickangle=-45)
st.plotly_chart(fig_spec_area, use_container_width=True)

st.markdown("---")

# --- 板块三：价格段分析 (分行展示优化版) ---
st.header("3️⃣ 价格段深度分析")

# 第一行：展示占比饼图
st.subheader("整体市场价格构成 (所选范围内)")
fig_pie = px.pie(
    filtered_df, 
    values='销量', 
    names='价格段', 
    hole=0.4,
    color_discrete_sequence=px.colors.qualitative.Pastel # 使用柔和配色
)
fig_pie.update_traces(textinfo='percent+label', pull=[0.05]*len(filtered_df['价格段'].unique())) 
st.plotly_chart(fig_pie, use_container_width=True)

st.markdown("---") # 分割线

# 第二行：展示月度走势条形图
st.subheader("月度价格走势推移")
price_data = filtered_df.groupby(['时间轴', '价格段'])['销量'].sum().reset_index()
fig_price = px.bar(
    price_data, 
    x='时间轴', 
    y='销量', 
    color='价格段', 
    title="不同价格段的销量波动 (横向拉长更易观察趋势)",
    barmode='group', # 改为并列条形图，更容易对比每个月谁最高
    height=500
)
# 优化横轴显示
fig_price.update_layout(xaxis_tickangle=-45)
st.plotly_chart(fig_price, use_container_width=True)
