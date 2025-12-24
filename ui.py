# -*- coding: utf-8 -*-
import math
from pathlib import Path

import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode, JsCode
from streamlit_option_menu import option_menu
import streamlit_extras.stylable_container as stylable_container

# 设置Streamlit主题 - 必须是第一个st命令
st.set_page_config(
    layout="wide", 
    page_title="AI代码审查平台", 
    page_icon="🤖", 
    initial_sidebar_state="expanded"
)

import datetime
import os
import hashlib
import hmac
import base64
import time
import pandas as pd
from dotenv import load_dotenv
import matplotlib.pyplot as plt
import matplotlib as mpl
import matplotlib.font_manager as fm
import plotly.graph_objects as go
import plotly.express as px

from biz.service.review_service import ReviewService
from biz.ui.webhook_ui import render_webhook_management, render_branch_webhook_management
from biz.service.webhook_service import WebhookService
from matplotlib.ticker import MaxNLocator
from streamlit_cookies_manager import CookieManager

load_dotenv("conf/.env")


def set_global_font():
    """设置全局字体，如果字体文件不存在则忽略并使用默认字体"""
    font_path = "fonts/SourceHanSansCN-Regular.otf"
    if Path(font_path).exists():
        try:
            fm.fontManager.addfont(font_path)
            mpl.rcParams["font.family"] = "Source Han Sans CN"
        except Exception as e:
            st.warning(f"字体加载失败，使用默认字体。错误信息：{e}")
    else:
        st.warning(f"字体文件未找到：{font_path}，将使用默认字体。")

    mpl.rcParams["axes.unicode_minus"] = False  # 解决负号显示问题


# 在项目启动时调用
set_global_font()

# 从环境变量中读取用户名和密码
DASHBOARD_USER = os.getenv("DASHBOARD_USER", "admin")
DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "admin")
USER_CREDENTIALS = {
    DASHBOARD_USER: DASHBOARD_PASSWORD
}

# 用于生成和验证token的密钥
SECRET_KEY = os.getenv("DASHBOARD_SECRET_KEY", "fac8cf149bdd616c07c1a675c4571ccacc40d7f7fe16914cfe0f9f9d966bb773")

# 初始化cookie管理器
cookies = CookieManager()


def generate_token(username):
    """生成包含时间戳的认证token"""
    timestamp = str(int(time.time()))
    message = f"{username}:{timestamp}"

    # 使用HMAC-SHA256生成签名
    signature = hmac.new(
        SECRET_KEY.encode(),
        message.encode(),
        hashlib.sha256
    ).digest()

    # 将消息和签名编码为base64
    token = base64.b64encode(f"{message}:{base64.b64encode(signature).decode()}".encode()).decode()
    return token


def verify_token(token):
    """验证token的有效性并提取用户名"""
    try:
        # 解码token
        decoded = base64.b64decode(token.encode()).decode()
        message, signature = decoded.rsplit(":", 1)
        username, timestamp = message.split(":", 1)

        # 验证签名
        expected_signature = hmac.new(
            SECRET_KEY.encode(),
            message.encode(),
            hashlib.sha256
        ).digest()

        actual_signature = base64.b64decode(signature)

        if not hmac.compare_digest(expected_signature, actual_signature):
            return None

        # 检查token是否过期（30天）
        if int(time.time()) - int(timestamp) > 30 * 24 * 60 * 60:
            return None

        return username
    except:
        return None


# 检查登录状态
def check_login_status():
    if not cookies.ready():
        st.stop()

    if 'login_status' not in st.session_state:
        st.session_state['login_status'] = False

    # 尝试从cookie获取token
    auth_token = cookies.get('auth_token')
    if auth_token:
        username = verify_token(auth_token)
        if username and username in USER_CREDENTIALS:
            st.session_state['login_status'] = True
            st.session_state['username'] = username
            st.session_state['saved_username'] = username

    return st.session_state['login_status']


