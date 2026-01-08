import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np  # 修复 1: 必须导入 numpy

# --- 1. 页面配置 ---
st.set_page_config(page_title="酒精笔销量深度看板", layout="wide")
st.title("📊 酒精笔市场趋势监测看板 (修复完成版)")
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

# --- 3. 侧边栏 ---
st.sidebar.header("🎛️ 全局筛选")
if not df.empty:
    years = sorted(list(set(df['month(month)'].str[:4])))
    selected_years = st.sidebar.multiselect("1. 选择年份", years, default=years)

    age_options = ["全部", "是", "否"]
    selected_age = st.sidebar.selectbox("2. 受众群体 (是否8+)", age_options, index=0)

    filtered_df = df[df['month(month)'].str[:4].isin(selected_years)].copy()
    if selected_age != "全部":
        filtered_df = filtered_df[filtered_df['是否8+'] == selected_age]
else:
    st.stop()

# --- 4. 看板布局 ---

# 板块一：笔尖类型趋势
st.header("1️⃣ 笔尖类型：不同市场销量起伏对比")

if selected_age == "全部":
    # --- 修改点：删掉 col1, col2 = st.columns(2) 以及相关的 with 语句 ---
    
    # 直接显示第一个图表（8+ 市场）
    st.subheader("8+ 市场")
    d1 = filtered_df[filtered_df['是否8+'] == '是'].groupby(['时间轴', '笔头类型'])['销量'].sum().reset_index()
    st.plotly_chart(px.line(d1, x='时间轴', y='销量', color='笔头类型', markers=True), width='stretch')
    
    # 可以在两个图之间加一个分割线
    st.markdown("---") 
    
    # 直接显示第二个图表（非 8+ 市场）
    st.subheader("非 8+ 市场")
    d2 = filtered_df[filtered_df['是否8+'] == '否'].groupby(['时间轴', '笔头类型'])['销量'].sum().reset_index()
    st.plotly_chart(px.line(d2, x='时间轴', y='销量', color='笔头类型', markers=True), width='stretch')

else:
    # 如果只选了某一个市场，逻辑保持不变
    d3 = filtered_df.groupby(['时间轴', '笔头类型'])['销量'].sum().reset_index()
    st.plotly_chart(px.line(d3, x='时间轴', y='销量', color='笔头类型', markers=True), width='stretch')

# --- 板块二：规格支数分析 ---
st.header("2️⃣ 规格支数：核心规格增长分析")
st.info("💡 已筛选销量前 10 规格。")

spec_total = filtered_df.groupby('支数')['销量'].sum().sort_values(ascending=False).reset_index()
top_10_specs = spec_total.head(10)['支数'].tolist()
spec_data = filtered_df[filtered_df['支数'].isin(top_10_specs)].groupby(['时间轴', '支数'])['销量'].sum().reset_index()

# 2.1 独立趋势图
st.subheader("📈 各核心规格独立销量趋势")
fig_spec_line = px.line(
    spec_data, 
    x='时间轴', 
    y='销量', 
    color='支数', 
    facet_col='支数', 
    facet_col_wrap=2, 
    height=800
)
fig_spec_line.for_each_annotation(lambda a: a.update(text=f"规格：{a.text.split('=')[-1]} 支"))
fig_spec_line.update_layout(showlegend=False)
st.plotly_chart(fig_spec_line, width='stretch')

st.markdown("---")

# --- 2.2 市场份额图 (核心修复版) ---
st.subheader("📊 核心规格市场份额变化")

# 第一步：手动计算占比
total_monthly = spec_data.groupby('时间轴')['销量'].transform('sum')
total_monthly = total_monthly.replace(0, np.nan)
spec_data['占比'] = spec_data['销量'] / total_monthly

# 第二步：使用 Graph Objects 逐个添加
fig_spec_area = go.Figure()
categories = sorted(spec_data['支数'].unique())

for cat in categories:
    df_sub = spec_data[spec_data['支数'] == cat]
    fig_spec_area.add_trace(go.Scatter(
        x=df_sub['时间轴'],
        y=df_sub['占比'],
        name=str(cat),
        mode='lines',      
        stackgroup='one',  
        fill='tonexty',    
        customdata=df_sub['销量'],
        # 修复 3: 限制 hover 触发区域
        hoveron='points+fills', 
        hovertemplate=(
            "<b>规格: " + str(cat) + "</b><br>" +
            "月份: %{x}<br>" +
            "市场占比: %{y:.1%}<br>" +
            "具体销量: %{customdata:,.0f} 支<extra></extra>"
        )
    ))

# 第三步：强化布局设置
fig_spec_area.update_layout(
    xaxis_tickangle=-45,
    hovermode="closest",       # 必须为 closest
    hoverdistance=10,          # 鼠标距离点10像素内才触发，防止垂直线触发所有数据
    spikedistance=-1,          # 关闭辅助线触发
    yaxis_tickformat='.0%',
    yaxis_title="市场份额占比",
    height=500
)

# 第四步：锁定交互工具栏
st.plotly_chart(
    fig_spec_area, 
    width='stretch', 
    config={
        'modeBarButtonsToRemove': ['hoverCompareCartesian', 'toggleHover'] # 彻底移除对比按钮
    }
)

# --- 板块三：价格段分析 ---
st.header("3️⃣ 价格段深度分析")
st.subheader("📊 整体市场价格构成")
fig_pie = px.pie(
    filtered_df, 
    values='销量', 
    names='价格段', 
    hole=0.4,
    color_discrete_sequence=px.colors.qualitative.Pastel
)
fig_pie.update_traces(textinfo='percent+label') 
st.plotly_chart(fig_pie, width='stretch')

st.markdown("---")

st.subheader("📈 月度价格走势推移")
price_data = filtered_df.groupby(['时间轴', '价格段'])['销量'].sum().reset_index()
fig_price = px.bar(
    price_data, 
    x='时间轴', 
    y='销量', 
    color='价格段', 
    barmode='group', 
    height=500
)
fig_price.update_layout(xaxis_tickangle=-45)
st.plotly_chart(fig_price, width='stretch')
