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
    "TOEIC 黒フレ": "toeic_words.xlsx",
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

def is_similar(str1, str2, threshold=0.4):
    """
    2つの文字列が似ているか判定する関数
    threshold: 類似度のしきい値（0.0〜1.0）。数値が高いほど「激似」じゃないと弾かない。
    0.4くらいが「漢字が部分的に被っている」のを弾くのに丁度よい。
    """
    # 完全に一致する場合は「似ている」とする
    if str1 == str2:
        return True
    
    # SequenceMatcherで類似度(0.0~1.0)を計算
    similarity = difflib.SequenceMatcher(None, str(str1), str(str2)).ratio()
    return similarity > threshold

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
    st.title("単語クイズ for TOEIC 📚")
    st.write("コースを選んでスタート！")

    # 問題数設定（アコーディオンに隠してスッキリさせる）
    with st.expander("⚙️ オプション設定"):
        num_q = st.slider("1回の問題数", min_value=5, max_value=50, value=10)
    
    st.markdown("---") # 区切り線

    # コースボタンを生成して配置
    # 辞書(QUIZ_FILES)にあるコースの分だけボタンを作ります
    for course_name in QUIZ_FILES.keys():
        # type="primary" で目立つ色に、use_container_width=True で横幅いっぱいに
        if st.button(course_name, type="primary", use_container_width=True):
            # ボタンが押されたらそのコースで開始
            if initialize_quiz(course_name, num_q):
                st.session_state.page = "quiz"
                st.rerun()
        
        st.write("") # ボタン間の隙間

# --- 画面2: クイズ画面 ---
elif st.session_state.page == "quiz":
    
    if 'quiz_data' not in st.session_state:
        st.session_state.page = "menu"
        st.rerun()

    # ヘッダー
    col1, col2 = st.columns([3, 1])
    with col1:
        st.caption(f"挑戦中: {st.session_state.quiz_data['course_name']}")
    with col2:
        if st.button("中断", key="back_btn"):
            go_to_menu()
            st.rerun()

    # 結果発表
    if st.session_state.quiz_finished:
        st.balloons()
        st.header("🎉 結果発表 🎉")
        
        score = st.session_state.score
        total = st.session_state.quiz_data['total_questions']
        percentage = score / total * 100
        
        st.metric(label="スコア", value=f"{score} / {total}", delta=f"{percentage:.0f}%")
        
        if percentage == 100:
            st.success("Perfect! 完璧です！")
        elif percentage >= 80:
            st.info("Excellent! すごい！")
        else:
            st.warning("Keep going! 復習しましょう。")
            
        st.write("")
        if st.button("メニューに戻る 🏠", type="primary", use_container_width=True):
            go_to_menu()
            st.rerun()
            
    # 出題中
    else:
        # 正誤表示
        if st.session_state.last_result:
            msg, type_ = st.session_state.last_result
            if type_ == "success":
                st.success(msg)
            else:
                st.error(msg)
            st.session_state.last_result = None

        # 問題表示
        current_idx = st.session_state.current_index
        total_q = st.session_state.quiz_data['total_questions']
        q_word = st.session_state.quiz_data['question_words'][current_idx]
        correct_meaning = st.session_state.quiz_data['words_dict'][q_word]

        st.progress((current_idx) / total_q)
        st.markdown(f"### Q{current_idx + 1}.  **{q_word}**")

        # --- ★自動選別ロジック、意味が似ている単語を選択肢からはじく---
        if st.session_state.current_choices is None:
            all_meanings = list(st.session_state.quiz_data['words_dict'].values())
            
            # 誤答候補を入れるリスト
            distractors = []
            
            # 全単語リストをシャッフルして、一つずつチェックしていく
            random.shuffle(all_meanings)
            
            for candidate in all_meanings:
                # 誤答が3つ集まったら終了
                if len(distractors) >= 3:
                    break
                
                # チェック1: 正解そのものではないか？
                if candidate == correct_meaning:
                    continue
                
                # チェック2: 正解と日本語が似すぎていないか？
                if is_similar(candidate, correct_meaning, threshold=0.4):
                    continue # 似ているのでスキップ
                
                # チェック3: すでに選んだ誤答と似すぎていないか？（選択肢同士の被り防止）
                is_duplicate = False
                for existing_distractor in distractors:
                    if is_similar(candidate, existing_distractor, threshold=0.4):
                        is_duplicate = True
                        break
                if is_duplicate:
                    continue
                
                # 合格したものを採用
                distractors.append(candidate)
            
            # 万が一、厳しすぎて候補が足りない場合の安全策（ランダムで埋める）
            while len(distractors) < 3:
                m = random.choice(all_meanings)
                if m != correct_meaning and m not in distractors:
                    distractors.append(m)

            choices = distractors
            choices.append(correct_meaning)
            random.shuffle(choices)
            st.session_state.current_choices = choices

        # ボタン表示
        choices = st.session_state.current_choices
        for choice in choices:
            if st.button(choice, use_container_width=True):
                check_answer(choice)
                st.rerun()
