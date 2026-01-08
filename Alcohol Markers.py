import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# --- 1. 页面配置 ---
st.set_page_config(page_title="酒精笔销量深度看板", layout="wide")
st.title("📊 酒精笔市场趋势监测看板")
st.markdown("---")

# --- 2. 数据处理 ---
@st.cache_data
def load_data():
    file_path = "酒精笔销量数据.xlsx" 
    try:
        df = pd.read_excel(file_path, engine='openpyxl')
        df.columns = [c.strip() for c in df.columns] 
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

# --- 3. 侧边栏 (全局核心筛选) ---
st.sidebar.header("🎛️ 全局核心筛选")
if not df.empty:
    years = sorted(list(set(df['month(month)'].str[:4])))
    selected_years = st.sidebar.multiselect("1. 选择年份", years, default=years)
    
    selected_age = st.sidebar.radio("2. 市场分类 (是否8+)", ["全部", "是", "否"], index=0)
    
    mask = df['month(month)'].str[:4].isin(selected_years)
    if selected_age != "全部":
        mask &= (df['是否8+'] == selected_age)
    
    filtered_df = df[mask].copy()
else:
    st.stop()

# --- 4. 看板布局 ---

# --- 板块一：笔尖类型 ---
st.header("1️⃣ 笔尖类型：销量趋势分析")

# 图表 1：整体分布 (不受局部按钮影响)
st.subheader("📊 笔尖整体销量构成")
tip_pie = px.pie(filtered_df, values='销量', names='笔头类型', hole=0.4)
st.plotly_chart(tip_pie, use_container_width=True)

# 局部按钮 (多选模式)
all_tips = sorted(filtered_df['笔头类型'].unique().tolist())
selected_tips = st.pills("细分笔头查看 (支持多选)：", all_tips, selection_mode="multi", default=all_tips[:3])

# 图表 2：局部联动走势
if selected_tips:
    d_tip = filtered_df[filtered_df['笔头类型'].isin(selected_tips)]
    tip_trend = d_tip.groupby(['时间轴', '笔头类型'])['销量'].sum().reset_index()
    fig_tip = px.line(tip_trend, x='时间轴', y='销量', color='笔头类型', markers=True, 
                      title=f"选定笔头的月度走势")
    st.plotly_chart(fig_tip, use_container_width=True)
else:
    st.info("请在上方选择笔头类型以查看走势。")

st.markdown("---")

# --- 板块二：规格支数 ---
st.header("2️⃣ 规格支数：核心规格分析")
st.info("💡 系统已自动筛选销量前 10 的规格。")

# 图表 1：市场份额变化 (固定显示 Top 10，不受局部按钮影响)
st.subheader("📊 核心规格市场份额推移")
spec_total = filtered_df.groupby('支数')['销量'].sum().sort_values(ascending=False).reset_index()
top_10_specs = spec_total.head(10)['支数'].tolist()
spec_data_all = filtered_df[filtered_df['支数'].isin(top_10_specs)].groupby(['时间轴', '支数'])['销量'].sum().reset_index()

total_monthly_all = spec_data_all.groupby('时间轴')['销量'].transform('sum')
spec_data_all['占比'] = spec_data_all['销量'] / total_monthly_all.replace(0, np.nan)

fig_spec_area = go.Figure()
for cat in sorted(spec_data_all['支数'].unique()):
    df_sub = spec_data_all[spec_data_all['支_数'] == cat]
    fig_spec_area.add_trace(go.Scatter(
        x=df_sub['时间轴'], 
        y=df_sub['占比'], 
        name=f"{cat}支",
        stackgroup='one', 
        fill='tonexty', 
        # 修改点 1: 增加 hoveron，确保悬停时依然能看到点和轴的信息
        hoveron='points+fills', 
        customdata=df_sub['销量'],
        # 修改点 2: 在悬停模板中加入时间轴信息 %{x}
        hovertemplate=(
            "<b>时间: %{x}</b><br>" +
            "规格: %{fullData.name}<br>" +
            "占比: %{y:.1%}<br>" +
            "销量: %{customdata:,.0f}<extra></extra>"
        )
    ))

# 强化 xaxis 设置，确保标签显示并旋转以防重叠
fig_spec_area.update_layout(
    hovermode="x unified",     # 建议使用 unified 模式，一次查看该时间点所有规格
    yaxis_tickformat='.0%', 
    height=500,
    xaxis=dict(
        type='category',       # 强制将时间轴视为类别，确保每个月份都显示
        tickangle=-45,         # 标签倾斜 45 度
        showgrid=True,
        title="时间轴"
    ),
    yaxis=dict(title="市场份额占比")
)

st.plotly_chart(fig_spec_area, use_container_width=True)

# 图表 2：细分销量趋势
if selected_specs:
    selected_specs_int = [int(s) for s in selected_specs]
    display_spec_data = spec_data_all[spec_data_all['支数'].isin(selected_specs_int)]
    fig_spec_line = px.line(display_spec_data, x='时间轴', y='销量', color='支数', markers=True, title="选定规格销量走势")
    st.plotly_chart(fig_spec_line, use_container_width=True)
else:
    st.info("请在上方选择具体规格以对比销量。")

st.markdown("---")

# --- 板块三：价格段 ---
st.header("3️⃣ 价格段深度分析")

# 图表 1：价格构成 (全局锁定)
st.subheader("📊 整体市场价格构成")
fig_pie_price = px.pie(filtered_df, values='销量', names='价格段', hole=0.4)
st.plotly_chart(fig_pie_price, use_container_width=True)

# 局部按钮 (多选模式)
all_prices = sorted(filtered_df['价格段'].unique().tolist())
selected_prices = st.pills("筛选价格区间 (支持多选)：", all_prices, selection_mode="multi")

# 图表 2：细分走势
if selected_prices:
    d_price = filtered_df[filtered_df['价格段'].isin(selected_prices)]
    price_trend = d_price.groupby(['时间轴', '价格段'])['销量'].sum().reset_index()
    fig_price_bar = px.bar(price_trend, x='时间轴', y='销量', color='价格段', barmode='group', title="选定价格段月度对比")
    st.plotly_chart(fig_price_bar, use_container_width=True)
else:
    st.info("请在上方选择价格段以对比走势。")
