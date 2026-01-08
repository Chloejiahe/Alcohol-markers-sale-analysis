import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# --- 1. 页面配置 ---
st.set_page_config(page_title="酒精笔销量深度看板", layout="wide")
st.title("📊 酒精笔市场趋势监测看板 (全局同步版)")
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

# --- 3. 侧边栏 (这里是你要的大型交互区) ---
st.sidebar.header("🎛️ 全局核心筛选")
if not df.empty:
    # 3.1 时间筛选
    years = sorted(list(set(df['month(month)'].str[:4])))
    selected_years = st.sidebar.multiselect("1. 选择年份", years, default=years)
    
    # 3.2 市场分类筛选 (从板块一移动到这里)
    # 使用 radio 或 selectbox 都可以，这里用 radio 更直观
    selected_age = st.sidebar.radio("2. 市场分类 (是否8+)", ["全部", "是", "否"], index=0, help="切换 8+ 受众市场或非 8+ 市场")
    
    # 执行全局过滤
    mask = df['month(month)'].str[:4].isin(selected_years)
    if selected_age != "全部":
        mask &= (df['是否8+'] == selected_age)
    
    filtered_df = df[mask].copy()
else:
    st.stop()

# --- 4. 看板布局 ---

# --- 板块一：笔尖类型 ---
st.header("1️⃣ 笔尖类型：销量趋势分析")

# 局部药丸筛选：仅针对笔头
all_tips = ["全部笔头"] + sorted(filtered_df['笔头类型'].unique().tolist())
selected_tip = st.pills("细分笔头查看：", all_tips, default="全部笔头")

d_tip = filtered_df.copy()
if selected_tip != "全部笔头":
    d_tip = d_tip[d_tip['笔头类型'] == selected_tip]

# 绘图
tip_trend = d_tip.groupby(['时间轴', '笔头类型'])['销量'].sum().reset_index()
fig_tip = px.line(tip_trend, x='时间轴', y='销量', color='笔头类型', markers=True, 
                  title=f"当前市场 ({selected_age}) 下的笔头销量走势")
st.plotly_chart(fig_tip, width='stretch')

st.markdown("---")

# --- 板块二：规格支数 ---
st.header("2️⃣ 规格支数：核心规格分析")

spec_total = filtered_df.groupby('支数')['销量'].sum().sort_values(ascending=False).reset_index()
top_10_specs = spec_total.head(10)['支数'].tolist()

selected_spec = st.pills("筛选特定规格：", ["全部 Top10"] + [str(s) for s in sorted(top_10_specs)], default="全部 Top10")

spec_data = filtered_df[filtered_df['支数'].isin(top_10_specs)].groupby(['时间轴', '支数'])['销量'].sum().reset_index()

if selected_spec != "全部 Top10":
    display_spec_data = spec_data[spec_data['支数'] == int(selected_spec)]
else:
    display_spec_data = spec_data

st.subheader("📈 销量趋势")
fig_spec_line = px.line(display_spec_data, x='时间轴', y='销量', color='支数', markers=True)
st.plotly_chart(fig_spec_line, width='stretch')

st.subheader("📊 市场份额变化")
total_monthly = display_spec_data.groupby('时间轴')['销量'].transform('sum')
display_spec_data['占比'] = display_spec_data['销量'] / total_monthly.replace(0, np.nan)

fig_spec_area = go.Figure()
for cat in sorted(display_spec_data['支数'].unique()):
    df_sub = display_spec_data[display_spec_data['支数'] == cat]
    fig_spec_area.add_trace(go.Scatter(
        x=df_sub['时间轴'], y=df_sub['占比'], name=f"{cat}支",
        stackgroup='one', fill='tonexty', hoveron='points',
        customdata=df_sub['销量'],
        hovertemplate="规格: %{fullData.name}<br>占比: %{y:.1%}<br>销量: %{customdata:,.0f}<extra></extra>"
    ))
fig_spec_area.update_layout(hovermode="closest", yaxis_tickformat='.0%', height=450)
st.plotly_chart(fig_spec_area, width='stretch')

st.markdown("---")

# --- 板块三：价格段 ---
st.header("3️⃣ 价格段深度分析")

all_prices = sorted(filtered_df['价格段'].unique().tolist())
selected_price = st.pills("筛选价格区间：", ["全部价格"] + all_prices, default="全部价格")

d_price = filtered_df.copy()
if selected_price != "全部价格":
    d_price = d_price[d_price['价格段'] == selected_price]

col_a, col_b = st.columns([1, 2])
with col_a:
    st.subheader("价格构成")
    fig_pie = px.pie(d_price, values='销量', names='价格段', hole=0.4)
    st.plotly_chart(fig_pie, width='stretch')
with col_b:
    st.subheader("月度走势推移")
    price_trend = d_price.groupby(['时间轴', '价格段'])['销量'].sum().reset_index()
    fig_price_bar = px.bar(price_trend, x='时间轴', y='销量', color='价格段', barmode='group')
    st.plotly_chart(fig_price_bar, width='stretch')
