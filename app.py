import streamlit as st
import pandas as pd
import random
import os
import difflib
import time
import csv
from datetime import datetime


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
/* 1. 基本のバー（問題番号）を青にする */
.stProgress > div > div > div > div {
    background-color: #007bff;
}

/* 2. 制限時間のバー（2つ目に表示されるバー）を赤で上書きする */
/* ページ内の2番目のプログレスバーをターゲットにします */
.stProgress:nth-of-type(2) > div > div > div > div {
    background-color: #ff4b4b;
}
</style>
""", unsafe_allow_html=True)

# ファイルパス設定
BASE_DIR = os.getcwd()
HISTORY_FILE = os.path.join(BASE_DIR, "history.csv") # 学習履歴保存用ファイル

# コースとファイル名の対応表
QUIZ_FILES = {
    "テスト用":"toeic_words_gemini.xlsx",
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

# 回答結果をCSVに記録する関数
def save_history(word, is_correct):
    """学習履歴を保存"""
    # ファイルがなければヘッダーを作成
    if not os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["Word", "IsCorrect", "Timestamp"])

    # 追記モードで保存
    with open(HISTORY_FILE, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([word, 1 if is_correct else 0, datetime.now().isoformat()])

# 苦手な単語を選びやすくするAIロジック
def get_weighted_questions(words, num_questions):
    """学習履歴を読み込み、苦手な単語が出やすくなるように重み付け抽選を行う"""
    if not os.path.exists(HISTORY_FILE):
        return random.sample(words, min(num_questions, len(words)))

    try:
        history_df = pd.read_csv(HISTORY_FILE)
        
        # 単語ごとの「正解数」と「不正解数」を集計
        stats = history_df.groupby("Word")["IsCorrect"].agg(['sum', 'count']).reset_index()
        stats.rename(columns={'sum': 'corrects', 'count': 'total'}, inplace=True)
        stats['wrongs'] = stats['total'] - stats['corrects']
        
        wrong_counts = dict(zip(stats['Word'], stats['wrongs']))
        correct_counts = dict(zip(stats['Word'], stats['corrects']))

        # 重み（出やすさ）の計算
        # 基本10 + (不正解数 × 20) - (正解数 × 2)
        weights = []
        for word in words:
            w_count = wrong_counts.get(word, 0)
            c_count = correct_counts.get(word, 0)
            score = 10 + (w_count * 20) - (c_count * 2)
            if score < 1: score = 1
            weights.append(score)
        
        # 重複なしで重み付き抽選を行うロジック
        selected_questions = []
        temp_words = list(words)
        temp_weights = list(weights)
        
        for _ in range(min(num_questions, len(words))):
            chosen_list = random.choices(temp_words, weights=temp_weights, k=1)
            chosen_word = chosen_list[0]
            selected_questions.append(chosen_word)
            
            # 選ばれた単語を候補から削除
            idx = temp_words.index(chosen_word)
            temp_words.pop(idx)
            temp_weights.pop(idx)
            
        return selected_questions

    except Exception:
        return random.sample(words, min(num_questions, len(words)))

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

def initialize_quiz(course_name, num_questions, time_limit, use_ai_mode):
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

    if use_ai_mode:
        question_words = get_weighted_questions(words, actual_num)
    else:
        question_words = random.sample(words, actual_num)
    
    st.session_state.quiz_data = {
        'course_name': course_name,
        'words_dict': word_data,
        'question_words': question_words,
        'total_questions': actual_num,
        'time_limit': time_limit,
        'use_ai_mode': use_ai_mode # モード情報を保存
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
    
    is_correct = (selected_meaning == correct_meaning)
    
    # 履歴保存
    save_history(q_word, is_correct)
    
    if is_correct:
        st.session_state.score += 1
        st.session_state.last_result = ("✅ 正解！", "success")
    else:
        st.session_state.last_result = (f"❌ 不正解... (正解は「{correct_meaning}」)", "error")
        
    move_to_next()

def handle_time_up():
    """時間切れ時の処理"""
    q_word = st.session_state.quiz_data['question_words'][st.session_state.current_index]
    correct_meaning = st.session_state.quiz_data['words_dict'][q_word]
    
    # 時間切れメッセージを設定
    save_history(q_word, False)
    st.session_state.last_result = (f"⏰ 時間切れ！ (正解は「{correct_meaning}」)", "error")
    
    move_to_next()

def move_to_next():
    """次の問題へ進む共通処理"""
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

    # オプション設定（アコーディオンに隠してスッキリさせる）
    with st.expander("⚙️ オプション設定"):
        num_q = st.slider("問題数", min_value=5, max_value=50, value=10)
    
        st.write("---") # 区切り線

        use_ai = st.toggle("🔥 AI弱点克服モード", value=False, help="過去に間違えた問題を優先的に出題します")

        st.write("---")

    # 制限時間設定
        use_timer = st.checkbox("制限時間を設ける", value=False)
        if use_timer:
            time_limit = st.slider("1問あたりの制限時間（秒）", min_value=3, max_value=10, value=5)
        else:
            time_limit = 0 # 0は制限時間なしとする

        st.markdown("---")

    # コースボタンを生成して配置
    # 辞書(QUIZ_FILES)にあるコースの分だけボタンを作ります
    for course_name in QUIZ_FILES.keys():
        # type="primary" で目立つ色に、use_container_width=True で横幅いっぱいに
        if st.button(course_name, type="primary", use_container_width=True):
            # ボタンが押されたらそのコースで開始
            if initialize_quiz(course_name, num_q,time_limit,use_ai):
                st.session_state.page = "quiz"
                st.rerun()
        
        st.write("") # ボタン間の隙間

#学習ダッシュボード
    st.markdown("---")
    st.header("📊 学習データ")
    
    if os.path.exists(HISTORY_FILE):
        try:
            df = pd.read_csv(HISTORY_FILE)
            if not df.empty:
                # 1. 基本スタッツの表示
                total_answers = len(df)
                total_correct = df['IsCorrect'].sum()
                accuracy = (total_correct / total_answers) * 100
                
                col1, col2, col3 = st.columns(3)
                col1.metric("総回答数", f"{total_answers}問")
                col2.metric("正解数", f"{total_correct}問")
                col3.metric("正答率", f"{accuracy:.1f}%")
                
                # 2. 日別学習量のグラフ
                # Timestamp列を日時型に変換して、日付ごとの回答数を集計
                df['Date'] = pd.to_datetime(df['Timestamp']).dt.date
                daily_counts = df.groupby('Date')['IsCorrect'].count()
                
                st.write("##### 📅 日々の学習量")
                st.bar_chart(daily_counts)

                st.write("")
                with st.expander("🗑️ データの管理（リセット）"):
                    st.warning("これまでの学習履歴（正解・不正解の記録）をすべて消去します。この操作は取り消せません。")
                    if st.button("学習データを完全にリセットする", type="primary"):
                        os.remove(HISTORY_FILE) # ファイルを削除
                        st.success("リセットしました！")
                        time.sleep(1) # 1秒待ってから
                        st.rerun() # 画面を更新
                
            else:
                st.info("まだ学習履歴がありません。クイズを解くとここにデータが表示されます。")
        except Exception as e:
            st.error(f"データの読み込みに失敗しました: {e}")
    else:
        st.info("まだ学習データがありません。クイズに挑戦して履歴を作りましょう！")

# --- 画面2: クイズ画面 ---
elif st.session_state.page == "quiz":
    
    if 'quiz_data' not in st.session_state:
        st.session_state.page = "menu"
        st.rerun()

    # ヘッダー
    col1, col2 = st.columns([3, 1])
    with col1:
        mode_text = "🔥AIモード" if st.session_state.quiz_data.get('use_ai_mode') else "通常モード"
        st.caption(f"挑戦中: {st.session_state.quiz_data['course_name']} ({mode_text})")
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

        col_retry, col_menu = st.columns(2)
        
        with col_retry:
            # 同じ設定でもう一度遊ぶボタン
            if st.button("もう一度挑戦 🔄", type="primary", use_container_width=True):
                # 現在の設定を取得
                d = st.session_state.quiz_data
                # AIモードの設定も引き継いで再初期化
                initialize_quiz(d['course_name'], d['total_questions'], d['time_limit'], d['use_ai_mode'])
                st.rerun()

        with col_menu:
            # メニューに戻るボタン
            if st.button("メニューに戻る 🏠", use_container_width=True):
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

        # 制限時間の取得
        limit_sec = st.session_state.quiz_data.get('time_limit', 0)
        # タイマー表示用のプレースホルダー（空き地）を作っておく
        # ここに後でバーを表示します
        timer_placeholder = st.empty()

        # 進捗バーと問題文
        st.progress((current_idx) / total_q)
        st.markdown(f"### Q{current_idx + 1}.  **{q_word}**")

        # --- 自動選別ロジック、意味が似ている単語を選択肢からはじく---
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
                # ボタンが押されたら check_answer が走って rerun され、下のループは中断される
                check_answer(choice)
                st.rerun()

        #制限時間のカウントダウン
        # ボタン表示の下に書くことで、ボタン描画後に待機ループに入る
        if limit_sec > 0:
            # バーを表示するコンテナ
            with timer_placeholder.container():
                progress_bar = st.progress(1.0) # 最初は満タン(1.0)
                status_text = st.empty()
            
            # カウントダウンループ
            # Streamlitの仕様上、このループ中にボタンが押されると
            # ループは中断され、スクリプトが再実行(rerun)されます。
            # つまり、時間切れになる前にボタンを押せばOKということです。
            
            start_time = time.time()
            while True:
                elapsed = time.time() - start_time
                remaining = limit_sec - elapsed
                
                if remaining <= 0:
                    # 時間切れ！
                    progress_bar.progress(0.0)
                    status_text.write("⏳ 0.0 秒")
                    handle_time_up() # 時間切れ処理を実行
                    st.rerun() # 強制リロードして次の問題へ
                    break
                
                # バーと時間を更新
                ratio = max(0.0, remaining / limit_sec)
                progress_bar.progress(ratio)
                
                # 少し待機（この間にボタンクリックを検知させる）
                time.sleep(0.1)
            
