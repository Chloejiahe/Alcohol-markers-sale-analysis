import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import statsmodels.api as sm

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
        
        # --- 1. 强制转换月份为字符串并去除空格 (防止排序报错) ---
        df['month(month)'] = df['month(month)'].astype(str).str.strip()
        
        # --- 2. 只有统一为字符串后，排序才是绝对安全的 ---
        df = df.sort_values('month(month)')

        # --- 3. 单只价格深度清洗 ---
        df['单只价格'] = pd.to_numeric(df['单只价格'], errors='coerce')
        df = df[df['单只价格'] > 0].copy() 
        
        # 价格区间定义 (保持你原有的逻辑)
        bins = [0, 0.25, 0.5, 1.0, 2.0, 4.0, 6.0, float('inf')]
        labels = [
            '1. 超低价走量款 (≤0.25)', '2. 大众平价款 (0.25-0.5]', 
            '3. 标准办公款 (0.5-1.0]', '4. 品质进阶款 (1.0-2.0]', 
            '5. 中端功能款 (2.0-4.0]', '6. 中高端款 (4.0-6.0]', 
            '7. 高端/奢侈款 (>6.0)'
        ]
        df['单只价格区间'] = pd.cut(df['单只价格'], bins=bins, labels=labels)

        # 时间轴与填充
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

# 1. 整体分布：静态切片
st.subheader("📊 笔尖整体销量构成")
tip_pie = px.pie(filtered_df, values='销量', names='笔头类型', hole=0.4)
# 优化：显示百分比和标签
tip_pie.update_traces(textposition='inside', textinfo='percent+label')
st.plotly_chart(tip_pie, use_container_width=True)

# 2. 【新增】市场份额演变：动态结构分析
st.subheader("📈 笔头类型市场份额推移")

# 聚合数据：按月和笔头类型统计销量
tip_share_data = filtered_df.groupby(['时间轴', '笔头类型'])['销量'].sum().reset_index()

# 计算每月总销量，用于计算占比（归一化）
monthly_total = tip_share_data.groupby('时间轴')['销量'].transform('sum')
tip_share_data['占比'] = tip_share_data['销量'] / monthly_total

# 绘制堆积面积图
fig_tip_share = go.Figure()
tip_types = sorted(tip_share_data['笔头类型'].unique())

for tip in tip_types:
    sub_df = tip_share_data[tip_share_data['笔头类型'] == tip]
    fig_tip_share.add_trace(go.Scatter(
        x=sub_df['时间轴'], 
        y=sub_df['占比'], 
        name=tip,
        stackgroup='one',  # 开启堆积模式
        mode='lines',
        fill='tonexty',
        hovertemplate=f"笔头: {tip}<br>份额: %{{y:.1%}}<extra></extra>"
    ))

fig_tip_share.update_layout(
    xaxis_title="时间轴",
    yaxis_title="市场份额占比",
    yaxis_tickformat='.0%',  # 纵坐标显示百分比
    hovermode="x unified",    # 悬浮时显示该时间点所有数据
    height=450,
    template="plotly_white",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)
st.plotly_chart(fig_tip_share, use_container_width=True)



# 3. 细分对比：局部联动走势
st.subheader("🔍 细分笔头销量走势对比")

# 局部按钮 (多选模式)
all_tips = sorted(filtered_df['笔头类型'].unique().tolist())
selected_tips = st.pills("选择笔头进行具体走势对比 (支持多选)：", all_tips, selection_mode="multi", default=all_tips[:3])

if selected_tips:
    d_tip = filtered_df[filtered_df['笔头类型'].isin(selected_tips)]
    tip_trend = d_tip.groupby(['时间轴', '笔头类型'])['销量'].sum().reset_index()
    fig_tip = px.line(
        tip_trend, 
        x='时间轴', 
        y='销量', 
        color='笔头类型', 
        markers=True, 
        title=f"选定笔头的月度销量走势"
    )
    fig_tip.update_layout(hovermode="x unified", template="plotly_white")
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

