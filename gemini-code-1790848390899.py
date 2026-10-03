import streamlit as st
import pandas as pd
import copy
from datetime import datetime
import os

st.set_page_config(page_title="イナリンピック 当日受付システム", layout="wide")

# ===== 1. ローカルCSVファイルからのデータ読み込み =====
CSV_FILE = 'history.csv'

if os.path.exists(CSV_FILE):
    df = pd.read_csv(CSV_FILE)
    # 古いCSV（氏名列がないデータ）を読み込んだ時のためのエラー回避処理
    if "氏名" not in df.columns:
        df["氏名"] = "未入力"
else:
    # データ枠の定義に「氏名」を追加
    df = pd.DataFrame(columns=["日時", "氏名", "チーム", "部門", "競技"])

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

if 'assigned_team' not in st.session_state:
    st.session_state.assigned_team = None

tab_reception, tab_roster = st.tabs(["📋 受付画面", "📖 参加者名簿"])

# ----------------------------------------
# 【タブ1】受付画面
# ----------------------------------------
with tab_reception:
    col_main, col_side = st.columns([2, 1])

    with col_main:
        if st.session_state.assigned_team:
            st.balloons()
            team = st.session_state.assigned_team
            
            if team == 'Red':
                st.markdown("""
                <div style="background-color:#ff4b4b; padding:50px; border-radius:15px; text-align:center; box-shadow: 0 4px 8px rgba(0,0,0,0.2);">
                    <h1 style="color:white; font-size:60px; margin:0;">🔴 赤チーム</h1>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div style="background-color:#ffffff; padding:50px; border-radius:15px; border:8px solid #dddddd; text-align:center; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
                    <h1 style="color:#333333; font-size:60px; margin:0;">⚪ 白チーム</h1>
                </div>
                """, unsafe_allow_html=True)
                
            st.markdown("<br>", unsafe_allow_html=True)
            
            if st.button("▶ 次の方の受付へ進む", type="primary", use_container_width=True):
                st.session_state.assigned_team = None
                st.rerun()

        else:
            st.subheader("👥 ご家族の受付")
            num_members = st.number_input("ご家族の人数を入力", min_value=1, max_value=10, value=1)
            family_data = []
            
            for i in range(num_members):
                st.markdown(f"**メンバー {i+1}**")
                # 名前・部門・競技を 1.5 : 1 : 2.5 の幅で横に並べる
                c1, c2, c3 = st.columns([1.5, 1, 2.5])
                with c1:
                    name = st.text_input("氏名", key=f"name_{i}", label_visibility="collapsed", placeholder="氏名 または ニックネーム")
                with c2:
                    dept = st.selectbox("部門", departments, key=f"dept_{i}", label_visibility="collapsed")
                with c3:
                    selected_games = st.multiselect("参加競技", list(game_options.keys()), key=f"games_{i}", label_visibility="collapsed", placeholder="参加競技を選択...")
                
                games_indices = [game_options[g] for g in selected_games]
                family_data.append({'name': name, 'dept': dept, 'games': games_indices})
                st.divider()

            if st.button("この家族のチームを判定！", type="primary", use_container_width=True):
                # エラーチェック（名前の空欄と、競技の未選択を防ぐ）
                if any(member['name'].strip() == "" for member in family_data):
                    st.warning("⚠ 氏名（ニックネーム）が入力されていないメンバーがいます。")
                elif any(len(member['games']) == 0 for member in family_data):
                    st.warning("⚠ 参加競技が選択されていないメンバーがいます。")
                else:
                    assigned_team = assigner.assign_family(family_data)
                    
                    new_rows = []
                    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    for member in family_data:
                        games_str = ",".join(map(str, member['games']))
                        new_rows.append({
                            "日時": now,
                            "氏名": member['name'],  # ★ここで名前を保存
                            "チーム": assigned_team,
                            "部門": member['dept'],
                            "競技": games_str
                        })
                    
                    updated_df = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True)
                    updated_df.to_csv(CSV_FILE, index=False)
                    
                    st.session_state.assigned_team = assigned_team
                    st.rerun()

        st.divider()
        if st.button("↩ 直前の受付を取り消す (Undo)", type="secondary"):
            if df.empty:
                st.warning("取り消すデータがありません。")
            else:
                last_timestamp = df.iloc[-1]['日時']
                df_updated = df[df['日時'] != last_timestamp]
                df_updated.to_csv(CSV_FILE, index=False)
                
                st.session_state.assigned_team = None
                st.success("直前の受付データを取り消しました！")
                st.rerun()

    with col_side:
        st.header("📊 現在のバランス")
        
        for dept in departments:
            st.markdown(f"### {dept}部門")
            chart_data = []
            for game_name, game_idx in game_options.items():
                red_count = assigner.counts['Red'][dept][game_idx]
                white_count = assigner.counts['White'][dept][game_idx]
                chart_data.append({"競技": game_name, "赤チーム": red_count, "白チーム": white_count})
            
            df_chart = pd.DataFrame(chart_data).set_index("競技")
            st.bar_chart(df_chart, color=["#ff4b4b", "#d3d3d3"])
            
            with st.expander("詳細な数字を確認"):
                for data in chart_data:
                    st.text(f"{data['競技']} - 赤: {data['赤チーム']}人 | 白: {data['白チーム']}人")
            st.divider()

# ----------------------------------------
# 【タブ2】参加者名簿画面
# ----------------------------------------
with tab_roster:
    st.header("📖 参加者名簿（受付データ一覧）")
    
    if df.empty:
        st.info("まだ受付データがありません。")
    else:
        idx_to_name = {str(v): k for k, v in game_options.items()}
        
        def format_games(games_str):
            if pd.isna(games_str): return ""
            indices = str(games_str).split(',')
            names = [idx_to_name.get(i.strip(), "不明") for i in indices]
            return "、".join(names)
            
        display_df = df.copy()
        display_df['競技'] = display_df['競技'].apply(format_games)
        
        # DataFrameの表示を少し整える
        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True  # 左端の連番（0,1,2...）を隠してスッキリさせる
        )
        
        csv_data = display_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 名簿をExcel(CSV)でダウンロード",
            data=csv_data,
            file_name="inarinpic_roster.csv",
            mime="text/csv",
        )

# ===== 5. 管理者メニュー =====
st.sidebar.divider()
with st.sidebar.expander("⚙️ 管理者メニュー (危険)"):
    st.warning("⚠️ これまでのすべての受付データを削除し、ゼロからやり直します。")
    confirm = st.checkbox("本当にすべてのデータを削除する")
    
    if confirm:
        if st.button("🚨 全データをリセット", type="primary", use_container_width=True):
            if os.path.exists(CSV_FILE):
                os.remove(CSV_FILE)
            st.session_state.assigned_team = None
            st.success("すべてのデータをリセットしました！")
            st.rerun()
