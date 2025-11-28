import streamlit as st
import json
import random
import os
import pandas as pd

# --- 配置 ---
DATA_FILE = 'questions.json'

# --- 1. 数据管理函数 ---
def load_data():
    """读取题库"""
    if not os.path.exists(DATA_FILE):
        st.error(f"❌ 找不到 {DATA_FILE}，请先运行之前的转换脚本生成题库！")
        return []
    
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 初始化字段
    for q in data:
        if 'stats' not in q:
            q['stats'] = {'attempts': 0, 'correct': 0, 'wrong': 0}
        if 'favorite' not in q:
            q['favorite'] = False 
            
    return data

def save_data(data):
    """保存数据"""
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def reset_stats():
    """重置统计"""
    for q in st.session_state['data']:
        q['stats'] = {'attempts': 0, 'correct': 0, 'wrong': 0}
    save_data(st.session_state['data'])
    st.toast("🧹 所有做题记录已清空！", icon="✅")
    st.rerun()

# 辅助函数：根据ID找索引
def find_index_by_id(data, target_id):
    for i, q in enumerate(data):
        if q['id'] == target_id:
            return i
    return 0

# --- 2. 核心逻辑 ---
def get_next_question(mode):
    """获取下一题"""
    data = st.session_state['data']
    
    if mode == "顺序练习":
        current_idx = st.session_state.get('current_q_index', 0)
        next_idx = (current_idx + 1) % len(data)
        return next_idx
        
    elif mode == "随机刷题":
        return random.randint(0, len(data) - 1)
        
    elif mode == "错题攻坚 (智能推荐)":
        candidates = [i for i, q in enumerate(data) if q['stats']['wrong'] > 0 or q['stats']['attempts'] == 0]
        if not candidates:
            return -1 
        return random.choice(candidates)
    
    elif mode == "❤️ 收藏夹练习":
        candidates = [i for i, q in enumerate(data) if q.get('favorite', False)]
        if not candidates:
            return -2
        return random.choice(candidates)

# --- 3. 界面初始化 ---
st.set_page_config(page_title="FK9820", page_icon="🎓", layout="wide")

if 'data' not in st.session_state:
    st.session_state['data'] = load_data()
if 'current_q_index' not in st.session_state:
    st.session_state['current_q_index'] = 0
if 'user_answer' not in st.session_state:
    st.session_state['user_answer'] = None
if 'submitted' not in st.session_state:
    st.session_state['submitted'] = False

# ⚠️ 关键修复：使用专门的变量来控制当前页面，而不是依赖 widget key
if 'current_page' not in st.session_state:
    st.session_state['current_page'] = "📝 开始刷题"

# --- 4. 侧边栏 ---
with st.sidebar:
    st.title("🧩 功能导航")
    
    # 定义页面选项
    page_options = ["📝 开始刷题", "🏆 错题排行榜"]
    
    # ⚠️ 关键修复：根据 state 决定 index，从而避免报错
    try:
        current_index = page_options.index(st.session_state['current_page'])
    except ValueError:
        current_index = 0
        
    # 这里不要加 key="nav_page"，而是通过 index 控制
    selected_page = st.radio("前往页面", page_options, index=current_index)
    
    # 如果用户手动点击了导航栏，更新状态
    if selected_page != st.session_state['current_page']:
        st.session_state['current_page'] = selected_page
        st.rerun()

    st.markdown("---")
    
    if st.session_state['current_page'] == "📝 开始刷题":
        st.subheader("⚙️ 刷题设置")
        mode = st.selectbox("选择模式", ["顺序练习", "随机刷题", "错题攻坚 (智能推荐)", "❤️ 收藏夹练习"])
        
        data = st.session_state['data']
        total_attempts = sum(q['stats']['attempts'] for q in data)
        fav_count = sum(1 for q in data if q.get('favorite', False))
        
        st.info(f"📊 已刷: {total_attempts} 题 | ❤️ 收藏: {fav_count} 题")
        
        if st.button("跳过此题 / 下一题"):
            new_idx = get_next_question(mode)
            if new_idx == -1:
                st.warning("🎉 没有错题了！")
            elif new_idx == -2:
                st.warning("📭 收藏夹是空的！")
            else:
                st.session_state['current_q_index'] = new_idx
                st.session_state['submitted'] = False
                st.rerun()

    st.markdown("---")
    st.subheader("🗑️ 数据管理")
    if st.button("⚠️ 重置所有进度(统计清零)"):
        reset_stats()

# --- 5. 主页面逻辑 ---