# 1. 整体分布：静态切片
st.subheader("📊 整体市场价格构成")
fig_pie_price = px.pie(filtered_df, values='销量', names='价格段', hole=0.4)
fig_pie_price.update_traces(textposition='inside', textinfo='percent+label')
st.plotly_chart(fig_pie_price, use_container_width=True)

# 2. 【新增】价格段市场份额推移：动态结构分析
st.subheader("📈 价格段市场份额演变")

# 聚合数据：按月和价格段统计销量
price_share_data = filtered_df.groupby(['时间轴', '价格段'])['销量'].sum().reset_index()

# 计算每月总销量，用于归一化百分比
monthly_total_price = price_share_data.groupby('时间轴')['销量'].transform('sum')
price_share_data['占比'] = price_share_data['销量'] / monthly_total_price

# 为了绘图美观，对价格段进行排序（确保 0-4.99 在最下面，>=70 在最上面）
price_order = ['0-4.99', '5-9.99', '10-14.99', '15-19.99', '20-24.99', '25-29.99', '30-34.99', '35-39.99', '40-69.99', '>=70']
# 只保留数据中存在的价格段
existing_prices = [p for p in price_order if p in price_share_data['价格段'].unique()]

fig_price_share = go.Figure()

for price_range in existing_prices:
    sub_df = price_share_data[price_share_data['价格段'] == price_range]
    fig_price_share.add_trace(go.Scatter(
        x=sub_df['时间轴'], 
        y=sub_df['占比'], 
        name=price_range,
        stackgroup='one', # 开启堆积
        mode='lines',
        fill='tonexty',
        hovertemplate=f"价格段: {price_range}<br>份额: %{{y:.1%}}<extra></extra>"
    ))

fig_price_share.update_layout(
    xaxis_title="时间轴",
    yaxis_title="市场份额占比",
    yaxis_tickformat='.0%',
    hovermode="x unified",
    height=500,
    template="plotly_white",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)
st.plotly_chart(fig_price_share, use_container_width=True)


# 3. 细分走势：局部联动
st.subheader("🔍 细分价格段销量走势对比")

# 局部按钮 (多选模式)
all_prices = sorted(filtered_df['价格段'].unique().tolist())
selected_prices = st.pills("筛选价格区间查看走势 (支持多选)：", all_prices, selection_mode="multi")

# 图表 2：细分走势
if selected_prices:
    d_price = filtered_df[filtered_df['价格段'].isin(selected_prices)]
    price_trend = d_price.groupby(['时间轴', '价格段'])['销量'].sum().reset_index()
    # 这里将 px.bar 改为 px.line 更好观察趋势，或者保留 bar 也可以
    fig_price_line = px.line(
        price_trend, 
        x='时间轴', 
        y='销量', 
        color='价格段', 
        markers=True, 
        title="选定价格段月度销量走势"
    )
    fig_price_line.update_layout(hovermode="x unified", template="plotly_white")
    st.plotly_chart(fig_price_line, use_container_width=True)
else:
    st.info("请在上方选择价格段以对比走势。")

st.markdown("---")
    
# --- 板块四：单只价格精细分析 (最新业务逻辑) ---
st.header("4️⃣ 单只定价区间分析")

# 1. 过滤异常数据与准备
biz_df = filtered_df[filtered_df['单只价格'].notna() & (filtered_df['单只价格'] > 0)].copy()

