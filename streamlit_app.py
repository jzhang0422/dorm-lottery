"""
宿舍抽签系统 V3.3 - 持久化云端版
作者：凯迪
功能：男女生分开抽取、问题宿舍管理、单次记录删除、已抽签宿舍上传、多轮抽签
更新：数据存储在 GitHub，永久保存不丢失
"""

import streamlit as st
import pandas as pd
import random
import os
from datetime import datetime
import json
import io
import base64
import requests

# ==================== 配置 ====================
st.set_page_config(
    page_title="宿舍抽签系统 V3.3",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# GitHub 配置（从 secrets 读取）
GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN", "")
GITHUB_REPO = "jzhang0422/dorm-lottery"
GITHUB_BRANCH = "main"
DATA_PATH = "data"

# ==================== GitHub 数据存储函数 ====================

def get_github_headers():
    """获取 GitHub API 请求头"""
    return {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }

def github_file_exists(file_path):
    """检查 GitHub 上文件是否存在"""
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{file_path}"
    params = {"ref": GITHUB_BRANCH}
    try:
        response = requests.get(url, headers=get_github_headers(), params=params, timeout=30)
        return response.status_code == 200
    except:
        return False

def github_read_file(file_path):
    """从 GitHub 读取文件内容"""
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{file_path}"
    params = {"ref": GITHUB_BRANCH}
    try:
        response = requests.get(url, headers=get_github_headers(), params=params, timeout=30)
        if response.status_code == 200:
            content = response.json()
            if content.get("encoding") == "base64":
                return base64.b64decode(content["content"]).decode("utf-8"), content.get("sha")
        return None, None
    except Exception as e:
        st.error(f"读取 GitHub 文件失败: {e}")
        return None, None

def github_write_file(file_path, content, message="Update data"):
    """写入文件到 GitHub"""
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{file_path}"
    
    # 获取现有文件的 SHA（如果存在）
    _, sha = github_read_file(file_path)
    
    # 准备请求数据
    data = {
        "message": message,
        "branch": GITHUB_BRANCH,
        "content": base64.b64encode(content.encode("utf-8")).decode("utf-8")
    }
    if sha:
        data["sha"] = sha
    
    try:
        response = requests.put(url, headers=get_github_headers(), json=data, timeout=30)
        if response.status_code in [200, 201]:
            return True
        else:
            st.error(f"写入 GitHub 失败: {response.json().get('message', '未知错误')}")
            return False
    except Exception as e:
        st.error(f"写入 GitHub 失败: {e}")
        return False

# ==================== 数据加载/保存函数 ====================

def load_lottery_data():
    """加载抽签数据"""
    file_path = f"{DATA_PATH}/lottery_data_v3.json"
    content, _ = github_read_file(file_path)
    if content:
        try:
            data = json.loads(content)
            # 兼容旧数据，添加轮次字段
            for gender in ["男生", "女生"]:
                if "当前轮次" not in data[gender]:
                    data[gender]["当前轮次"] = 1
                if "轮次已抽取" not in data[gender]:
                    old_drawn = data[gender].get("已抽取", [])
                    data[gender]["轮次已抽取"] = {"1": old_drawn}
            return data
        except:
            pass
    return {
        "男生": {"记录": [], "当前轮次": 1, "轮次已抽取": {}},
        "女生": {"记录": [], "当前轮次": 1, "轮次已抽取": {}}
    }

def save_lottery_data(data):
    """保存抽签数据到 GitHub"""
    file_path = f"{DATA_PATH}/lottery_data_v3.json"
    content = json.dumps(data, ensure_ascii=False, indent=2)
    return github_write_file(file_path, content, "更新抽签数据")

def load_problem_dorms():
    """加载问题宿舍数据"""
    file_path = f"{DATA_PATH}/problem_dorms.json"
    content, _ = github_read_file(file_path)
    if content:
        try:
            return json.loads(content)
        except:
            pass
    return {}

def save_problem_dorms(data):
    """保存问题宿舍数据到 GitHub"""
    file_path = f"{DATA_PATH}/problem_dorms.json"
    content = json.dumps(data, ensure_ascii=False, indent=2)
    return github_write_file(file_path, content, "更新问题宿舍数据")

def load_dorm_list():
    """加载宿舍清单"""
    file_path = f"{DATA_PATH}/dorm_list.json"
    content, _ = github_read_file(file_path)
    if content:
        try:
            data = json.loads(content)
            return pd.DataFrame(data)
        except:
            pass
    return None

def save_dorm_list(df):
    """保存宿舍清单到 GitHub"""
    file_path = f"{DATA_PATH}/dorm_list.json"
    # 转换为 JSON 格式存储
    content = df.to_json(orient="records", force_ascii=False)
    return github_write_file(file_path, content, "更新宿舍清单")

# ==================== 样式 ====================

st.markdown("""
<style>
    .main-header {
        font-size: 2rem;
        font-weight: bold;
        text-align: center;
        padding: 1rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 10px;
        margin-bottom: 1rem;
    }
    .round-badge {
        background: linear-gradient(135deg, #ffd43b 0%, #ff922b 100%);
        color: #333;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-weight: bold;
        display: inline-block;
    }
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        padding: 1rem;
        border-radius: 5px;
        margin: 0.5rem 0;
    }
    .warning-box {
        background-color: #fff3cd;
        border: 1px solid #ffeeba;
        color: #856404;
        padding: 1rem;
        border-radius: 5px;
        margin: 0.5rem 0;
    }
    .data-status {
        position: fixed;
        top: 10px;
        right: 10px;
        background: #28a745;
        color: white;
        padding: 5px 10px;
        border-radius: 15px;
        font-size: 0.8rem;
        z-index: 999;
    }
</style>
""", unsafe_allow_html=True)

# ==================== 侧边栏 ====================

st.sidebar.title("🏠 宿舍抽签系统")
st.sidebar.caption("V3.3 - 持久化云端版")
st.sidebar.success("💾 数据已保存到云端")

page = st.sidebar.radio(
    "📋 功能导航",
    ["🎲 抽签", "📤 已抽签宿舍上传", "❓ 问题宿舍管理", "📄 上传宿舍清单", "📊 数据统计"]
)

st.sidebar.markdown("---")

# ==================== 主程序 ====================

df = load_dorm_list()
lottery_data = load_lottery_data()
problem_dorms = load_problem_dorms()

# ==================== 页面1：抽签 ====================

if page == "🎲 抽签":
    if df is None:
        st.warning("⚠️ 请先在「上传宿舍清单」页面上传宿舍数据！")
        st.stop()
    
    st.markdown('<div class="main-header">🎲 宿舍抽签</div>', unsafe_allow_html=True)
    
    # 统计信息
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("总宿舍数", len(df))
    with col2:
        male_count = len(df[df['性别'] == '男生公寓'])
        st.metric("男生宿舍", male_count)
    with col3:
        female_count = len(df[df['性别'] == '女生公寓'])
        st.metric("女生宿舍", female_count)
    with col4:
        problem_count = len(problem_dorms)
        st.metric("问题宿舍", problem_count)
    
    st.markdown("---")
    
    # 抽签设置
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("📌 抽签设置")
        
        gender_choice = st.radio("选择宿舍类型：", options=["男生", "女生"], horizontal=True)
        
        gender_text = "男生公寓" if gender_choice == "男生" else "女生公寓"
        gender_df = df[df['性别'] == gender_text].copy()
        total_dorms = len(gender_df)
        current_round = lottery_data[gender_choice]["当前轮次"]
        round_drawn_dict = lottery_data[gender_choice].get("轮次已抽取", {})
        
        # 获取当前轮已抽取的宿舍
        current_round_drawn = round_drawn_dict.get(str(current_round), [])
        # 所有轮已抽取的宿舍（用于排除）
        all_drawn = []
        for r in range(1, current_round + 1):
            all_drawn.extend(round_drawn_dict.get(str(r), []))
        
        # 当前轮未抽取的宿舍
        available_df = gender_df[~gender_df['宿舍号'].astype(str).isin(current_round_drawn)]
        problem_available = [d for d in problem_dorms.keys() if d in available_df['宿舍号'].astype(str).tolist()]
        normal_available = available_df[~available_df['宿舍号'].astype(str).isin(problem_dorms.keys())]
        
        st.info(f"📊 {gender_choice}宿舍状态：")
        st.markdown(f'<span class="round-badge">第 {current_round} 轮</span>', unsafe_allow_html=True)
        st.write(f"- 总宿舍数：{total_dorms} 间")
        st.write(f"- 当前轮已抽取：{len(current_round_drawn)} 间")
        st.write(f"- 当前轮剩余未抽：{len(available_df)} 间")
        st.write(f"- 其中问题宿舍：{len(problem_available)} 间")
        
        draw_count = st.number_input("抽取数量：", min_value=1, max_value=total_dorms, value=min(20, total_dorms), step=1)
        
        max_problem = min(len(problem_available), draw_count)
        problem_count_setting = st.number_input(
            "包含问题宿舍数量：", min_value=0, max_value=max_problem if max_problem > 0 else 0,
            value=min(5, max_problem) if max_problem > 0 else 0, step=1, help="优先抽取问题宿舍"
        )
        
        if len(available_df) < draw_count:
            need_from_new_round = draw_count - len(available_df)
            st.warning(f"⚠️ 当前轮剩余 {len(available_df)} 间，将从第 {current_round + 1} 轮补抽 {need_from_new_round} 间")
    
    with col2:
        st.subheader("🎯 操作")
        
        if st.button("🎲 开始抽取", type="primary", use_container_width=True):
            with st.spinner("正在抽取并保存到云端..."):
                selected_dorms = []
                round_info = []
                remaining_to_draw = draw_count
                
                # 先抽问题宿舍（从当前轮）
                if problem_count_setting > 0 and problem_available:
                    problem_to_draw = min(problem_count_setting, len(problem_available))
                    selected_problems = random.sample(problem_available, problem_to_draw)
                    selected_dorms.extend(selected_problems)
                    round_info.extend([current_round] * len(selected_problems))
                    remaining_to_draw -= len(selected_problems)
                
                # 从当前轮抽正常宿舍
                if remaining_to_draw > 0:
                    normal_list = normal_available['宿舍号'].astype(str).tolist()
                    normal_list = [d for d in normal_list if d not in selected_dorms]
                    if normal_list:
                        to_draw_now = min(remaining_to_draw, len(normal_list))
                        selected_now = random.sample(normal_list, to_draw_now)
                        selected_dorms.extend(selected_now)
                        round_info.extend([current_round] * len(selected_now))
                        remaining_to_draw -= to_draw_now
                
                # 从新一轮补抽
                while remaining_to_draw > 0:
                    new_round = lottery_data[gender_choice]["当前轮次"] + 1
                    lottery_data[gender_choice]["当前轮次"] = new_round
                    
                    all_dorm_ids = gender_df['宿舍号'].astype(str).tolist()
                    new_round_dorms = [d for d in all_dorm_ids if d not in selected_dorms]
                    
                    if not new_round_dorms:
                        break
                    
                    to_draw_new = min(remaining_to_draw, len(new_round_dorms))
                    selected_new = random.sample(new_round_dorms, to_draw_new)
                    selected_dorms.extend(selected_new)
                    round_info.extend([new_round] * len(selected_new))
                    remaining_to_draw -= to_draw_new
                
                # 获取详情
                result_df = gender_df[gender_df['宿舍号'].astype(str).isin(selected_dorms)]
                detail_list = []
                for _, row in result_df.iterrows():
                    dorm_id = str(row['宿舍号'])
                    idx = selected_dorms.index(dorm_id)
                    detail = row.to_dict()
                    detail['轮次'] = round_info[idx]
                    detail_list.append(detail)
                
                result = {
                    "序号": len(lottery_data[gender_choice]["记录"]) + 1,
                    "时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "类型": gender_choice,
                    "抽取数量": len(selected_dorms),
                    "问题宿舍数": len([d for d in selected_dorms if d in problem_dorms]),
                    "来源": "系统抽取",
                    "涉及轮次": sorted(list(set(round_info))),
                    "宿舍列表": selected_dorms,
                    "详情": detail_list
                }
                
                # 更新轮次已抽取记录
                for i, dorm_id in enumerate(selected_dorms):
                    r = str(round_info[i])
                    if "轮次已抽取" not in lottery_data[gender_choice]:
                        lottery_data[gender_choice]["轮次已抽取"] = {}
                    if r not in lottery_data[gender_choice]["轮次已抽取"]:
                        lottery_data[gender_choice]["轮次已抽取"][r] = []
                    lottery_data[gender_choice]["轮次已抽取"][r].append(dorm_id)
                
                lottery_data[gender_choice]["记录"].append(result)
                
                # 保存到 GitHub
                if save_lottery_data(lottery_data):
                    st.success(f"✅ 抽取成功！已保存到云端，共 {len(selected_dorms)} 间")
                    st.rerun()
                else:
                    st.error("❌ 保存失败，请重试")
        
        if st.button("🗑️ 清空全部记录", type="secondary", use_container_width=True):
            lottery_data[gender_choice]["记录"] = []
            lottery_data[gender_choice]["当前轮次"] = 1
            lottery_data[gender_choice]["轮次已抽取"] = {}
            if save_lottery_data(lottery_data):
                st.success(f"✅ 已清空{gender_choice}宿舍全部记录")
                st.rerun()
        
        st.markdown("---")
        st.subheader("🔄 轮次管理")
        
        if st.button("🆕 手动开始新一轮", use_container_width=True):
            new_round = current_round + 1
            lottery_data[gender_choice]["当前轮次"] = new_round
            if save_lottery_data(lottery_data):
                st.success(f"✅ 已开始第 {new_round} 轮")
                st.rerun()
        
        st.caption(f"当前：第 {current_round} 轮 | 点击后进入新一轮，旧记录保留")
    
    st.markdown("---")
    st.subheader("📋 抽取记录")
    
    records = lottery_data[gender_choice]["记录"]
    if records:
        for i, record in enumerate(reversed(records)):
            record_index = len(records) - 1 - i
            source_icon = "📥" if record.get('来源') == "手动导入" else "🎲"
            rounds = record.get('涉及轮次', [1])
            rounds_str = "、".join([f"第{r}轮" for r in rounds])
            
            with st.expander(f"{source_icon} 第 {record['序号']} 次 - {record['时间']} | {record['抽取数量']}间（{rounds_str}）", expanded=(i==0)):
                detail_df = pd.DataFrame(record['详情'])
                
                if len(detail_df) > 0:
                    def mark_problem(row):
                        if str(row['宿舍号']) in problem_dorms:
                            return f"⚠️ {problem_dorms[str(row['宿舍号'])].get('问题类型', '未知')}"
                        return "✅ 正常"
                    detail_df['状态'] = detail_df.apply(mark_problem, axis=1)
                    
                    display_cols = ['宿舍号', '公寓号', '年级', '辅导员', '轮次', '状态']
                    display_cols = [c for c in display_cols if c in detail_df.columns]
                    st.dataframe(detail_df[display_cols], use_container_width=True, hide_index=True)
                    
                    col1, col2 = st.columns([1, 1])
                    with col1:
                        csv = detail_df.to_csv(index=False).encode('utf-8-sig')
                        st.download_button("📥 导出 CSV", csv, f"抽签结果_{gender_choice}_第{record['序号']}次.csv", "text/csv", key=f"exp_{record_index}")
                    with col2:
                        if st.button("🗑️ 删除此记录", key=f"del_{record_index}"):
                            for j, dorm_id in enumerate(record['宿舍列表']):
                                r = str(record['详情'][j].get('轮次', 1))
                                if r in lottery_data[gender_choice].get("轮次已抽取", {}):
                                    if dorm_id in lottery_data[gender_choice]["轮次已抽取"][r]:
                                        lottery_data[gender_choice]["轮次已抽取"][r].remove(dorm_id)
                            lottery_data[gender_choice]["记录"].pop(record_index)
                            if save_lottery_data(lottery_data):
                                st.success("✅ 已删除")
                                st.rerun()
    else:
        st.info("暂无抽取记录")

# ==================== 页面2：已抽签宿舍上传 ====================

elif page == "📤 已抽签宿舍上传":
    st.markdown('<div class="main-header">📤 已抽签宿舍上传</div>', unsafe_allow_html=True)
    
    if df is None:
        st.warning("⚠️ 请先在「上传宿舍清单」页面上传宿舍数据！")
        st.stop()
    
    st.markdown("### 📝 功能说明\n此功能用于导入历史已抽签记录，避免重复抽取。\n\n**格式要求：** 必需列 `宿舍号`，可选列 `抽取日期`")
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    with col1:
        male_drawn = sum(len(v) for v in lottery_data["男生"].get("轮次已抽取", {}).values())
        st.metric("男生已抽取", male_drawn, f"第{lottery_data['男生']['当前轮次']}轮")
    with col2:
        female_drawn = sum(len(v) for v in lottery_data["女生"].get("轮次已抽取", {}).values())
        st.metric("女生已抽取", female_drawn, f"第{lottery_data['女生']['当前轮次']}轮")
    
    st.markdown("---")
    st.subheader("📥 上传已抽签宿舍")
    
    uploaded = st.file_uploader("选择 Excel 文件", type=["xlsx", "xls"], key="upload_drawn")
    
    if uploaded:
        upload_df = pd.read_excel(uploaded)
        if '宿舍号' not in upload_df.columns:
            st.error("❌ 缺少「宿舍号」列！")
        else:
            upload_df['宿舍号'] = upload_df['宿舍号'].astype(str)
            st.dataframe(upload_df.head(5), use_container_width=True, hide_index=True)
            
            dorm_list = df.copy()
            dorm_list['宿舍号'] = dorm_list['宿舍号'].astype(str)
            
            matched, unmatched, already = [], [], []
            for _, row in upload_df.iterrows():
                dorm_id = row['宿舍号']
                match = dorm_list[dorm_list['宿舍号'] == dorm_id]
                if len(match) == 0:
                    unmatched.append(dorm_id)
                else:
                    info = match.iloc[0]
                    gender = "男生" if "男" in str(info['性别']) else "女生"
                    current_round = str(lottery_data[gender]["当前轮次"])
                    round_drawn = lottery_data[gender].get("轮次已抽取", {}).get(current_round, [])
                    if dorm_id in round_drawn:
                        already.append(dorm_id)
                    else:
                        matched.append((dorm_id, gender, info))
            
            st.write(f"✅ 可导入：{len(matched)} 间")
            st.write(f"⚠️ 已存在：{len(already)} 间")
            st.write(f"❌ 未匹配：{len(unmatched)} 间")
            
            if matched:
                if st.button("确认导入", type="primary"):
                    with st.spinner("正在保存到云端..."):
                        for dorm_id, gender, info in matched:
                            current_round = str(lottery_data[gender]["当前轮次"])
                            if "轮次已抽取" not in lottery_data[gender]:
                                lottery_data[gender]["轮次已抽取"] = {}
                            if current_round not in lottery_data[gender]["轮次已抽取"]:
                                lottery_data[gender]["轮次已抽取"][current_round] = []
                            lottery_data[gender]["轮次已抽取"][current_round].append(dorm_id)
                        
                        if save_lottery_data(lottery_data):
                            st.success(f"✅ 成功导入 {len(matched)} 条记录！")
                            st.rerun()

# ==================== 页面3：问题宿舍管理 ====================

elif page == "❓ 问题宿舍管理":
    st.markdown('<div class="main-header">❓ 问题宿舍管理</div>', unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["添加问题宿舍", "问题宿舍列表", "批量导入"])
    
    with tab1:
        st.subheader("添加单个问题宿舍")
        dorm_id = st.text_input("宿舍号：")
        problem_type = st.selectbox("问题类型：", ["卫生差", "违规电器", "设施损坏", "噪音扰民", "其他"])
        note = st.text_input("备注（可选）：")
        
        if st.button("添加", type="primary"):
            if dorm_id:
                problem_dorms[dorm_id] = {
                    "问题类型": problem_type,
                    "备注": note,
                    "添加时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "复查状态": "待复查"
                }
                if save_problem_dorms(problem_dorms):
                    st.success(f"✅ 已添加：{dorm_id}")
                    st.rerun()
            else:
                st.warning("请输入宿舍号")
    
    with tab2:
        st.subheader(f"问题宿舍列表（共 {len(problem_dorms)} 间）")
        if problem_dorms:
            for dorm_id, info in problem_dorms.items():
                with st.expander(f"🏠 {dorm_id} - {info.get('问题类型', '未知')}"):
                    col1, col2 = st.columns([2, 1])
                    with col1:
                        st.write(f"**问题类型：** {info.get('问题类型', '-')}")
                        st.write(f"**备注：** {info.get('备注', '-')}")
                        st.write(f"**添加时间：** {info.get('添加时间', '-')}")
                        status = info.get('复查状态', '待复查')
                        if status == "已合格":
                            st.success(f"**复查状态：** {status}")
                        else:
                            st.warning(f"**复查状态：** {status}")
                    with col2:
                        if st.button(f"✅ 标记合格", key=f"pass_{dorm_id}"):
                            problem_dorms[dorm_id]["复查状态"] = "已合格"
                            if save_problem_dorms(problem_dorms):
                                st.success("已标记为合格")
                                st.rerun()
                        if st.button(f"🗑️ 删除", key=f"del_{dorm_id}"):
                            del problem_dorms[dorm_id]
                            if save_problem_dorms(problem_dorms):
                                st.success("已删除")
                                st.rerun()
        else:
            st.info("暂无问题宿舍")
    
    with tab3:
        st.subheader("批量导入问题宿舍")
        st.write("上传 Excel 文件，必需列：宿舍号、问题类型")
        upload_file = st.file_uploader("选择文件", type=["xlsx", "xls"], key="upload_problem")
        if upload_file:
            upload_df = pd.read_excel(upload_file)
            if '宿舍号' not in upload_df.columns or '问题类型' not in upload_df.columns:
                st.error("❌ 缺少必需列！")
            else:
                st.dataframe(upload_df.head(5), use_container_width=True, hide_index=True)
                if st.button("确认导入", type="primary"):
                    with st.spinner("正在保存到云端..."):
                        count = 0
                        for _, row in upload_df.iterrows():
                            dorm_id = str(row['宿舍号'])
                            problem_dorms[dorm_id] = {
                                "问题类型": row['问题类型'],
                                "备注": row.get('备注', ''),
                                "添加时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "复查状态": "待复查"
                            }
                            count += 1
                        if save_problem_dorms(problem_dorms):
                            st.success(f"✅ 成功导入 {count} 条记录！")
                            st.rerun()

# ==================== 页面4：上传宿舍清单 ====================

elif page == "📄 上传宿舍清单":
    st.markdown('<div class="main-header">📄 上传宿舍清单</div>', unsafe_allow_html=True)
    
    st.warning("⚠️ 上传新清单将清空所有抽签记录！")
    
    uploaded_file = st.file_uploader("选择 Excel 文件", type=["xlsx", "xls"])
    
    if uploaded_file:
        new_df = pd.read_excel(uploaded_file)
        st.write("预览数据：")
        st.dataframe(new_df.head(10), use_container_width=True, hide_index=True)
        
        required_cols = ['宿舍号', '性别']
        missing = [c for c in required_cols if c not in new_df.columns]
        
        if missing:
            st.error(f"❌ 缺少必需列：{', '.join(missing)}")
        else:
            st.write(f"**总行数：** {len(new_df)}")
            st.write(f"**男生宿舍：** {len(new_df[new_df['性别'] == '男生公寓'])} 间")
            st.write(f"**女生宿舍：** {len(new_df[new_df['性别'] == '女生公寓'])} 间")
            
            if st.button("确认上传", type="primary"):
                with st.spinner("正在保存到云端..."):
                    # 清空抽签记录
                    lottery_data = {
                        "男生": {"记录": [], "当前轮次": 1, "轮次已抽取": {}},
                        "女生": {"记录": [], "当前轮次": 1, "轮次已抽取": {}}
                    }
                    if save_dorm_list(new_df) and save_lottery_data(lottery_data):
                        st.success("✅ 上传成功！抽签记录已清空。")
                        st.rerun()

# ==================== 页面5：数据统计 ====================

elif page == "📊 数据统计":
    st.markdown('<div class="main-header">📊 数据统计</div>', unsafe_allow_html=True)
    
    if df is None:
        st.warning("⚠️ 请先上传宿舍清单！")
        st.stop()
    
    tab1, tab2, tab3 = st.tabs(["抽签进度", "问题宿舍统计", "辅导员统计"])
    
    with tab1:
        st.subheader("抽签进度统计")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 👨 男生宿舍")
            male_total = len(df[df['性别'] == '男生公寓'])
            male_drawn = sum(len(v) for v in lottery_data["男生"].get("轮次已抽取", {}).values())
            male_round = lottery_data["男生"]["当前轮次"]
            male_records = len(lottery_data["男生"]["记录"])
            
            st.metric("总宿舍数", male_total)
            st.metric("已抽取", male_drawn)
            st.metric("当前轮次", f"第 {male_round} 轮")
            st.metric("抽取次数", male_records)
            st.progress(male_drawn / male_total if male_total > 0 else 0)
        
        with col2:
            st.markdown("#### 👩 女生宿舍")
            female_total = len(df[df['性别'] == '女生公寓'])
            female_drawn = sum(len(v) for v in lottery_data["女生"].get("轮次已抽取", {}).values())
            female_round = lottery_data["女生"]["当前轮次"]
            female_records = len(lottery_data["女生"]["记录"])
            
            st.metric("总宿舍数", female_total)
            st.metric("已抽取", female_drawn)
            st.metric("当前轮次", f"第 {female_round} 轮")
            st.metric("抽取次数", female_records)
            st.progress(female_drawn / female_total if female_total > 0 else 0)
    
    with tab2:
        st.subheader("问题宿舍统计")
        if problem_dorms:
            type_count = {}
            status_count = {"待复查": 0, "已合格": 0}
            for info in problem_dorms.values():
                t = info.get('问题类型', '未知')
                type_count[t] = type_count.get(t, 0) + 1
                s = info.get('复查状态', '待复查')
                status_count[s] = status_count.get(s, 0) + 1
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**按类型：**")
                for t, c in type_count.items():
                    st.write(f"- {t}：{c} 间")
            with col2:
                st.markdown("**按状态：**")
                for s, c in status_count.items():
                    st.write(f"- {s}：{c} 间")
        else:
            st.info("暂无问题宿舍")
    
    with tab3:
        st.subheader("辅导员被抽中统计")
        
        all_records = lottery_data["男生"]["记录"] + lottery_data["女生"]["记录"]
        counselor_count = {}
        
        for record in all_records:
            for detail in record.get("详情", []):
                counselor = detail.get("辅导员", "未知")
                counselor_count[counselor] = counselor_count.get(counselor, 0) + 1
        
        if counselor_count:
            sorted_counselors = sorted(counselor_count.items(), key=lambda x: x[1], reverse=True)
            stat_df = pd.DataFrame(sorted_counselors, columns=["辅导员", "被抽中次数"])
            st.dataframe(stat_df, use_container_width=True, hide_index=True)
        else:
            st.info("暂无数据")
