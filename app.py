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

# ファイルパス設定（カレントディレクトリ基準）
BASE_DIR = os.getcwd()

# ★ポイント1: コースとファイル名の対応表
# 将来ファイルを増やしたい時は、この辞書に追加するだけでOKです
# 今回は例として、同じファイルを指す2つのコースを作っています
QUIZ_FILES = {
    "TOEIC 黒フレ": "toeic_words.xlsx",
    "TOEIC 復習モード (テスト用)": "toeic_words.xlsx" 
}

# ==========================================
# 関数定義
# ==========================================
@st.cache_data
def load_data(filename):
    """Excelデータを読み込む関数"""
    file_path = os.path.join(BASE_DIR, filename)
    
    if not os.path.exists(file_path):
        return None # エラーハンドリングは呼び出し元で行う

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
        return False # 初期化失敗

    if len(word_data) < 4:
        st.error("データが不足しています。最低4単語必要です。")
        return False

    words = list(word_data.keys())
    actual_num = min(num_questions, len(words))
    
    # セッションステートにクイズデータを保存
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
    
    return True # 初期化成功

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
    # クイズデータはクリアしても良いし、残しておいても良いですが今回はリセット
    if 'quiz_data' in st.session_state:
        del st.session_state['quiz_data']

# ==========================================
# メイン処理 (画面分岐)
# ==========================================

# アプリ起動時に「現在のページ」変数がなければ作成
if 'page' not in st.session_state:
    st.session_state.page = "menu"

# --- 画面1: メニュー画面 ---
if st.session_state.page == "menu":
    st.title("単語クイズ 📚")
    st.write("挑戦するコースを選んでください。")

    # コース選択（ラジオボタン）
    selected_course = st.radio(
        "コース選択:",
        list(QUIZ_FILES.keys())
    )

    # 問題数選択（おまけ機能）
    num_q = st.slider("問題数", min_value=5, max_value=20, value=10)

    st.write("") # 空白
    
    # スタートボタン
    if st.button("クイズスタート 🚀", type="primary", use_container_width=True):
        # 初期化が成功したらページを移動
        if initialize_quiz(selected_course, num_q):
            st.session_state.page = "quiz"
            st.rerun()

# --- 画面2: クイズ画面 ---
elif st.session_state.page == "quiz":
    
    # もしデータがない状態でここに来たらメニューに戻す（リロード対策）
    if 'quiz_data' not in st.session_state:
        st.session_state.page = "menu"
        st.rerun()

    # ヘッダー（メニューに戻るボタン付き）
    col1, col2 = st.columns([3, 1])
    with col1:
        st.caption(f"コース: {st.session_state.quiz_data['course_name']}")
    with col2:
        if st.button("中断して戻る", key="back_btn"):
            go_to_menu()
            st.rerun()

    # --- クイズ終了時の表示 ---
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
            
    # --- クイズ出題中の表示 ---
    else:
        # 直前の結果表示
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

        # 選択肢生成
        if st.session_state.current_choices is None:
            all_meanings = list(st.session_state.quiz_data['words_dict'].values())
            distractors = [m for m in all_meanings if m != correct_meaning]
            num_distractors = min(len(distractors), 3)
            choices = random.sample(distractors, num_distractors)
            choices.append(correct_meaning)
            random.shuffle(choices)
            st.session_state.current_choices = choices

        # 選択肢ボタン
        choices = st.session_state.current_choices
        for choice in choices:
            if st.button(choice, use_container_width=True):
                check_answer(choice)
                st.rerun()