# 定义标签顺序，确保图表堆叠逻辑从低价到高价
biz_price_order = [
    '1. 超低价走量款 (≤0.25)', 
    '2. 大众平价款 (0.25-0.5]', 
    '3. 标准办公款 (0.5-1.0]', 
    '4. 品质进阶款 (1.0-2.0]', 
    '5. 中端功能款 (2.0-4.0]', 
    '6. 中高端款 (4.0-6.0]', 
    '7. 高端/奢侈款 (>6.0)'
]

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
            title="哪个定价带最能出单？",
            category_orders={"单只价格区间": biz_price_order}
        )
        st.plotly_chart(price_dist_fig, use_container_width=True)
    
    with col_b:
        st.subheader("💰 单只定价区间市场份额")
        # 饼图：展示各区间份额占比
        fig_pie_biz = px.pie(
            biz_df, values='销量', names='单只价格区间', 
            hole=0.4, title="7级定价带销量占比",
            category_orders={"单只价格区间": biz_price_order}
        )
        fig_pie_biz.update_traces(textinfo='percent+label')
        st.plotly_chart(fig_pie_biz, use_container_width=True)

with tab_trend:
    # --- 新增：单只定价份额演变（面积图） ---
    st.subheader("📈 单只价格区间份额演变")
    
    # 计算份额数据
    biz_share_data = biz_df.groupby(['时间轴', '单只价格区间'], observed=False)['销量'].sum().reset_index()
    biz_monthly_total = biz_share_data.groupby('时间轴')['销量'].transform('sum')
    biz_share_data['占比'] = biz_share_data['销量'] / biz_monthly_total

    fig_biz_share = go.Figure()
    # 按照业务逻辑顺序堆叠
    existing_biz_labels = [l for l in biz_price_order if l in biz_share_data['单只价格区间'].unique()]
    
    for label in existing_biz_labels:
        sub_df = biz_share_data[biz_share_data['单只价格区间'] == label]
        fig_biz_share.add_trace(go.Scatter(
            x=sub_df['时间轴'], y=sub_df['占比'], 
            name=label,
            stackgroup='one',
            mode='lines',
            fill='tonexty',
            hovertemplate=f"区间: {label}<br>份额: %{{y:.1%}}<extra></extra>"
        ))
    
    fig_biz_share.update_layout(
        xaxis_title="时间轴", yaxis_title="市场份额",
        yaxis_tickformat='.0%', hovermode="x unified",
        height=450, template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig_biz_share, use_container_width=True)

# --- 2. 【核心修改】细分单价销量走势对比：改为按键操作模式 ---
    st.subheader("🔍 细分单价销量走势对比")

    # 获取所有可选的定价区间标签
    all_biz_intervals = sorted(biz_df['单只价格区间'].unique().tolist())
    
    # 添加按键操作 (st.pills)
    # 默认选中前三个区间，或者你可以根据业务需求调整 default
    selected_intervals = st.pills(
        "选择定价区间查看走势 (支持多选)：", 
        all_biz_intervals, 
        selection_mode="multi", 
        default=all_biz_intervals[:3]
    )

    if selected_intervals:
        # 根据按键选择过滤数据
        d_biz_trend = biz_df[biz_df['单只价格区间'].isin(selected_intervals)]
        
        # 聚合过滤后的数据
        biz_trend_plot_data = d_biz_trend.groupby(['时间轴', '单只价格区间'], observed=False)['销量'].sum().reset_index()
        
        fig_biz_trend = px.line(
            biz_trend_plot_data, 
            x='时间轴', 
            y='销量', 
            color='单只价格区间', 
            markers=True,
            category_orders={"单只价格区间": biz_price_order},
            title="选定单只定价带的月度实物销量走势"
        )
        fig_biz_trend.update_layout(hovermode="x unified", template="plotly_white")
        st.plotly_chart(fig_biz_trend, use_container_width=True)
    else:
        st.info("请在上方选择定价区间以查看具体销量走势。")

st.markdown("---")

# --- 1. 战略机会识别：规格 x 笔尖 蓝海气泡图 ---
st.markdown("---")
st.header("🚀 战略定位：细分蓝海机会识别")

# 提取年份
df['year_int'] = df['month(month)'].astype(str).str[:4].astype(int)

