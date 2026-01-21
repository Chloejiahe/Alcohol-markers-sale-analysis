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

# 过滤异常数据：
# 1. 剔除非数字内容（如 '--' 转换后变成的 NaN）
# 2. 剔除单价小于等于 0 的数据
biz_df = filtered_df[filtered_df['单只价格'].notna() & (filtered_df['单只价格'] > 0)].copy()

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



# --- 5. 产品矩阵分析：基于 ASIN (唯一商品) 维度 ---
st.markdown("---")
st.header("🎯 ASIN 矩阵：爆款潜力挖掘")

id_col = 'ASIN' 
# 使用你定义的月份列名，根据之前代码应该是 '时间轴' 或 'month(month)'
# 这里建议使用 month(month) 因为它便于排序
month_col = 'month(month)' 

new_asin_list = [
    "B0FCS8ZWQB", "B0FKLR5YCB", "B0FCS6M53X", "B0FGHQCR1C", "B0FL2FVWRS",
    "B0FL2KGB6Q", "B0FD34KW2Z", "B0FMYFW6Q9", "B0FNW7NYZ5", "B0FM3Q1R6V",
    "B0FM83L163", "B0FH1JBW5T", "B0FDLC8MJ6", "B0FP2YV4ZZ", "B0FPDZ7VYM",
    "B0F91WRVHF", "B0FL78FF2F", "B0FKMB9LVM", "B0FKGPNWMN", "B0FKN1JBXR"]

if id_col in filtered_df.columns and month_col in filtered_df.columns:
    
    # 1. 获取最近 12 个月列表 (对应过去一年)
    recent_12_months = sorted(filtered_df[month_col].unique())[-12:]
    matrix_base_df = filtered_df[filtered_df[month_col].isin(recent_12_months)].copy()
    
    asin_stats = []
    
    # 第一步：遍历计算每个 ASIN 的基础统计值
    for asin, group in matrix_base_df.groupby(id_col):
        # Y 轴：月平均销量
        avg_sales = group.groupby(month_col)['销量'].sum().mean()
        
        # X 轴：月度趋势计算
        m_sales_series = group.groupby(month_col)['销量'].sum().sort_index()
        m_sales = m_sales_series.values
        
        if len(m_sales) > 1:
            # 使用简单的 0, 1, 2... 作为时间轴进行回归
            x = np.arange(len(m_sales))
            x_with_const = sm.add_constant(x)
            try:
                # 稳健回归获取月度增长斜率
                model = sm.RLM(m_sales, x_with_const).fit()
                trend_score = model.params[1]
            except:
                trend_score = 0
        else:
            trend_score = 0
            
        asin_stats.append({
            'ASIN': asin,
            '销售趋势得分': trend_score,
            '月均销量': avg_sales
        })

    if asin_stats:
        plot_df = pd.DataFrame(asin_stats)
        
        # --- 第二步：分类边界定义 (基于月度得分的分位数) ---
        x_p25 = plot_df['销售趋势得分'].quantile(0.25)
        x_p75 = plot_df['销售趋势得分'].quantile(0.75)
        x_median = plot_df['销售趋势得分'].median()
        y_median = plot_df['月均销量'].median()
        y_mean = plot_df['月均销量'].mean() # 【新增】计算月均销量的平均值

        def classify_asin(row):
            if row['ASIN'] in new_asin_list:
                return '新品 (90天)'
            if x_p25 <= row['销售趋势得分'] <= x_p75:
                return '稳定产品'
            else:
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
                    hovertemplate="ASIN: %{text}<br>月度趋势得分: %{x:.2f}<br>月均销量: %{y:.0f}<br>分类: "+t+"<extra></extra>"
                ))

        # 4. 视觉辅助线与背景
        fig_matrix.add_vrect(
            x0=x_p25, x1=x_p75, 
            fillcolor="rgba(128, 128, 128, 0.1)", 
            layer="below", line_width=0,
            annotation_text="稳定波动区 (P25-P75)", annotation_position="top left"
        )

        # 垂直线 (X轴趋势)
        fig_matrix.add_vline(x=x_median, line_color="red", line_width=1.5)
        fig_matrix.add_vline(x=x_p25, line_dash="dash", line_color="red", line_width=0.8)
        fig_matrix.add_vline(x=x_p75, line_dash="dash", line_color="red", line_width=0.8)
        
        # 水平参考线（Y轴）
        fig_matrix.add_hline(y=y_median, line_color="#4a90e2", line_width=1.5) # 蓝色实线：中位数
        fig_matrix.add_hline(y=y_mean, line_color="#4a90e2", line_dash="dash", line_width=1.2, opacity=0.7)

        # 5. 具体数值标注
        
        # X轴数值标注
        y_max = plot_df['月均销量'].max()
        annotations = [
            dict(x=x_p25, y=y_max, text=f"P25: {x_p25:.2f}", showarrow=False, yshift=20, font=dict(color="red", size=10)),
            dict(x=x_median, y=y_max, text=f"中位数: {x_median:.2f}", showarrow=False, yshift=35, font=dict(color="red", size=11, bold=True)),
            dict(x=x_p75, y=y_max, text=f"P75: {x_p75:.2f}", showarrow=False, yshift=20, font=dict(color="red", size=10)),
        ]

        # Y轴数值标注
        x_max = plot_df['销售趋势得分'].max()
        annotations.extend([
            dict(x=x_max, y=y_median, text=f" 中位数: {y_median:,.0f}", xanchor="left", showarrow=False, 
                 bgcolor="black", font=dict(color="white", size=10)),
            dict(x=x_max, y=y_mean, text=f" 平均值: {y_mean:,.0f}", xanchor="left", showarrow=False, 
                 bgcolor="#4a90e2", font=dict(color="white", size=10), yshift=15 if abs(y_mean-y_median)<(y_max*0.05) else 0)
        ])
        
        fig_matrix.update_layout(
            template="plotly_white",
            title=f"产品矩阵分析 (基于最近 {len(recent_12_months)} 个月数据)",
            xaxis_title="销售趋势得分 (月度增长斜率)",
            yaxis_title="月度平均销量",
            height=700,
            margin=dict(r=120, t=80), # 增加右边距和顶边距放标签
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )

        st.plotly_chart(fig_matrix, use_container_width=True)
    else:
        st.warning("数据不足，无法生成矩阵。")
