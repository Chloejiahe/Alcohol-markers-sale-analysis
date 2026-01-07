import streamlit as st
import pandas as pd
import plotly.express as px

# --- 1. 页面配置 ---
st.set_page_config(page_title="酒精笔销售深度分析", layout="wide")
st.title("📊 酒精笔市场趋势监测看板")
st.markdown("---")

# --- 2. 数据处理逻辑 ---
@st.cache_data
def load_data():
    file_path = "酒精笔销量数据.xlsx" 
    try:
        df = pd.read_excel(file_path, engine='openpyxl')
        # 清洗：去除列名空格
        df.columns = [c.strip() for c in df.columns]
        
        # 转换时间格式：将 202311 转换为 2023-11 字符串，确保排序正确
        df['month(month)'] = df['month(month)'].astype(str)
        df = df.sort_values('month(month)')
        df['时间轴'] = df['month(month)'].apply(lambda x: f"{x[:4]}-{x[4:]}")
        
        # 填充缺失值
        df['是否8+'] = df['是否8+'].fillna('否')
        
        # 仅保留酒精笔数据
        if '目标分类' in df.columns:
            df = df[df['目标分类'] == '酒精笔']
            
        return df
    except Exception as e:
        st.error(f"数据加载出错，请检查Excel列名。错误: {e}")
        return pd.DataFrame()

df = load_data()

# --- 3. 增强版侧边栏筛选 ---
st.sidebar.header("🎛️ 全局筛选器")

# 年份筛选
years = sorted(list(set(df['month(month)'].str[:4])))
selected_years = st.sidebar.multiselect("1. 选择年份", years, default=years)

# 核心修改：受众群体筛选
age_options = ["全部", "是", "否"]
selected_age = st.sidebar.radio("2. 受众群体 (是否8+)", age_options, index=0)

# 执行过滤
filtered_df = df[df['month(month)'].str[:4].isin(selected_years)]
if selected_age != "全部":
    filtered_df = filtered_df[filtered_df['是否8+'] == selected_age]

# --- 4. 看板布局 ---

# 板块一：笔尖类型趋势 (解决你说的对比不清晰问题)
st.header("1️⃣ 笔尖类型趋势深度对比")

if selected_age == "全部":
    st.info("💡 当前展示‘8+’与‘非8+’对比模式")
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("年龄段：8+")
        d1 = filtered_df[filtered_df['是否8+'] == '是'].groupby(['时间轴', '笔头类型'])['销量'].sum().reset_index()
        fig1 = px.line(d1, x='时间轴', y='销量', color='笔头类型', markers=True, title="8+ 市场趋势")
        st.plotly_chart(fig1, use_container_width=True)
        
    with col2:
        st.subheader("年龄段：非 8+")
        d2 = filtered_df[filtered_df['是否8+'] == '否'].groupby(['时间轴', '笔头类型'])['销量'].sum().reset_index()
        fig2 = px.line(d2, x='时间轴', y='销量', color='笔头类型', markers=True, title="非 8+ 市场趋势")
        st.plotly_chart(fig2, use_container_width=True)
else:
    st.subheader(f"当前筛选：受众是否为8+ -> {selected_age}")
    d3 = filtered_df.groupby(['时间轴', '笔头类型'])['销量'].sum().reset_index()
    fig3 = px.line(d3, x='时间轴', y='销量', color='笔头类型', markers=True, height=600)
    st.plotly_chart(fig3, use_container_width=True)

st.markdown("---")

# 板块二：价格段分布 (使用百分比堆叠，看结构变化)
st.header("2️⃣ 价格段市场结构分析")
col3, col4 = st.columns([1, 2])

with col3:
    # 饼图看整体
    fig_pie = px.pie(filtered_df, values='销量', names='价格段', hole=0.4, title="所选范围内价格构成")
    st.plotly_chart(fig_pie, use_container_width=True)

with col4:
    # 堆叠条形图看每个月价格重心的移动
    price_data = filtered_df.groupby(['时间轴', '价格段'])['销量'].sum().reset_index()
    fig_bar = px.bar(price_data, x='时间轴', y='销量', color='价格段', title="月度价格结构推移", barmode='relative')
    st.plotly_chart(fig_bar, use_container_width=True)

st.markdown("---")

# 板块三：规格支数 (解决混乱，采用矩阵热力图)
st.header("3️⃣ 规格支数销量热度矩阵")
st.write("颜色越深代表销量越高，可以直观看出哪个时间点哪个规格卖得最好。")

# 矩阵图
heatmap_data = filtered_df.pivot_table(index='支数', columns='时间轴', values='销量', aggfunc='sum').fillna(0)
fig_heat = px.imshow(heatmap_data, text_auto=True, color_continuous_scale='RdBu_r', aspect="auto")
st.plotly_chart(fig_heat, use_container_width=True)

if st.checkbox("查看过滤后的原始数据明细"):
    st.dataframe(filtered_df)
