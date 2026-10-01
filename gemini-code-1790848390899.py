import streamlit as st
import pandas as pd
import copy
from datetime import datetime
import os

st.set_page_config(page_title="イナリンピック 当日受付システム", layout="wide")

# ===== 1. ローカルCSVファイルからのデータ読み込み =====
CSV_FILE = 'history.csv'

# ファイルが存在すれば読み込み、なければ空のデータ枠を作る
if os.path.exists(CSV_FILE):
    df = pd.read_csv(CSV_FILE)
else:
    df = pd.DataFrame(columns=["日時", "チーム", "部門", "競技"])

# ===== 2. 判定アルゴリズム =====
class TeamAssigner:
    def __init__(self, history_df):
        self.teams = ['Red', 'White']
        self.departments = ['初心者', '中級者', '上級者']
        self.num_games = 4
        
        self.counts = {
            team: {dept: [0] * self.num_games for dept in self.departments}
            for team in self.teams
        }
        
        # CSVの履歴から現在の人数を復元
        if not history_df.empty:
            for _, row in history_df.iterrows():
                team = str(row['チーム'])
                dept = str(row['部門'])
                games_str = str(row['競技'])
                
                if team in self.teams and dept in self.departments and games_str != "nan":
                    for g in games_str.split(','):
                        if g.strip().isdigit():
                            game_idx = int(g.strip())
                            if 0 <= game_idx < self.num_games:
                                self.counts[team][dept][game_idx] += 1

    def _calculate_diff_score(self, temp_counts):
        score = 0
        for dept in self.departments:
            for game_idx in range(self.num_games):
                score += abs(temp_counts['Red'][dept][game_idx] - temp_counts['White'][dept][game_idx])
        return score

    def assign_family(self, family_members):
        best_team = None
        min_score = float('inf')
        
        for target_team in self.teams:
            temp_counts = copy.deepcopy(self.counts)
            for member in family_members:
                dept = member['dept']
                for game_idx in member['games']:
                    temp_counts[target_team][dept][game_idx] += 1
            
            score = self._calculate_diff_score(temp_counts)
            
            if score < min_score:
                min_score = score
                best_team = target_team
            elif score == min_score:
                red_total = sum(sum(temp_counts['Red'][d]) for d in self.departments)
                white_total = sum(sum(temp_counts['White'][d]) for d in self.departments)
                best_team = 'Red' if red_total < white_total else 'White'
                
        return best_team

assigner = TeamAssigner(df)


# ===== 3. Web画面 UI =====
st.title("🚩 運動会 当日受付システム")

departments = ['初心者', '中級者', '上級者']
game_options = {'障害物走': 0, 'ドッチボールo玉入れ': 1, '綱引き': 2, 'リレー': 3}

col_main, col_side = st.columns([2, 1])

with col_main:
    st.subheader("👥 ご家族の受付")
    num_members = st.number_input("ご家族の人数を入力", min_value=1, max_value=10, value=1)
    family_data = []

    for i in range(num_members):
        st.markdown(f"**メンバー {i+1}**")
        c1, c2 = st.columns([1, 2])
        with c1:
            dept = st.selectbox("部門", departments, key=f"dept_{i}", label_visibility="collapsed")
        with c2:
            selected_games = st.multiselect("参加競技", list(game_options.keys()), key=f"games_{i}", label_visibility="collapsed", placeholder="参加競技を選択...")
        
        games_indices = [game_options[g] for g in selected_games]
        family_data.append({'dept': dept, 'games': games_indices})
        st.divider()

    # --- 判定＆保存ボタン ---
    if st.button("この家族のチームを判定！", type="primary", use_container_width=True):
        if any(len(member['games']) == 0 for member in family_data):
            st.warning("⚠ 参加競技が選択されていないメンバーがいます。")
        else:
            assigned_team = assigner.assign_family(family_data)
            
            # CSVに追記するデータを作成
            new_rows = []
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            for member in family_data:
                games_str = ",".join(map(str, member['games']))
                new_rows.append({
                    "日時": now,
                    "チーム": assigned_team,
                    "部門": member['dept'],
                    "競技": games_str
                })
            
            # 既存データに結合してCSVファイルを上書き保存
            updated_df = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True)
            updated_df.to_csv(CSV_FILE, index=False)
                
            if assigned_team == 'Red':
                st.error("🎉 判定結果: 【 赤チーム 】 です！")
            else:
                st.info("🎉 判定結果: 【 白チーム 】 です！")
            st.balloons()
            st.rerun()

    # --- 取り消し（Undo）ボタン ---
    st.divider()
    if st.button("↩ 直前の受付を取り消す (Undo)", type="secondary"):
        if df.empty:
            st.warning("取り消すデータがありません。")
        else:
            # 最新の日時を取得し、それ以外のデータを残す（最新を削除）
            last_timestamp = df.iloc[-1]['日時']
            df_updated = df[df['日時'] != last_timestamp]
            
            # CSVファイルを上書きして保存
            df_updated.to_csv(CSV_FILE, index=False)
            
            st.success(f"直前の受付データを取り消しました！")
            st.rerun()


# ===== 4. 現在のバランス状況 =====
with col_side:
    st.header("📊 現在のバランス")
    for dept in departments:
        st.markdown(f"**{dept}部門**")
        for game_name, game_idx in game_options.items():
            red_count = assigner.counts['Red'][dept][game_idx]
            white_count = assigner.counts['White'][dept][game_idx]
            st.text(f"{game_name}\n赤: {red_count}人 | 白: {white_count}人")
        st.divider()
# ===== 5. 管理者メニュー（テストデータのリセット） =====
    st.sidebar.divider()
    
    # expanderを使うことで、普段は折りたたんで隠しておけます
    with st.sidebar.expander("⚙️ 管理者メニュー (危険)"):
        st.warning("⚠️ これまでのすべての受付データを削除し、ゼロからやり直します。")
        
        # 安全装置：チェックボックス
        confirm = st.checkbox("本当にすべてのデータを削除する")
        
        # チェックが入っている時だけボタンを有効化する
        if confirm:
            if st.button("🚨 全データをリセット", type="primary", use_container_width=True):
                # CSVファイルが存在していれば削除する
                import os
                if os.path.exists(CSV_FILE):
                    os.remove(CSV_FILE)
                
                st.success("すべてのデータをリセットしました！")
                st.rerun()
