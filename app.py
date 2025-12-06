import streamlit as st
import pandas as pd
import random
import os

# ==========================================
# 設定：ページの基本設定（スマホで見やすく）
# ==========================================
st.set_page_config(
    page_title="TOEIC上級単語クイズ",
    layout="centered", # スマホの中央に寄せる
    initial_sidebar_state="collapsed"
)

# ファイルパス設定（カレントディレクトリ基準）
BASE_DIR = os.getcwd()
EXCEL_FILE = os.path.join(BASE_DIR, "toeic_words.xlsx")

# ==========================================
# 関数定義
# ==========================================
@st.cache_data  # データをキャッシュして読み込みを高速化
def load_data(file_path):
    """Excelデータを読み込む関数"""
    if not os.path.exists(file_path):
        st.error(f"エラー: ファイル '{file_path}' が見つかりません。")
        return None
    try:
        df = pd.read_excel(file_path, engine='openpyxl')
        if 'Word' not in df.columns or 'Meaning' not in df.columns:
            st.error("エラー: Excelファイルに 'Word' または 'Meaning' 列がありません。")
            return None
        df = df.dropna(subset=['Word', 'Meaning'])
        return dict(zip(df['Word'], df['Meaning']))
    except Exception as e:
        st.error(f"予期せぬエラーが発生しました: {e}")
        return None

def initialize_quiz(num_questions=10):
    """クイズの状態をリセット・初期化する"""
    word_data = load_data(EXCEL_FILE)
    if not word_data or len(word_data) < 4:
        st.error("データが不足しています。Excelファイルを確認してください。")
        st.stop() # 処理を停止

    words = list(word_data.keys())
    actual_num = min(num_questions, len(words))
    
    # アプリの状態（セッションステート）にデータを保存
    st.session_state.quiz_data = {
        'words_dict': word_data,
        'question_words': random.sample(words, actual_num),
        'total_questions': actual_num
    }
    st.session_state.current_index = 0
    st.session_state.score = 0
    st.session_state.quiz_finished = False
    st.session_state.current_choices = None # 選択肢の並び順を保持用
    st.session_state.last_result = None # 直前の問題の正誤結果表示用

def check_answer(selected_meaning):
    """ボタンが押された時の回答チェック処理"""
    # 現在の問題情報を取り出す
    q_word = st.session_state.quiz_data['question_words'][st.session_state.current_index]
    correct_meaning = st.session_state.quiz_data['words_dict'][q_word]
    
    # 正誤判定
    if selected_meaning == correct_meaning:
        st.session_state.score += 1
        st.session_state.last_result = ("✅ 正解！", "success")
    else:
        st.session_state.last_result = (f"❌ 不正解... (正解は「{correct_meaning}」)", "error")
        
    # 次の問題へ進む準備
    st.session_state.current_index += 1
    st.session_state.current_choices = None # 次の問題のために選択肢をリセット
    
    # 全問終了したかチェック
    if st.session_state.current_index >= st.session_state.quiz_data['total_questions']:
        st.session_state.quiz_finished = True

# ==========================================
# メイン画面描画 (UI)
# ==========================================
st.title("🎓 TOEIC上級単語クイズ")

# 初回起動時のみ初期化を実行
if 'quiz_data' not in st.session_state:
    initialize_quiz()

# --- 画面パターン1: 結果発表画面 ---
if st.session_state.quiz_finished:
    st.balloons() # 終了時に風船を飛ばす演出
    st.header("🎉 結果発表 🎉")
    
    score = st.session_state.score
    total = st.session_state.quiz_data['total_questions']
    percentage = score / total * 100
    
    # スコアを見やすく表示
    st.metric(label="あなたのスコア", value=f"{score} / {total} 問正解", delta=f"正答率 {percentage:.0f}%")
    
    # メッセージ
    if percentage == 100:
        st.success("Perfect! 素晴らしい語彙力です！")
    elif percentage >= 80:
        st.info("Excellent! その調子です。")
    else:
        st.warning("Keep studying! 復習しましょう。")
        
    st.write("") # 空白
    # リトライボタン（横幅いっぱい）
    if st.button("もう一度挑戦する 🔄", type="primary", use_container_width=True):
        initialize_quiz() # 状態をリセット
        st.rerun() # 画面を再読み込み
    st.stop() # 以降の処理を行わない

# --- 画面パターン2: クイズ出題画面 ---

# 1. 直前の問題の正誤結果を表示（もしあれば）
if st.session_state.last_result:
    msg, type_ = st.session_state.last_result
    if type_ == "success":
        st.success(msg)
    else:
        st.error(msg)
    st.session_state.last_result = None # 表示したら消す

# 2. 現在の問題データを取得
current_idx = st.session_state.current_index
total_q = st.session_state.quiz_data['total_questions']
q_word = st.session_state.quiz_data['question_words'][current_idx]
correct_meaning = st.session_state.quiz_data['words_dict'][q_word]

# 3. 進捗バーと問題文表示
st.write(f"問題 {current_idx + 1} / {total_q}")
st.progress((current_idx) / total_q)
st.markdown(f"# 📝 {q_word}") # 単語を大きく表示

st.write("正しい意味を選択してください:")

# 4. 選択肢の生成（この問題でまだ生成していなければ作成）
# ※これを行わないと、ボタンを押すたびに選択肢が変わってしまいます
if st.session_state.current_choices is None:
    all_meanings = list(st.session_state.quiz_data['words_dict'].values())
    distractors = [m for m in all_meanings if m != correct_meaning]
    # 誤答が足りない場合の安全策
    num_distractors = min(len(distractors), 3)
    choices = random.sample(distractors, num_distractors)
    choices.append(correct_meaning)
    random.shuffle(choices)
    # 生成した選択肢をセッションステートに保存
    st.session_state.current_choices = choices

# 5. 選択肢ボタンの配置（縦並び）
choices = st.session_state.current_choices
for choice in choices:
    # ボタンを作成。押されるとTrueになりif文の中が実行される
    # use_container_width=True でスマホの横幅いっぱいに広げる
    if st.button(choice, use_container_width=True):
        check_answer(choice) # 回答チェック関数を呼ぶ
        st.rerun() # 画面を即座に更新して次の問題へ