# 设置登录状态
def set_login_status(username, remember):
    st.session_state['login_status'] = True
    st.session_state['username'] = username
    st.session_state['saved_username'] = username if remember else ''

    if remember:
        # 生成并保存token到cookie
        auth_token = generate_token(username)
        cookies['auth_token'] = auth_token
    else:
        # 如果不记住登录状态，清除cookie
        if 'auth_token' in cookies:
            del cookies['auth_token']
    cookies.save()


# 获取保存的用户名
def get_saved_credentials():
    auth_token = cookies.get('auth_token')
    if auth_token:
        username = verify_token(auth_token)
        if username:
            return username, ''
    return st.session_state.get('saved_username', ''), ''


# 登录验证函数
def authenticate(username, password, remember_password=False):
    if username in USER_CREDENTIALS and USER_CREDENTIALS[username] == password:
        set_login_status(username, remember_password)
        return True
    return False


# 获取数据函数
def get_data(service_func, authors=None, project_names=None, updated_at_gte=None, updated_at_lte=None, columns=None):
    df = service_func(authors=authors, project_names=project_names, updated_at_gte=updated_at_gte,
                      updated_at_lte=updated_at_lte)

    if df.empty:
        return pd.DataFrame(columns=columns)

    if "updated_at" in df.columns:
        df["updated_at"] = df["updated_at"].apply(
            lambda ts: datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
            if isinstance(ts, (int, float)) else ts
        )

    def format_delta(row):
        if not math.isnan(row['additions']) and not math.isnan(row['deletions']):
            return f"+{int(row['additions'])}  -{int(row['deletions'])}"
        else:
            return ""

    if "additions" in df.columns and "deletions" in df.columns:
        df["delta"] = df.apply(format_delta, axis=1)
    else:
        df["delta"] = ""

    data = df[columns]
    return data


