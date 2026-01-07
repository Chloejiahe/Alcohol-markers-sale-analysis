import streamlit as st
import pandas as pd
import plotly.express as px

# --- 1. 配置页面 ---
st.set_page_config(page_title="酒精笔销量看板", layout="wide")
st.title("📊 酒精笔市场实时分析看板")

# --- 2. 读取并清洗数据 ---
@st.cache_data
def load_data():
    file_path = "酒精笔销量数据.xlsx" 
    try:
        # 自动识别是 Excel 还是 GitHub 上的 CSV 格式
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path, engine='openpyxl')
    except Exception as e:
        st.error(f"文件读取失败，请检查文件名是否准确。错误信息: {e}")
        return pd.DataFrame()

    # 清洗：处理缺失值
    if '是否8+' in df.columns:
        df['是否8+'] = df['是否8+'].fillna('否')
    
    if 'month(month)' in df.columns:
        df['month(month)'] = df['month(month)'].astype(str)
        df = df.sort_values('month(month)') #
        
    # 过滤目标分类
    if '目标分类' in df.columns:
        return df[df['目标分类'] == '酒精笔'] #
    return df

df = load_data()

if df.empty:
    st.warning("数据为空，请检查数据源文件。")
    st.stop()

# --- 3. 侧边栏：交互控件 ---
st.sidebar.header("控制面板")
analysis_type = st.sidebar.selectbox(
    "选择分析维度",
    ["笔头类型趋势", "价格段分布", "支数趋势"]
)

# 动态获取受众群体选项
options = list(df['是否8+'].unique()) if '是否8+' in df.columns else ["是", "否"]
age_filter = st.sidebar.multiselect("受众群体筛选", options=options, default=options)

# --- 4. 根据筛选器过滤数据 ---
mask = df['是否8+'].isin(age_filter)
filtered_df = df[mask]

# --- 5. 实时图表逻辑 ---
if analysis_type == "笔头类型趋势":
    st.subheader("📈 笔尖销量随时间演变趋势")
    # 修正点：使用 '笔头类型'
    chart_data = filtered_df.groupby(['month(month)', '笔头类型', '是否8+'])['销量'].sum().reset_index()
    fig = px.line(chart_data, x='month(month)', y='销量', color='笔头类型',
                  facet_col='是否8+', markers=True, height=500)
    st.plotly_chart(fig, use_container_width=True)

elif analysis_type == "价格段分布":
    st.subheader("💰 各价格段销量占比分析")
    # 修正点：使用 '价格段'
    price_order = sorted(filtered_df['价格段'].unique()) if '价格段' in filtered_df.columns else None
    chart_data = filtered_df.groupby(['价格段', '是否8+'])['销量'].sum().reset_index()
    fig = px.bar(chart_data, x='价格段', y='销量', color='是否8+',
                barmode='group', category_orders={"价格段": price_order}, height=500)
    st.plotly_chart(fig, use_container_width=True)

else: # 支数趋势
    st.subheader("🔢 不同规格(支数)销量走势")
    # 修正点：将 '笔的数量' 改为 '支数'
    chart_data = filtered_df.groupby(['month(month)', '支数'])['销量'].sum().reset_index()
    fig = px.area(chart_data, x='month(month)', y='销量', color='支数', height=500)
    st.plotly_chart(fig, use_container_width=True)

# 展示原始数据预览
if st.checkbox("显示原始数据预览"):
    st.dataframe(filtered_df.head(50))
