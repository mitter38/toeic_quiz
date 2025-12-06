import streamlit as st
import pandas as pd
import random
import os

# ==========================================
# 設定：ページの基本設定
# ==========================================
st.set_page_config(
    page_title="単語クイズアプリ",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# スタイル調整：ボタンを少し大きく見やすくするCSS（おまけ）
st.markdown("""
<style>
div.stButton > button {
    height: 3em;
    font-size: 20px;
    font-weight: bold;
}
</style>
""", unsafe_allow_html=True)

# ファイルパス設定
BASE_DIR = os.getcwd()

# コースとファイル名の対応表
QUIZ_FILES = {
    "TOEIC 上級 (800-990点)": "toeic_words.xlsx",
    "TOEIC 復習モード": "toeic_words.xlsx"
}

# ==========================================
# 関数定義
# ==========================================
@st.cache_data
def load_data(filename):
    """Excelデータを読み込む関数"""
    file_path = os.path.join(BASE_DIR, filename)
    if not os.path.exists(file_path):
        return None
    try:
        df = pd.read_excel(file_path, engine='openpyxl')
        if 'Word' not in df.columns or 'Meaning' not in df.columns:
            return None
        df = df.dropna(subset=['Word', 'Meaning'])
        return dict(zip(df['Word'], df['Meaning']))
    except Exception:
        return None

def initialize_quiz(course_name, num_questions=10):
    """選択されたコースでクイズを初期化する"""
    filename = QUIZ_FILES[course_name]
    word_data = load_data(filename)
    
    if not word_data:
        st.error(f"エラー: データファイル（{filename}）の読み込みに失敗しました。")
        return False

    if len(word_data) < 4:
        st.error("データが不足しています。最低4単語必要です。")
        return False

    words = list(word_data.keys())
    actual_num = min(num_questions, len(words))
    
    st.session_state.quiz_data = {
        'course_name': course_name,
        'words_dict': word_data,
        'question_words': random.sample(words, actual_num),
        'total_questions': actual_num
    }
    st.session_state.current_index = 0
    st.session_state.score = 0
    st.session_state.quiz_finished = False
    st.session_state.current_choices = None
    st.session_state.last_result = None
    
    return True

def check_answer(selected_meaning):
    """回答チェック処理"""
    q_word = st.session_state.quiz_data['question_words'][st.session_state.current_index]
    correct_meaning = st.session_state.quiz_data['words_dict'][q_word]
    
    if selected_meaning == correct_meaning:
        st.session_state.score += 1
        st.session_state.last_result = ("✅ 正解！", "success")
    else:
        st.session_state.last_result = (f"❌ 不正解... (正解は「{correct_meaning}」)", "error")
        
    st.session_state.current_index += 1
    st.session_state.current_choices = None
    
    if st.session_state.current_index >= st.session_state.quiz_data['total_questions']:
        st.session_state.quiz_finished = True

def go_to_menu():
    """メニュー画面に戻る"""
    st.session_state.page = "menu"
    if 'quiz_data' in st.session_state:
        del st.session_state['quiz_data']

# ==========================================
# メイン処理
# ==========================================

if 'page' not in st.session_state:
    st.session_state.page = "menu"

# --- 画面1: メニュー画面 ---
if st.session_state.page == "menu":
    st.title("単語クイズ 📚")
    st.write("コースを選んでスタート！")

    # 問題数設定（アコーディオンに隠してスッキリさせる）
    with st.expander("⚙️ オプション設定（問題数など）"):
        num_q = st.slider("1回の問題数", min_value=5, max_value=20, value=10)
    
    st
