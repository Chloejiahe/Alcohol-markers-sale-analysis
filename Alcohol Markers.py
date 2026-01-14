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
        
        # --- 【关键步骤】单只价格深度清洗与区间定义 ---
        # 1. 强制转为数字，无法转换的变为 NaN
        df['单只价格'] = pd.to_numeric(df['单只价格'], errors='coerce')
        
        # 2. 物理剔除负数和 0 (这是你指出的核心步骤，确保分析纯净)
        df = df[df['单只价格'] > 0].copy() 
        
        # 3. 按照您的 7 级业务逻辑划分区间
        bins = [0, 0.25, 0.5, 1.0, 2.0, 4.0, 6.0, float('inf')]
        labels = [
            '1. 超低价走量款 (≤0.25)', 
            '2. 大众平价款 (0.25-0.5]', 
            '3. 标准办公款 (0.5-1.0]', 
            '4. 品质进阶款 (1.0-2.0]', 
            '5. 中端功能款 (2.0-4.0]', 
            '6. 中高端款 (4.0-6.0]', 
            '7. 高端/奢侈款 (>6.0)'
        ]
        df['单只价格区间'] = pd.cut(df['单只价格'], bins=bins, labels=labels)
        # --------------------------------------------

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

    df_sub = spec_data_all[spec_data_all['支数'] == cat]

    fig_spec_area.add_trace(go.Scatter(
    x=df_sub['时间轴'], 
    y=df_sub['占比'], 
    name=f"{cat}支",
    stackgroup='one', 
    fill='tonexty', 
    hoveron='points',
    customdata=df_sub['销量'],
    # 重点：加入 时间: %{x}
    hovertemplate=(
        "时间: %{x}<br>"
        "规格: %{fullData.name}<br>"
        "占比: %{y:.1%}<br>"
        "销量: %{customdata:,.0f}"
        "<extra></extra>"
    )
))

fig_spec_area.update_layout(hovermode="closest", yaxis_tickformat='.0%', height=500)

st.plotly_chart(fig_spec_area, use_container_width=True)
# 局部按钮 (多选模式)
selected_specs = st.pills("筛选特定规格 (支持多选)：", [str(s) for s in sorted(top_10_specs)], selection_mode="multi")

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

# --- 板块四：单只价格精细分析 (最新业务逻辑) ---
st.header("4️⃣ 单只定价区间分析")

# 过滤异常数据（只看单价大于0的）
biz_df = filtered_df[filtered_df['单只价格'] > 0].copy()

tab_dist, tab_trend = st.tabs(["📊 销量占比分布", "📈 市场趋势推移"])

with tab_dist:
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("🎯 单只定价区间销量对比")
        # 柱状图：展示各区间总销量
        price_dist_fig = px.bar(
            biz_df.groupby('单只价格区间', observed=False)['销量'].sum().reset_index(),
            x='单只价格区间', y='销量', 
            color='单只价格区间',
            text_auto='.2s',
            title="哪个定价带最能出单？"
        )
        st.plotly_chart(price_dist_fig, use_container_width=True)
    
    with col_b:
        st.subheader("💰 单只定价区间市场份额")
        # 饼图：展示各区间份额占比
        fig_pie_biz = px.pie(
            biz_df, values='销量', names='单只价格区间', 
            hole=0.4, title="7级定价带销量占比"
        )
        st.plotly_chart(fig_pie_biz, use_container_width=True)

with tab_trend:
    st.subheader("⏳ 各单只定价月度销量走势")
    # 观察低价走量款与品质款的市场热度切换
    biz_trend_data = biz_df.groupby(['时间轴', '单只价格区间'], observed=False)['销量'].sum().reset_index()
    fig_biz_trend = px.line(biz_trend_data, x='时间轴', y='销量', color='单只价格区间', markers=True)
    st.plotly_chart(fig_biz_trend, use_container_width=True)

st.markdown("---")

# --- 核心规格定价博弈矩阵 ---
st.subheader("🔍 Top 10 规格竞争力定价矩阵")

# 1. 业务逻辑解析卡片
with st.expander("💡 如何解读这个矩阵？ (点击展开)"):
    st.markdown("""
    * **横轴 (X轴) - 规格支数**：反映了市场上最主流的 10 种产品规格。
    * **纵轴 (Y轴) - 单只价格**：反映了产品的溢价能力。纵向分布越广，说明该规格下的品牌差异化越大。
    * **气泡大小 - 销量**：气泡越大，代表该定价策略下的市场接受度越高。
    * **核心逻辑**：
        * **左下角气泡**：极致性价比区。靠超低单价获取海量市场份额。
        * **中上部气泡**：品牌/品质区。即便单价较高，若气泡依然巨大，说明该品牌拥有极强的护城河。
        * **孤立小气泡**：定价危险区。单价高且气泡小，可能存在溢价过高或受众过窄的问题。
    """)
    
# --- 关键修改：确保数据是干净的数字类型 ---
biz_df_top10 = biz_df[biz_df['支数'].isin(top_10_specs)].copy()
# 强制转换支数为整数，防止出现“.0”或乱码标签
biz_df_top10['支数'] = biz_df_top10['支数'].astype(int)

fig_scatter = px.scatter(
    biz_df_top10,
    x='支数',               # 确保这里对应的列只有数字
    y='单只价格', 
    size='销量', 
    color='单只价格区间',
    hover_name='Title',     # 产品标题仅出现在悬停浮窗里，不会跑到坐标轴上
    size_max=45,
    title="核心规格定价博弈矩阵", 
    labels={'单只价格': '单价 (USD)', '支数': '规格 (支数)'},
    hover_data={'支数': True, '单只价格': ':.3f', '销量': True, '单只价格区间': False}
)

# --- 关键修正 2：强制 X 轴为线性数字轴 ---
fig_scatter.update_layout(
    yaxis_range=[0, 8],
    xaxis=dict(
        type='linear',      # 强制指定为线性轴，防止 Plotly 把它当成文本轴
        tickmode='array',   # 指定只显示我们想要的刻度
        tickvals=sorted(top_10_specs), # 只在有数据的支数位置显示刻度
        title_font=dict(size=14)
    )
)

st.plotly_chart(fig_scatter, use_container_width=True)
