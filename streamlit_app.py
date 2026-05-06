"""
宿舍抽签系统 V3.2
作者：凯迪
功能：男女生分开抽取、问题宿舍管理、单次记录删除、已抽签宿舍上传、多轮抽签
更新：支持跨轮抽取，剩余不足时自动从新一轮补抽
"""

import streamlit as st
import pandas as pd
import random
import os
from datetime import datetime
import json
import io

# ==================== 配置 ====================
st.set_page_config(
    page_title="宿舍抽签系统 V3.2",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 数据路径（云端部署版）
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DATA_FILE = os.path.join(DATA_DIR, "lottery_data_v3.json")
DORM_FILE = os.path.join(DATA_DIR, "dorm_list.xlsx")
PROBLEM_FILE = os.path.join(DATA_DIR, "problem_dorms.json")

os.makedirs(DATA_DIR, exist_ok=True)

# ==================== 数据加载/保存函数 ====================

def load_lottery_data():
    """加载抽签数据"""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # 兼容旧数据，添加轮次字段
            for gender in ["男生", "女生"]:
                if "当前轮次" not in data[gender]:
                    data[gender]["当前轮次"] = 1
                if "轮次已抽取" not in data[gender]:
                    # 迁移旧数据：将已抽取放入第1轮
                    old_drawn = data[gender].get("已抽取", [])
                    data[gender]["轮次已抽取"] = {"1": old_drawn}
            return data
    return {
        "男生": {"记录": [], "当前轮次": 1, "轮次已抽取": {}},
        "女生": {"记录": [], "当前轮次": 1, "轮次已抽取": {}}
    }

def save_lottery_data(data):
    """保存抽签数据"""
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_problem_dorms():
    """加载问题宿舍数据"""
    if os.path.exists(PROBLEM_FILE):
        with open(PROBLEM_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_problem_dorms(data):
    """保存问题宿舍数据"""
    with open(PROBLEM_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_dorm_list():
    """加载宿舍清单"""
    if os.path.exists(DORM_FILE):
        return pd.read_excel(DORM_FILE)
    return None

def save_dorm_list(df):
    """保存宿舍清单"""
    df.to_excel(DORM_FILE, index=False)

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
</style>
""", unsafe_allow_html=True)

# ==================== 侧边栏 ====================

st.sidebar.title("🏠 宿舍抽签系统")
st.sidebar.caption("V3.2 - 多轮抽签版")

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
            
            # 从新一轮补抽（新一轮可以重新抽取所有宿舍）
            while remaining_to_draw > 0:
                # 进入新一轮
                new_round = lottery_data[gender_choice]["当前轮次"] + 1
                lottery_data[gender_choice]["当前轮次"] = new_round
                
                # 新一轮所有宿舍都可抽取（排除本轮已抽的）
                all_dorm_ids = gender_df['宿舍号'].astype(str).tolist()
                new_round_dorms = [d for d in all_dorm_ids if d not in selected_dorms]
                
                if not new_round_dorms:
                    break  # 没有更多宿舍可抽
                
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
            save_lottery_data(lottery_data)
            
            rounds_str = "、".join([f"第{r}轮" for r in result['涉及轮次']])
            st.success(f"✅ 抽取成功！共 {len(selected_dorms)} 间（{rounds_str}）")
            st.rerun()
        
        if st.button("🗑️ 清空全部记录", type="secondary", use_container_width=True):
            lottery_data[gender_choice]["记录"] = []
            lottery_data[gender_choice]["当前轮次"] = 1
            lottery_data[gender_choice]["轮次已抽取"] = {}
            save_lottery_data(lottery_data)
            st.success(f"✅ 已清空{gender_choice}宿舍全部记录，重置为第1轮")
            st.rerun()
        
        st.markdown("---")
        st.subheader("🔄 轮次管理")
        
        if st.button("🆕 手动开始新一轮", use_container_width=True):
            new_round = current_round + 1
            lottery_data[gender_choice]["当前轮次"] = new_round
            save_lottery_data(lottery_data)
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
                            # 从轮次已抽取中删除
                            for i, dorm_id in enumerate(record['宿舍列表']):
                                r = str(record['详情'][i].get('轮次', 1))
                                if r in lottery_data[gender_choice].get("轮次已抽取", {}):
                                    if dorm_id in lottery_data[gender_choice]["轮次已抽取"][r]:
                                        lottery_data[gender_choice]["轮次已抽取"][r].remove(dorm_id)
                            lottery_data[gender_choice]["记录"].pop(record_index)
                            save_lottery_data(lottery_data)
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
                    # 检查是否在当前轮已抽取
                    current_round = str(lottery_data[gender]["当前轮次"])
                    round_drawn = lottery_data[gender].get("轮次已抽取", {}).get(current_round, [])
                    if dorm_id in round_drawn:
                        already.append(dorm_id)
                    else:
                        matched.append({'宿舍号': dorm_id, '性别': gender, '公寓号': info.get('公寓号', ''), '年级': info.get('年级', ''), '辅导员': info.get('辅导员', ''), '抽取日期': row.get('抽取日期', datetime.now().strftime("%Y-%m-%d"))})
            
            col1, col2, col3 = st.columns(3)
            col1.metric("✅ 可导入", len(matched))
            col2.metric("⚠️ 已存在", len(already))
            col3.metric("❌ 未匹配", len(unmatched))
            
            if matched:
                male_imp = [d for d in matched if d['性别'] == '男生']
                female_imp = [d for d in matched if d['性别'] == '女生']
                
                if st.button("💾 确认导入", type="primary"):
                    if male_imp:
                        current_round = str(lottery_data["男生"]["当前轮次"])
                        if "轮次已抽取" not in lottery_data["男生"]:
                            lottery_data["男生"]["轮次已抽取"] = {}
                        if current_round not in lottery_data["男生"]["轮次已抽取"]:
                            lottery_data["男生"]["轮次已抽取"][current_round] = []
                        lottery_data["男生"]["轮次已抽取"][current_round].extend([d['宿舍号'] for d in male_imp])
                        lottery_data["男生"]["记录"].append({"序号": len(lottery_data["男生"]["记录"]) + 1, "时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "类型": "男生", "抽取数量": len(male_imp), "问题宿舍数": 0, "来源": "手动导入", "涉及轮次": [int(current_round)], "宿舍列表": [d['宿舍号'] for d in male_imp], "详情": male_imp})
                    if female_imp:
                        current_round = str(lottery_data["女生"]["当前轮次"])
                        if "轮次已抽取" not in lottery_data["女生"]:
                            lottery_data["女生"]["轮次已抽取"] = {}
                        if current_round not in lottery_data["女生"]["轮次已抽取"]:
                            lottery_data["女生"]["轮次已抽取"][current_round] = []
                        lottery_data["女生"]["轮次已抽取"][current_round].extend([d['宿舍号'] for d in female_imp])
                        lottery_data["女生"]["记录"].append({"序号": len(lottery_data["女生"]["记录"]) + 1, "时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "类型": "女生", "抽取数量": len(female_imp), "问题宿舍数": 0, "来源": "手动导入", "涉及轮次": [int(current_round)], "宿舍列表": [d['宿舍号'] for d in female_imp], "详情": female_imp})
                    save_lottery_data(lottery_data)
                    st.success(f"✅ 成功导入 {len(matched)} 间！")
                    st.rerun()
    
    st.markdown("---")
    st.subheader("📄 模板下载")
    if st.button("📥 下载导入模板"):
        template = pd.DataFrame({'宿舍号': ['21401', '21402'], '抽取日期': ['2026-04-15', '2026-04-16']})
        buf = io.BytesIO()
        template.to_excel(buf, index=False)
        buf.seek(0)
        st.download_button("📥 点击下载模板.xlsx", buf, "已抽签宿舍导入模板.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ==================== 页面3：问题宿舍管理 ====================

elif page == "❓ 问题宿舍管理":
    st.markdown('<div class="main-header">❓ 问题宿舍管理</div>', unsafe_allow_html=True)
    
    if df is None:
        st.warning("⚠️ 请先上传宿舍清单！")
        st.stop()
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("➕ 添加问题宿舍")
        dorm_options = df['宿舍号'].astype(str).tolist()
        selected = st.selectbox("选择宿舍：", [""] + dorm_options)
        
        if selected:
            info = df[df['宿舍号'].astype(str) == selected].iloc[0]
            st.info(f"宿舍信息：{info['公寓号']} | {info['性别']} | {info['年级']} | 辅导员：{info['辅导员']}")
            ptype = st.selectbox("问题类型：", ["卫生差", "违规电器", "设施损坏", "噪音扰民", "其他"])
            pdesc = st.text_area("问题描述：")
            
            if st.button("➕ 添加", type="primary"):
                problem_dorms[selected] = {"问题类型": ptype, "问题描述": pdesc, "发现日期": datetime.now().strftime("%Y-%m-%d"), "复查状态": "待复查", "复查次数": 0}
                save_problem_dorms(problem_dorms)
                st.success(f"✅ 已添加 {selected}")
                st.rerun()
    
    with col2:
        st.subheader("📋 问题宿舍列表")
        if problem_dorms:
            for dorm_id, info in list(problem_dorms.items()):
                row = df[df['宿舍号'].astype(str) == dorm_id]
                if len(row) > 0:
                    col_a, col_b = st.columns([3, 1])
                    with col_a:
                        st.write(f"**{dorm_id}** | {info['问题类型']} | {info['发现日期']}")
                    with col_b:
                        status = info.get('复查状态', '待复查')
                        st.success(f"✅ {status}") if status == "已合格" else st.warning(f"⚠️ {status}")
                    
                    if st.button(f"✅ 标记合格", key=f"pass_{dorm_id}"):
                        problem_dorms[dorm_id]["复查状态"] = "已合格"
                        problem_dorms[dorm_id]["复查日期"] = datetime.now().strftime("%Y-%m-%d")
                        save_problem_dorms(problem_dorms)
                        st.rerun()
                    st.markdown("---")
        else:
            st.info("暂无问题宿舍")

# ==================== 页面4：上传宿舍清单 ====================

elif page == "📄 上传宿舍清单":
    st.markdown('<div class="main-header">📄 上传宿舍清单</div>', unsafe_allow_html=True)
    
    if df is not None:
        st.subheader("📊 当前宿舍数据")
        st.dataframe(df.head(10), use_container_width=True, hide_index=True)
        st.info(f"共 {len(df)} 条记录")
    
    st.markdown("---")
    st.subheader("📥 上传新宿舍清单")
    
    uploaded = st.file_uploader("选择 Excel 文件", type=["xlsx", "xls"])
    if uploaded:
        new_df = pd.read_excel(uploaded)
        if '宿舍号' not in new_df.columns or '性别' not in new_df.columns:
            st.error("❌ 缺少必需列：宿舍号、性别")
        else:
            st.success(f"✅ 格式正确，共 {len(new_df)} 条")
            st.dataframe(new_df.head(5), use_container_width=True, hide_index=True)
            
            if st.button("💾 确认上传", type="primary"):
                save_dorm_list(new_df)
                lottery_data["男生"] = {"记录": [], "当前轮次": 1, "轮次已抽取": {}}
                lottery_data["女生"] = {"记录": [], "当前轮次": 1, "轮次已抽取": {}}
                save_lottery_data(lottery_data)
                st.success("✅ 上传成功！记录已清空。")
                st.rerun()

# ==================== 页面5：数据统计 ====================

elif page == "📊 数据统计":
    st.markdown('<div class="main-header">📊 数据统计</div>', unsafe_allow_html=True)
    
    if df is None:
        st.warning("⚠️ 请先上传宿舍清单！")
        st.stop()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📈 抽签进度")
        for gender in ["男生", "女生"]:
            gtext = "男生公寓" if gender == "男生" else "女生公寓"
            total = len(df[df['性别'] == gtext])
            drawn = sum(len(v) for v in lottery_data[gender].get("轮次已抽取", {}).values())
            rnd = lottery_data[gender]["当前轮次"]
            pct = drawn / total * 100 if total > 0 else 0
            st.metric(f"{gender}宿舍", f"{drawn}/{total}", f"第{rnd}轮 | {pct:.1f}%")
            st.progress(int(pct))
    
    with col2:
        st.subheader("❓ 问题宿舍统计")
        if problem_dorms:
            types = {}
            for info in problem_dorms.values():
                t = info.get('问题类型', '其他')
                types[t] = types.get(t, 0) + 1
            for t, c in types.items():
                st.write(f"- **{t}**：{c} 间")
            pending = sum(1 for i in problem_dorms.values() if i.get('复查状态') != '已合格')
            st.write(f"\n⏳ 待复查：{pending} 间")
        else:
            st.info("暂无问题宿舍")
    
    st.markdown("---")
    st.subheader("👨‍🏫 辅导员统计")
    
    stats = {}
    for gender in ["男生", "女生"]:
        for rec in lottery_data[gender]["记录"]:
            for d in rec.get("详情", []):
                c = d.get("辅导员", "未知")
                stats[c] = stats.get(c, 0) + 1
    
    if stats:
        stats_df = pd.DataFrame([{"辅导员": k, "被抽中次数": v} for k, v in stats.items()]).sort_values("被抽中次数", ascending=False)
        st.dataframe(stats_df, use_container_width=True, hide_index=True)
    else:
        st.info("暂无记录")

# ==================== 底部 ====================

st.sidebar.markdown("---")
st.sidebar.caption("💡 提示：男生和女生的抽签记录独立保存")
st.sidebar.caption(f"📅 最后更新：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