# 1. 自动定义“今年”和“去年”
latest_year = df['year_int'].max() 
prev_year = latest_year - 1

# 2. 人群筛选过滤
age_val = selected_age 
if age_val != "全部":
    base_calc_df = df[df['是否8+'] == age_val].copy()
else:
    base_calc_df = df.copy()

# 3. 分组聚合：增加对“月份数”的统计，用于计算月均值
# 今年数据：统计总销量和今年该产品卖了几个月
current_growth = base_calc_df[base_calc_df['year_int'] == latest_year].groupby(['支数', '笔头类型']).agg({
    '销量': 'sum', 
    '销售额': 'sum',
    'month(month)': 'nunique'  # 统计今年活跃了几个月
}).reset_index().rename(columns={'month(month)': '今年活跃月数'})

# 去年数据：统计总销量和去年该产品卖了几个月
prev_growth = base_calc_df[base_calc_df['year_int'] == prev_year].groupby(['支数', '笔头类型']).agg({
    '销量': 'sum',
    'month(month)': 'nunique'  # 统计去年活跃了几个月
}).reset_index().rename(columns={'销量': '去年销量', 'month(month)': '去年活跃月数'})

# 4. 合并计算
strat_df = pd.merge(current_growth, prev_growth, on=['支数', '笔头类型'], how='left').fillna(0)

# --- 核心逻辑切换：月均销量 ---
# 计算月均值（防止分母为0）
strat_df['今年月均'] = strat_df['销量'] / strat_df['今年活跃月数']
strat_df['去年月均'] = strat_df['去年销量'] / strat_df['去年活跃月数'].replace(0, np.nan)

# A. 同比增长率：现在是基于“月均效率”的增长
strat_df['同比增长率'] = (strat_df['今年月均'] - strat_df['去年月均']) / strat_df['去年月均']

# B. 市场份额：依然基于今年总销量，反映实际市场地位
strat_df['市场份额'] = strat_df['销量'] / strat_df['销量'].sum()

# C. 增长贡献率：基于总增量，反映对大盘贡献的物理支柱作用
total_delta = strat_df['销量'].sum() - strat_df['去年销量'].sum()
strat_df['增长贡献率'] = (strat_df['销量'] - strat_df['去年销量']) / (total_delta if total_delta != 0 else 1)

# --- 战略过滤 ---
# 过滤掉销量极低或增长率极其离谱的杂讯
plot_df = strat_df[
    (strat_df['销量'] > 100) & 
    (strat_df['同比增长率'] < 100) # 过滤掉月均增长超过100倍的离群值
].copy()

# 5. 绘图
fig_strat = px.scatter(
    plot_df, 
    x='市场份额',
    y='同比增长率',
    size='销量',
    color='增长贡献率',
    facet_col='笔头类型',
    hover_name='支数',
    # 悬浮框增加月均信息
    hover_data={'今年活跃月数': True, '今年月均': ':.1f', '去年月均': ':.1f'},
    color_continuous_scale='RdBu', 
    color_continuous_midpoint=0, 
    range_color=[-0.8, 0.8], # 饱和点设在80%贡献率
    title=f"战略定位：{latest_year} vs {prev_year} (月均增长逻辑)",
    labels={'市场份额': '市场份额 (重要性)', '同比增长率': '月均销量增长 (爆发力)'},
    height=600,
    template="plotly_white"
)

# 视觉增强
fig_strat.update_traces(marker=dict(line=dict(width=1, color='DarkSlateGrey'), opacity=0.85))
fig_strat.add_hline(y=0, line_dash="dash", line_color="black", opacity=0.3)
fig_strat.update_layout(coloraxis_colorbar=dict(title="贡献率(深蓝优)", tickformat=".0%"))

st.plotly_chart(fig_strat, use_container_width=True)