# 现代化Glassmorphism CSS样式
st.markdown("""
<style>
    /* 隐藏默认Streamlit菜单和页眉 */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* 主容器样式 */
    .main {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding-top: 1rem;
    }
    
    /* 侧边栏样式 */
    [data-testid="stSidebar"] {
        background: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(10px);
        box-shadow: 2px 0 10px rgba(0,0,0,0.1);
    }
    
    /* 玻璃态卡片样式 */
    .glass-card {
        background: rgba(255, 255, 255, 0.9);
        backdrop-filter: blur(10px);
        border-radius: 20px;
        padding: 2rem;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        border: 1px solid rgba(255, 255, 255, 0.2);
    }
    
    /* 登录容器样式 */
    .login-container {
        background: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(20px);
        border-radius: 30px;
        box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
        padding: 3rem 2rem;
        margin-top: 2rem;
        border: 1px solid rgba(255, 255, 255, 0.3);
    }
    
    /* 登录标题样式 */
    .login-title {
        text-align: center;
        color: #2E4053;
        margin: 1.5rem 0;
        font-size: 2.5rem;
        font-weight: 800;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    /* 平台图标样式 */
    .platform-icon {
        font-size: 5rem;
        text-align: center;
        margin-bottom: 1rem;
        text-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
    }
    
    /* 按钮样式 */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 25px;
        padding: 0.75rem 3rem;
        border: none;
        font-weight: 600;
        font-size: 1.1rem;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);
    }
    
    /* 输入框样式 */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea {
        border: 2px solid #e0e0e0;
        border-radius: 12px;
        padding: 0.75rem 1rem;
        background: rgba(255, 255, 255, 0.8);
        transition: all 0.3s ease;
    }
    
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: #667eea;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
    }
    
    /* 复选框样式 */
    .stCheckbox > div > div > input {
        accent-color: #667eea;
        width: 1.25rem;
        height: 1.25rem;
    }
    
    /* 数据表格样式 */
    .ag-theme-alpine {
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
    }
    
    /* 图表容器样式 */
    .chart-container {
        background: rgba(255, 255, 255, 0.9);
        backdrop-filter: blur(10px);
        border-radius: 20px;
        padding: 1.5rem;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
        height: 100%;
    }
    
    /* 侧边栏菜单样式 */
    .nav-menu {
        background: transparent;
        border: none;
        font-size: 1.1rem;
    }
    
    /* 信息提示样式 */
    .info-box {
        background: rgba(102, 126, 234, 0.1);
        border-left: 4px solid #667eea;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
    }
    
    .success-box {
        background: rgba(76, 175, 80, 0.1);
        border-left: 4px solid #4CAF50;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
    }
    
    .error-box {
        background: rgba(244, 67, 54, 0.1);
        border-left: 4px solid #F44336;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)


# 登录界面
def login_page():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        st.markdown('<div class="platform-icon">🤖</div>', unsafe_allow_html=True)
        st.markdown('<h1 class="login-title">AI代码审查平台</h1>', unsafe_allow_html=True)

        # 如果用户名和密码都为 'admin'，提示用户修改密码
        if DASHBOARD_USER == "admin" and DASHBOARD_PASSWORD == "admin":
            st.markdown('<div class="error-box">⚠️ <b>安全提示：</b>检测到默认用户名和密码为 \'admin\'，存在安全风险！<br><br>请立即修改：<br>1. 打开 <code>.env</code> 文件<br>2. 修改 <code>DASHBOARD_USER</code> 和 <code>DASHBOARD_PASSWORD</code> 变量<br>3. 保存并重启应用</div>', unsafe_allow_html=True)
            st.write(f"当前用户名: `{DASHBOARD_USER}`, 当前密码: `{DASHBOARD_PASSWORD}`")

        # 获取保存的用户名和密码
        saved_username, saved_password = get_saved_credentials()

        # 创建一个form，支持回车提交
        with st.form("login_form", clear_on_submit=False):
            username = st.text_input("👤 用户名", value=saved_username)
            password = st.text_input("🔑 密码", type="password", value=saved_password)
            remember_password = st.checkbox("记住密码", value=bool(saved_username))
            submit = st.form_submit_button("登 录")

            if submit:
                if authenticate(username, password, remember_password):
                    st.rerun()  # 重新运行应用以显示主要内容
                else:
                    st.markdown('<div class="error-box">❌ 用户名或密码错误</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)


# 生成Plotly图表 - 项目提交数量
def generate_project_count_chart_plotly(df):
    if df.empty:
        st.info("没有数据可供展示")
        return

    project_counts = df['project_name'].value_counts().reset_index()
    project_counts.columns = ['project_name', 'count']

    fig = px.bar(
        project_counts,
        x='project_name',
        y='count',
        title='项目提交统计',
        labels={'project_name': '项目', 'count': '提交数量'},
        color='count',
        color_continuous_scale='Viridis'
    )
    
    fig.update_layout(
        showlegend=False,
        xaxis_tickangle=-45,
        margin=dict(l=0, r=0, t=30, b=80),
        plot_bgcolor='rgba(255,255,255,0)',
        paper_bgcolor='rgba(255,255,255,0)',
    )
    
    fig.update_traces(
        marker_line_width=2,
        marker_line_color='rgba(0,0,0,0.1)',
        hovertemplate='<b>%{x}</b><br>提交数: %{y}<extra></extra>'
    )
    
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})


# 生成Plotly图表 - 项目平均分数
def generate_project_score_chart_plotly(df):
    if df.empty:
        st.info("没有数据可供展示")
        return

    project_scores = df.groupby('project_name')['score'].mean().reset_index()
    project_scores.columns = ['project_name', 'average_score']

    fig = px.bar(
        project_scores,
        x='project_name',
        y='average_score',
        title='项目平均得分',
        labels={'project_name': '项目', 'average_score': '平均得分'},
        color='average_score',
        color_continuous_scale='RdYlGn',
        range_color=[0, 100]
    )
    
    fig.update_layout(
        showlegend=False,
        xaxis_tickangle=-45,
        margin=dict(l=0, r=0, t=30, b=80),
        plot_bgcolor='rgba(255,255,255,0)',
        paper_bgcolor='rgba(255,255,255,0)',
        yaxis_range=[0, 100]
    )
    
    fig.update_traces(
        hovertemplate='<b>%{x}</b><br>平均分: %{y:.2f}<extra></extra>'
    )
    
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})


# 生成Plotly图表 - 人员提交数量
def generate_author_count_chart_plotly(df):
    if df.empty:
        st.info("没有数据可供展示")
        return

    author_counts = df['author'].value_counts().reset_index()
    author_counts.columns = ['author', 'count']

    fig = px.bar(
        author_counts,
        x='author',
        y='count',
        title='开发者提交统计',
        labels={'author': '开发者', 'count': '提交数量'},
        color='count',
        color_continuous_scale='Plasma'
    )
    
    fig.update_layout(
        showlegend=False,
        xaxis_tickangle=-45,
        margin=dict(l=0, r=0, t=30, b=80),
        plot_bgcolor='rgba(255,255,255,0)',
        paper_bgcolor='rgba(255,255,255,0)',
    )
    
    fig.update_traces(
        hovertemplate='<b>%{x}</b><br>提交数: %{y}<extra></extra>'
    )
    
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})


# 生成Plotly图表 - 人员平均分数
def generate_author_score_chart_plotly(df):
    if df.empty:
        st.info("没有数据可供展示")
        return

    author_scores = df.groupby('author')['score'].mean().reset_index()
    author_scores.columns = ['author', 'average_score']

    fig = px.bar(
        author_scores,
        x='author',
        y='average_score',
        title='开发者平均得分',
        labels={'author': '开发者', 'average_score': '平均得分'},
        color='average_score',
        color_continuous_scale='RdYlGn',
        range_color=[0, 100]
    )
    
    fig.update_layout(
        showlegend=False,
        xaxis_tickangle=-45,
        margin=dict(l=0, r=0, t=30, b=80),
        plot_bgcolor='rgba(255,255,255,0)',
        paper_bgcolor='rgba(255,255,255,0)',
        yaxis_range=[0, 100]
    )
    
    fig.update_traces(
        hovertemplate='<b>%{x}</b><br>平均分: %{y:.2f}<extra></extra>'
    )
    
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})


# 生成Plotly图表 - 人员代码行数
def generate_author_code_line_chart_plotly(df):
    if df.empty:
        st.info("没有数据可供展示")
        return

    if 'additions' not in df.columns or 'deletions' not in df.columns:
        st.warning("无法生成代码行数图表：缺少必要的数据列")
        return

    author_code_add = df.groupby('author')['additions'].sum().reset_index()
    author_code_add.columns = ['author', 'additions']
    author_code_del = df.groupby('author')['deletions'].sum().reset_index()
    author_code_del.columns = ['author', 'deletions']

    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        name='新增',
        x=author_code_add['author'],
        y=author_code_add['additions'],
        marker_color='rgba(76, 175, 80, 0.8)'
    ))
    
    fig.add_trace(go.Bar(
        name='删除',
        x=author_code_del['author'],
        y=-author_code_del['deletions'],
        marker_color='rgba(244, 67, 54, 0.8)'
    ))
    
    fig.update_layout(
        title='人员代码变更行数',
        xaxis_tickangle=-45,
        barmode='relative',
        showlegend=True,
        margin=dict(l=0, r=0, t=30, b=80),
        plot_bgcolor='rgba(255,255,255,0)',
        paper_bgcolor='rgba(255,255,255,0)',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})


# AgGrid分页表格显示
def display_aggrid(df, column_config, key):
    if df.empty:
        st.info("没有数据可供展示")
        return
    
    # 配置AgGrid选项
    gb = GridOptionsBuilder.from_dataframe(df)
    
    # 设置基本配置
    gb.configure_default_column(groupable=False, value=True, enableRowGroup=True, aggFunc='sum', pinned=True)
    
    # 配置列
    for col_name in df.columns:
        if col_name in column_config:
            config = column_config[col_name]
            if config is None:
                gb.configure_column(col_name, hide=True)
            elif isinstance(config, dict) and 'cellRenderer' in config:
                gb.configure_column(col_name, cellRenderer=config['cellRenderer'])
            elif isinstance(config, dict) and 'valueFormatter' in config:
                gb.configure_column(col_name, valueFormatter=config['valueFormatter'])
    
    # 配置分页
    gb.configure_pagination(
        paginationAutoPageSize=False,
        paginationPageSize=20,
        paginationPageSizeSelector=[10, 20, 50, 100]
    )
    
    # 配置选择
    gb.configure_selection(selection_mode='single', use_checkbox=True)
    gb.configure_grid_options(domLayout='normal')
    
    grid_options = gb.build()
    
    # 显示表格
    grid_response = AgGrid(
        df,
        gridOptions=grid_options,
        update_mode=GridUpdateMode.MODEL_CHANGED,
        data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
        fit_columns_on_grid_load=True,
        enable_enterprise_modules=True,
        key=key,
        theme='alpine',
        custom_css={
            ".ag-header": {
                "background-color": "rgba(102, 126, 234, 0.1) !important",
                "font-weight": "bold",
                "color": "#2E4053"
            },
            ".ag-row": {
                "font-size": "14px",
                "transition": "all 0.2s ease"
            },
            ".ag-row:hover": {
                "background-color": "rgba(102, 126, 234, 0.05) !important"
            }
        }
    )
    
    return grid_response


# 退出登录函数
def logout():
    # 清除session状态
    st.session_state['login_status'] = False
    st.session_state.pop('username', None)
    st.session_state.pop('saved_username', None)

    # 清除cookie
    if 'auth_token' in cookies:
        del cookies['auth_token']
    cookies.save()

    st.rerun()


# 主要内容
def main_page():
    # 侧边栏导航 - 使用现代化菜单
    with st.sidebar:
        selected = option_menu(
            menu_title=None,
            options=["📊 查询统计", "⚙️ 项目配置", "🌿 分支配置"],
            icons=["bar-chart", "gear", "git-branch"],
            menu_icon="cast",
            default_index=0,
            styles={
                "container": {"padding": "0!important", "background-color": "transparent"},
                "icon": {"color": "#667eea", "font-size": "1.2rem"},
                "nav-link": {
                    "font-size": "1rem",
                    "text-align": "left",
                    "margin": "0.5rem 0",
                    "--hover-color": "rgba(102, 126, 234, 0.1)",
                },
                "nav-link-selected": {
                    "background-color": "rgba(102, 126, 234, 0.15)",
                    "font-weight": "bold",
                    "color": "#667eea"
                },
            }
        )
    
    # 根据选择显示不同页面
    if selected == "⚙️ 项目配置":
        render_webhook_management()
        return
    elif selected == "🌿 分支配置":
        render_branch_webhook_management()
        return
    
    # 以下是 Dashboard 页面的内容
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown("#### 📊 查询统计")
    
    current_date = datetime.date.today()
    start_date_default = current_date - datetime.timedelta(days=7)

    # 根据环境变量决定是否显示 push_tab
    show_push_tab = os.environ.get('PUSH_REVIEW_ENABLED', '0') == '1'

    if show_push_tab:
        mr_tab, push_tab = st.tabs(["🔄 合并请求", "💻 代码推送"])
    else:
        mr_tab = st.container()

    def display_data(tab, service_func, columns, column_config, key):
        with tab:
            # 筛选器卡片
            st.markdown('<div class="chart-container" style="margin-bottom: 1.5rem;">', unsafe_allow_html=True)
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                start_date = st.date_input("📅 开始日期", start_date_default, key=f"{key}_start_date")
            with col2:
                end_date = st.date_input("📅 结束日期", current_date, key=f"{key}_end_date")

            start_datetime = datetime.datetime.combine(start_date, datetime.time.min)
            end_datetime = datetime.datetime.combine(end_date, datetime.time.max)

            data = get_data(service_func, updated_at_gte=int(start_datetime.timestamp()),
                            updated_at_lte=int(end_datetime.timestamp()), columns=columns)
            df = pd.DataFrame(data)

            unique_authors = sorted(df["author"].dropna().unique().tolist()) if not df.empty else []
            unique_projects = sorted(df["project_name"].dropna().unique().tolist()) if not df.empty else []
            with col3:
                authors = st.multiselect("👤 开发者", unique_authors, default=[], key=f"{key}_authors")
            with col4:
                project_names = st.multiselect("🏷️ 项目名称", unique_projects, default=[], key=f"{key}_projects")
            st.markdown('</div>', unsafe_allow_html=True)

            data = get_data(service_func, authors=authors, project_names=project_names,
                            updated_at_gte=int(start_datetime.timestamp()),
                            updated_at_lte=int(end_datetime.timestamp()), columns=columns)
            df = pd.DataFrame(data)

            # 统计信息
            total_records = len(df)
            average_score = df["score"].mean() if not df.empty else 0
            st.markdown(f'<div class="success-box">📊 <b>总记录数:</b> {total_records} | 🎯 <b>平均得分:</b> {average_score:.2f}</div>', unsafe_allow_html=True)

            # 数据表格 - 使用AgGrid
            display_aggrid(df, column_config, f"{key}_table")

            # 创建图表网格
            st.markdown('<br>', unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown('<div class="chart-container">', unsafe_allow_html=True)
                generate_project_count_chart_plotly(df)
                st.markdown('</div>', unsafe_allow_html=True)
            
            with col2:
                st.markdown('<div class="chart-container">', unsafe_allow_html=True)
                generate_project_score_chart_plotly(df)
                st.markdown('</div>', unsafe_allow_html=True)
            
            st.markdown('<br>', unsafe_allow_html=True)
            col3, col4 = st.columns(2)
            
            with col3:
                st.markdown('<div class="chart-container">', unsafe_allow_html=True)
                generate_author_count_chart_plotly(df)
                st.markdown('</div>', unsafe_allow_html=True)
            
            with col4:
                st.markdown('<div class="chart-container">', unsafe_allow_html=True)
                generate_author_score_chart_plotly(df)
                st.markdown('</div>', unsafe_allow_html=True)
            
            st.markdown('<br>', unsafe_allow_html=True)
            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
            generate_author_code_line_chart_plotly(df)
            st.markdown('</div>', unsafe_allow_html=True)
    
    # Merge Request 数据展示
    mr_columns = ["project_name", "author", "source_branch", "target_branch", "updated_at", "commit_messages", "delta",
                  "score", "url", 'additions', 'deletions']

    mr_column_config = {
        "project_name": "项目名称",
        "author": "开发者",
        "source_branch": "源分支",
        "target_branch": "目标分支",
        "updated_at": "更新时间",
        "commit_messages": "提交信息",
        "score": None,  # 进度条在AgGrid中需要特殊处理
        "url": {
            "headerName": "操作",
            "cellRenderer": JsCode("""
                class LinkRenderer {
                    init(params) {
                        this.eGui = document.createElement('a');
                        this.eGui.innerText = '查看详情';
                        this.eGui.href = params.value;
                        this.eGui.target = '_blank';
                        this.eGui.style.color = '#667eea';
                        this.eGui.style.fontWeight = 'bold';
                        this.eGui.style.textDecoration = 'none';
                        params.eGui.appendChild(this.eGui);
                    }
                    getGui() { return this.eGui; }
                }
                return new LinkRenderer();
            """)
        },
        "additions": None,
        "deletions": None,
        "delta": None,
    }

    display_data(mr_tab, ReviewService().get_mr_review_logs, mr_columns, mr_column_config, "mr")

    # Push 数据展示
    if show_push_tab:
        push_columns = ["project_name", "author", "branch", "updated_at", "commit_messages", "delta", "score",
                        'additions', 'deletions']

        push_column_config = {
            "project_name": "项目名称",
            "author": "开发者",
            "branch": "分支",
            "updated_at": "更新时间",
            "commit_messages": "提交信息",
            "score": None,
            "additions": None,
            "deletions": None,
            "delta": None,
        }

        display_data(push_tab, ReviewService().get_push_review_logs, push_columns, push_column_config, "push")
    
    st.markdown('</div>', unsafe_allow_html=True)


# 应用入口
if check_login_status():
    main_page()
else:
    login_page()

# 确保在直接运行 Streamlit UI 时也初始化 webhook 表
try:
    WebhookService.init_db()
except Exception:
    pass
