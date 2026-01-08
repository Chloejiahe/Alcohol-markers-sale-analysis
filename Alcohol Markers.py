import streamlit as st
import pandas as pd
import plotly.express as px

# --- 1. 页面配置 ---
st.set_page_config(page_title="酒精笔销量深度看板", layout="wide")
st.title("📊 酒精笔市场趋势监测看板 (修复版)")
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

# --- 3. 侧边栏 ---
st.sidebar.header("🎛️ 全局筛选")
if not df.empty:
    years = sorted(list(set(df['month(month)'].str[:4])))
    selected_years = st.sidebar.multiselect("1. 选择年份", years, default=years)

    age_options = ["全部", "是", "否"]
    selected_age = st.sidebar.selectbox("2. 受众群体 (是否8+)", age_options, index=0)

    # 执行过滤
    filtered_df = df[df['month(month)'].str[:4].isin(selected_years)].copy()
    if selected_age != "全部":
        filtered_df = filtered_df[filtered_df['是否8+'] == selected_age]
else:
    st.stop()

# --- 4. 看板布局 ---

# 板块一：笔尖类型趋势
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
st.plotly_chart(fig_spec_line, use_container_width=True)

st.markdown("---")

# --- 2.2 市场份额图 (强制单点交互版) ---
st.subheader("📊 核心规格市场份额变化")

# 1. 预计算占比
total_monthly = spec_data.groupby('时间轴')['销量'].transform('sum')
spec_data['占比'] = spec_data['销量'] / total_monthly

# 2. 绘图
fig_spec_area = px.area(
    spec_data, 
    x='时间轴', 
    y='占比', 
    color='支数', 
    height=500,
    title="100% 市场份额分布推移",
    custom_data=['销量', '支数']
)

# 3. 【最核心修改】强制交互只针对“当前图层” (Key Fix)
# hoveron='points+fills' 是关键！它告诉程序：只有鼠标真正停留在色块内时才触发，而不是只要 X 轴对齐就触发。
fig_spec_area.update_traces(
    hoveron='points+fills', 
    hovertemplate="<b>规格: %{customdata[1]} 支</b><br>" + 
                  "当前份额: %{y:.1%}<br>" + 
                  "具体销量: %{customdata[0]:,.0f} 支<extra></extra>"
)

# 4. 【彻底禁用全局行为】
fig_spec_area.update_layout(
    xaxis_tickangle=-45,
    # 强制 closest 交互
    hovermode="closest", 
    yaxis_tickformat='.0%',
    yaxis_title="市场份额占比",
    # 彻底关掉那个触发“全列数据显示”的垂直虚线(Spikes)
    xaxis=dict(
        showspikes=False,   # 关掉垂直虚线
        spikemode="toaxis"  
    ),
    # 移除侧边栏名称标签，让弹窗更干净
    hoverlabel=dict(namelength=0)
)

st.plotly_chart(fig_spec_area, use_container_width=True)

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
fig_pie.update_traces(textinfo='percent+label', pull=[0.05]*len(filtered_df['价格段'].unique())) 
st.plotly_chart(fig_pie, use_container_width=True)

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
st.plotly_chart(fig_price, use_container_width=True)