# ========== 页面 A: 错题排行榜 (修复版) ========== 
if st.session_state['current_page'] == "🏆 错题排行榜":
    st.title("🏆 错题排行榜 (Top 50)")
    st.caption("💡 操作提示：点击表格中任意一行（或点击 **➡️ 练习**），即可跳转到该题目！")
    
    raw_data = []
    for q in st.session_state['data']:
        stats = q['stats']
        if stats['attempts'] > 0:
            acc = (stats['correct'] / stats['attempts'] * 100)
            raw_data.append({
                "ID": q['id'],
                "题目片段": q['question'][:50] + "..." if len(q['question']) > 50 else q['question'],
                "❌ 错误次数": stats['wrong'],
                "✅ 正确次数": stats['correct'],
                "📉 错误率": f"{100-acc:.1f}%",
                "总尝试": stats['attempts'],
                "➡️ 操作": "➡️ 练习" # 新增一列，视觉上像按钮
            })
    
    if raw_data:
        df = pd.DataFrame(raw_data)
        df_sorted = df.sort_values(by="❌ 错误次数", ascending=False).head(50)
        max_wrong_val = int(df['❌ 错误次数'].max()) if not df.empty else 10

        # --- 表格交互逻辑 ---
        event = st.dataframe(
            df_sorted, 
            column_config={
                "ID": st.column_config.NumberColumn(format="%d", width="small"),
                "题目片段": st.column_config.TextColumn(width="large"),
                "❌ 错误次数": st.column_config.ProgressColumn(
                    "❌ 错误热度", format="%d", min_value=0, max_value=max_wrong_val
                ),
                "➡️ 操作": st.column_config.TextColumn("跳转", width="small")
            },
            use_container_width=True,
            hide_index=True,
            on_select="rerun",  # 选中后刷新
            selection_mode="single-row"
        )

        # 捕获选中事件
        if len(event.selection.rows) > 0:
            selected_row_index = event.selection.rows[0]
            selected_id = int(df_sorted.iloc[selected_row_index]["ID"])
            
            # 查找真实索引
            real_index = find_index_by_id(st.session_state['data'], selected_id)
            
            # 执行跳转：修改状态变量，而不是修改 widget key
            st.session_state['current_q_index'] = real_index
            st.session_state['submitted'] = False
            st.session_state['current_page'] = "📝 开始刷题" # 切换页面变量
            st.rerun() # 立即重跑，侧边栏会自动根据变量更新
            
    else:
        st.info("暂无做题数据，快去练习吧！")

# ========== 页面 B: 刷题界面 ========== 
elif st.session_state['current_page'] == "📝 开始刷题":
    
    # 样式注入：加大字体
    st.markdown("""
    <style>
        .big-question {
            font-size: 24px !important;
            font-weight: bold;
            line-height: 1.5;
            margin-bottom: 20px;
            color: #FAFAFA;
        }
        .stRadio p {
            font-size: 20px !important;
            line-height: 1.6;
        }
        .stAlert p {
            font-size: 18px !important;
        }
        button p {
            font-size: 18px !important;
            font-weight: 600 !important;
        }
    </style>
    """, unsafe_allow_html=True)

    # 居中布局
    _, col_center, _ = st.columns([1, 2, 1])
    
    with col_center:
        st.markdown("<br><br>", unsafe_allow_html=True)

        q_idx = st.session_state['current_q_index']
        if q_idx >= len(st.session_state['data']):
            q_idx = 0
            st.session_state['current_q_index'] = 0

        question = st.session_state['data'][q_idx]
        
        col_title, col_fav = st.columns([8, 2])
        with col_title:
            st.subheader(f"第 {question['id']} 题")
        with col_fav:
            is_fav = question.get('favorite', False)
            if st.button("💔 取消" if is_fav else "❤️ 收藏", 
                         type="secondary" if is_fav else "primary", key=f"fav_{q_idx}"):
                question['favorite'] = not is_fav
                save_data(st.session_state['data'])
                st.rerun()

        st.markdown(f'<div class="big-question">{question["question"]}</div>', unsafe_allow_html=True)
        
        options_map = {}
        for opt in ['A', 'B', 'C', 'D', 'E']:
            key = f"option_{opt}"
            if key in question and question[key]:
                options_map[opt] = f"{opt}. {question[key]}"
        
        selection = st.radio(
            "你的选择:", 
            options=list(options_map.keys()), 
            format_func=lambda x: options_map[x], 
            index=None,
            key="radio_selection",
            disabled=st.session_state['submitted']
        )
        
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("提交答案", type="primary", disabled=st.session_state['submitted'], use_container_width=True):
            if not selection:
                st.toast("请先选择一个选项！", icon="⚠️")
            else:
                st.session_state['submitted'] = True
                
                is_correct = (selection == question['answer'])
                question['stats']['attempts'] += 1
                if is_correct:
                    question['stats']['correct'] += 1
                else:
                    question['stats']['wrong'] += 1
                
                save_data(st.session_state['data'])
                st.rerun()

        if st.session_state['submitted']:
            st.markdown("---")
            user_choice = st.session_state.radio_selection
            correct_choice = question['answer']
            
            if user_choice == correct_choice:
                st.success(f"🎉 回答正确！")
            else:
                st.error(f"💥 回答错误！ 正确答案是：【 {correct_choice} 】")
                
            if question.get('note'):
                st.info(f"💡 **解析/备注**: {question['note']}")
                
            if st.button("下一题 ➡️", type="primary", use_container_width=True):
                new_idx = get_next_question(mode)
                if new_idx == -1:
                    st.balloons()
                    st.success("恭喜！错题已清空！")
                    st.session_state['current_q_index'] = random.randint(0, len(st.session_state['data'])-1)
                elif new_idx == -2:
                    st.warning("收藏夹为空！")
                else:
                    st.session_state['current_q_index'] = new_idx
                    st.session_state['submitted'] = False
                    st.rerun()