st.info("💡 **月均增长逻辑已启用**：Y轴反映的是单月销量的平均增幅。即使是今年新上架的产品，也能与其在架期间的平均表现进行公平对比。")

# --- 2. 深度配置定义：三维度交叉分析 ---
st.markdown("---")
st.header("🔬 深度定义：规格 x 定价 x 笔尖 交叉博弈")

if not biz_df.empty:
    # 聚合数据：支数(X), 单只单价(Y), 笔头类型(分栏), 价格段(颜色)
    triple_data = biz_df.groupby(['支数', '笔头类型', '价格段'], observed=False).agg({
        '销量': 'sum',
        '单只价格': 'mean' 
    }).reset_index()

    triple_data = triple_data[triple_data['销量'] > 100]

    fig_triple = px.scatter(
        triple_data,
        x='支数',
        y='单只价格',
        size='销量',
        color='价格段', 
        facet_col='笔头类型', 
        title="第三层：定义产品 (寻找高销量、高溢价的配置组合)",
        labels={'支数': '包装规格(支)', '单只价格': '平均单支售价(元)'},
        height=600,
        size_max=40,
        template="plotly_white",
        category_orders={"价格段": ['0-4.99', '5-9.99', '10-14.99', '15-19.99', '20-24.99', '25-29.99', '30-34.99', '35-39.99', '40-69.99', '>=70']}
    )

    fig_triple.update_layout(hovermode="closest")
    st.plotly_chart(fig_triple, use_container_width=True)
else:
    st.warning("当前筛选条件下无可用数据。")



import pandas as pd
import numpy as np
import plotly.graph_objects as go
import statsmodels.api as sm
import streamlit as st

# --- 5. 产品矩阵分析：基于 ASIN (唯一商品) 维度 ---
st.markdown("---")
st.header("🎯 ASIN 矩阵：爆款潜力挖掘")

id_col = 'ASIN' 
month_col = 'month(month)' 

# 预定义的新品列表
new_asin_list = [
    "B0FL78FF2F", "B0DP9BMKJR", "B0FB8LM5ZR", "B0FL2GLMPZ", "B0FDKM2Q3V",
    "B0DP9FDTT3", "B0F4X5NMCF", "B0F3JFHGCP", "B0FDG8XJPS", "B0FGHQCR1C",
    "B0FH4PYS7Q", "B0FH9MB9LD", "B0FJQM9LVB", "B0FJQXT63G"]

if id_col in df.columns and month_col in df.columns:
    # 1. 定义固定 12 个月区间
    target_12_months = [
        '202412', '202501', '202502', '202503', '202504', '202505', 
        '202506', '202507', '202508', '202509', '202510', '202511'
    ]
    
    matrix_base_df = df[df[month_col].astype(str).isin(target_12_months)].copy()
    
    # 同步侧边栏人群筛选（假设 side bar 已定义 selected_age）
    if 'selected_age' in locals() and selected_age != "全部":
        matrix_base_df = matrix_base_df[matrix_base_df['是否8+'] == selected_age]
    
    asin_stats = []
    # 第一步：遍历计算每个 ASIN 的基础统计值
    for asin, group in matrix_base_df.groupby(id_col):
        # 核心指标：该 ASIN 在这 12 个月里实际出现了几个月？
        m_sales_series = group.groupby(month_col)['销量'].sum().sort_index()
        active_months = len(m_sales_series)
        
        # Y 轴：月平均销量
        avg_sales = m_sales_series.mean()
        
        # X 轴：月度趋势得分 (RLM 回归)
        m_sales = m_sales_series.values
        if active_months > 1:
            x = np.arange(len(m_sales))
            x_with_const = sm.add_constant(x)
            try:
                model = sm.RLM(m_sales, x_with_const).fit()
                trend_score = model.params[1]
            except:
                trend_score = 0
        else:
            trend_score = 0
            
        asin_stats.append({
            'ASIN': asin,
            '销售趋势得分': trend_score,
            '月均销量': avg_sales,
            '活跃月份数': active_months  # 【新增】记录生存时长
        })

    if asin_stats:
        plot_df = pd.DataFrame(asin_stats)
        
        # --- 第二步：分类边界定义 ---
        x_p25 = plot_df['销售趋势得分'].quantile(0.25)
        x_p75 = plot_df['销售趋势得分'].quantile(0.75)
        x_median = plot_df['销售趋势得分'].median()
        x_mean = plot_df['销售趋势得分'].mean()
        y_median = plot_df['月均销量'].median()
        y_mean = plot_df['月均销量'].mean()

        def classify_asin(row):
            # 优先判定为手动指定的新品
            if row['ASIN'] in new_asin_list:
                return '新品 (90天)'
            
            # 【优化点】：只有销售时长 >= 4 个月的产品，才有资格评选“稳定产品”
            # 活跃月份太短的产品（即便得分平稳）统一划入“动态/待观察”
            if row['活跃月份数'] >= 4:
                if x_p25 <= row['销售趋势得分'] <= x_p75:
                    return '稳定产品'
            
            return '动态产品'

        plot_df['产品类型'] = plot_df.apply(classify_asin, axis=1)

        # --- 第三步：绘图 ---
        fig_matrix = go.Figure()

        color_map = {'动态产品': '#8c8cb4', '稳定产品': '#f2c977', '新品 (90天)': '#d65a5a'}
        symbol_map = {'动态产品': 'circle', '稳定产品': 'square', '新品 (90天)': 'triangle-up'}

        for t in ['稳定产品', '动态产品', '新品 (90天)']:
            curr_df = plot_df[plot_df['产品类型'] == t]
            if not curr_df.empty:
                fig_matrix.add_trace(go.Scatter(
                    x=curr_df['销售趋势得分'],
                    y=curr_df['月均销量'],
                    mode='markers',
                    name=t,
                    marker=dict(color=color_map[t], symbol=symbol_map[t], size=10, opacity=0.8),
                    text=curr_df['ASIN'],
                    customdata=curr_df['活跃月份数'], # 传入活跃月份
                    hovertemplate=(
                        "<b>ASIN: %{text}</b><br>" +
                        "活跃月份数: %{customdata}月<br>" +
                        "月度趋势得分: %{x:.2f}<br>" +
                        "月均销量: %{y:.0f}<br>" +
                        "分类: " + t + "<extra></extra>"
                    )
                ))

        # --- 第四步：视觉辅助线 ---
        fig_matrix.add_vline(x=x_p25, line_dash="dash", line_color="red", line_width=0.8,
                             annotation_text=f"P25: {x_p25:.2f}", annotation_position="top left")
        fig_matrix.add_vline(x=x_median, line_color="red", line_width=1.5,
                             annotation_text=f"<b>中位数: {x_median:.2f}</b>", annotation_position="top")
        fig_matrix.add_vline(x=x_p75, line_dash="dash", line_color="red", line_width=0.8,
                             annotation_text=f"P75: {x_p75:.2f}", annotation_position="top right")
        fig_matrix.add_hline(y=y_median, line_color="#4a90e2", line_width=1.5,
                             annotation_text=f"销量中位数: {y_median:,.0f}", annotation_position="right")

        # 布局设置
        fig_matrix.update_layout(
            template="plotly_white",
            title=f"产品矩阵分析 (固定周期: 202412 - 202511 | 稳定产品门槛: 活跃≥4个月)",
            xaxis_title="销售趋势得分 (月度增长斜率)",
            yaxis_title="月度平均销量",
            height=700,
            margin=dict(r=120, t=100),
            xaxis=dict(range=[plot_df['销售趋势得分'].min()*1.2 - 1, plot_df['销售趋势得分'].max()*1.2 + 1]),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )

        st.plotly_chart(fig_matrix, use_container_width=True)
else:
    st.error("数据缺失 ASIN 或 月份列，请检查数据源。")


# --- 6. 核心结构演变：Top15 季度竞争格局状况 ---
st.markdown("---")
st.header("⚖️ 核心结构演变：Top15 季度竞争格局状况")

# 定义你的 Top15 ASIN 列表
top15_asins = [
    "B07ZYFXLZ6", "B073TW8QHV", "B07NRB5G3Q", "B0BWH7CWFW", "B0BG7118BK",
    "B01H1NV1RE", "B08P4J7X8T", "B0BW87BYSN", "B074TC3LSR", "B07VK1G863",
    "B077S1NH7H", "B07RSV32MD", "B086JJVQPF", "B08YDDCBDZ", "B01GRF7NRY"
]

# 检查数据中是否存在“季度”列
if '季度' in filtered_df.columns:
    # 1. 标记是否为 Top15 产品
    struct_df = filtered_df.copy()
    struct_df['产品类型'] = struct_df['ASIN'].apply(lambda x: 'Top15头部' if x in top15_asins else '其他长尾产品')

    # 2. 按季度聚合销量
    # 注意：这里需要按季度排序，确保图表横轴逻辑正确
    quarter_stats = struct_df.groupby(['季度', '产品类型'])['销量'].sum().reset_index()
    
    # 3. 计算每个季度的贡献占比
    quarter_total = quarter_stats.groupby('季度')['销量'].transform('sum')
    quarter_stats['贡献占比'] = quarter_stats['销量'] / quarter_total

    # 4. 绘制季度结构演变堆积柱状图
    fig_struct = px.bar(
        quarter_stats, 
        x='季度', 
        y='销量', 
        color='产品类型',
        title="各季度市场结构演变 (Top15 vs 其他)",
        color_discrete_map={'Top15头部': '#1f77b4', '其他长尾产品': '#e5ecf6'},
        barmode='relative',
        text_auto='.2s'
    )
    
    # 5. 绘制贡献占比折线图（次坐标轴思想，通过两个图表并行展示）
    # 提取 Top15 的占比趋势
    top15_trend = quarter_stats[quarter_stats['产品类型'] == 'Top15头部'].sort_values('季度')
    
    fig_ratio = px.line(
        top15_trend,
        x='季度',
        y='贡献占比',
        markers=True,
        title="Top15 市场销量贡献率走势 (%)",
        text=top15_trend['贡献占比'].apply(lambda x: f"{x:.1%}")
    )
    fig_ratio.update_traces(textposition="top center", line_color='#d65a5a', line_width=3)
    fig_ratio.update_layout(yaxis_tickformat='.0%', yaxis_range=[0, 1])

    # 布局展示
    col_left, col_right = st.columns([3, 2])
    with col_left:
        st.plotly_chart(fig_struct, use_container_width=True)
    with col_right:
        st.plotly_chart(fig_ratio, use_container_width=True)

    # 6. 自动诊断逻辑
    latest_ratio = top15_trend['贡献占比'].iloc[-1] if not top15_trend.empty else 0
    avg_ratio = top15_trend['贡献占比'].mean() if not top15_trend.empty else 0
    
    st.info(f"""
    **🔍 季度结构诊断：**
    - **当前份额**：最近一个季度 Top15 占据了市场 **{latest_ratio:.1%}** 的销量。
    - **历史均值**：Top15 的平均贡献水平在 **{avg_ratio:.1%}**。
    - **格局提示**：{'⚠️ 头部效应正在加强，市场进入壁垒极高。' if latest_ratio > avg_ratio else '✅ 头部份额有所松动，新进产品存在突围空间。'}
    - **判断标准**：若 Top15 长期贡献 > 50%，说明增长严重依赖头部玩家，属于“存量收割”市场。
    """)
else:
    st.error("数据集中未找到名为 '季度' 的列，请检查 Excel 表头。")
