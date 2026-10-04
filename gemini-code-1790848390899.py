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
    if "氏名" not in df.columns:
        df["氏名"] = "未入力"
else:
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

if 'my_timestamps' not in st.session_state:
    st.session_state.my_timestamps = []

if 'last_family_data' not in st.session_state:
    st.session_state.last_family_data = None

st.sidebar.button("🔄 最新のデータに更新", type="primary", use_container_width=True)
st.sidebar.caption("他の端末で登録されたデータを画面に反映します")

tab_reception, tab_roster, tab_optimize = st.tabs(["📋 受付画面", "📖 参加者名簿・競技別", "⚖️️ 全体バランス調整"])

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
            
            if st.session_state.last_family_data:
                st.markdown("<br>", unsafe_allow_html=True)
                st.info("📸 **出番を忘れないように、この画面をスマホで写真に撮っておいてください。**")
                
                idx_to_name = {v: k for k, v in game_options.items()}
                
                with st.container(border=True):
                    st.markdown("#### 📝 ご家族の参加競技メモ")
                    for member in st.session_state.last_family_data:
                        game_names = [idx_to_name[g] for g in member['games']]
                        games_str = "、".join(game_names)
                        st.markdown(f"- **{member['name']}** さん （{member['dept']}） ： {games_str}")

            st.markdown("<br>", unsafe_allow_html=True)
            
            if st.button("▶ 次の方の受付へ進む", type="primary", use_container_width=True):
                st.session_state.assigned_team = None
                st.session_state.last_family_data = None
                st.rerun()

        else:
            st.subheader("👥 ご家族の受付")
            num_members = st.number_input("ご家族の人数を入力", min_value=1, max_value=10, value=1)
            family_data = []
            
            for i in range(num_members):
                st.markdown(f"**メンバー {i+1}**")
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
                            "氏名": member['name'],
                            "チーム": assigned_team,
                            "部門": member['dept'],
                            "競技": games_str
                        })
                    
                    updated_df = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True)
                    updated_df.to_csv(CSV_FILE, index=False)
                    
                    st.session_state.my_timestamps.append(now)
                    st.session_state.assigned_team = assigned_team
                    st.session_state.last_family_data = family_data 
                    st.rerun()

        st.divider()
        if st.button("↩ 直前の受付を取り消す (Undo)", type="secondary"):
            if len(st.session_state.my_timestamps) == 0:
                st.warning("この端末から取り消せる直前のデータがありません。")
            else:
                my_last_timestamp = st.session_state.my_timestamps[-1]
                if my_last_timestamp in df['日時'].values:
                    df_updated = df[df['日時'] != my_last_timestamp]
                    df_updated.to_csv(CSV_FILE, index=False)
                    st.success("あなたの端末で受け付けた直前のデータを取り消しました！")
                else:
                    st.warning("そのデータは既に名簿から削除されています。")
                
                st.session_state.my_timestamps.pop()
                st.session_state.assigned_team = None
                st.session_state.last_family_data = None
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
# 【タブ2】参加者名簿 ＆ 競技別名簿
# ----------------------------------------
with tab_roster:
    st.header("📖 参加者名簿 ＆ 競技別名簿")
    
    if st.button("🔄 名簿を最新状態にする", use_container_width=True):
        st.rerun()
        
    if df.empty:
        st.info("まだ受付データがありません。")
    else:
        # 表示用の翻訳準備
        idx_to_name = {str(v): k for k, v in game_options.items()}
        
        def format_games(games_str):
            if pd.isna(games_str): return ""
            indices = str(games_str).split(',')
            names = [idx_to_name.get(i.strip(), "不明") for i in indices]
            return "、".join(names)
            
        display_df = df.copy()
        display_df['競技'] = display_df['競技'].apply(format_games)
        
        # サブタブで「全体名簿」と「競技別名簿」を切り替えられるようにする
        sub_tab1, sub_tab2 = st.tabs(["📋 全体一覧・検索・削除", "🎯 競技別・部門別名簿"])
        
        with sub_tab1:
            search_query = st.text_input("🔍 名前で検索（家族も一緒に表示されます）", "")
            
            if search_query:
                matched_times = df[df['氏名'].str.contains(search_query, na=False)]['日時'].unique()
                filtered_display_df = display_df[display_df['日時'].isin(matched_times)]
                filtered_df = df[df['日時'].isin(matched_times)]
            else:
                filtered_display_df = display_df
                filtered_df = df
            
            st.dataframe(
                filtered_display_df,
                use_container_width=True,
                hide_index=True
            )
            
            st.divider()
            st.subheader("🗑️ 特定の参加者を削除")
            st.write("名簿から特定の人だけを消したい場合は、以下から選んで削除してください。")
            
            delete_options = []
            for idx, row in filtered_df.iterrows():
                delete_options.append(f"No.{idx} : {row['氏名']} （{row['チーム']}チーム / {row['部門']}）")
                
            selected_to_delete = st.selectbox("削除する人を選んでください", ["選択してください..."] + delete_options)
            
            if st.button("🚨 この参加者を削除", type="primary"):
                if selected_to_delete != "選択してください...":
                    target_idx = int(selected_to_delete.split(":")[0].replace("No.", "").strip())
                    df_updated = df.drop(index=target_idx)
                    df_updated.to_csv(CSV_FILE, index=False)
                    
                    st.success("参加者を削除しました！")
                    st.rerun()
                else:
                    st.warning("削除する人を選択してください。")
            
            st.divider()
            csv_data = display_df.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="📥 全体名簿をExcel(CSV)でダウンロード",
                data=csv_data,
                file_name="inarinpic_all_roster.csv",
                mime="text/csv",
            )
            
        with sub_tab2:
            st.subheader("🎯 競技別・部門別の出場者一覧")
            st.write("各競技の、部門ごとの赤・白の出場メンバーを確認できます。")
            
            # 競技ごとにループして表示
            for game_name in game_options.keys():
                with st.expander(f"🚩 {game_name} の出場者名簿", expanded=True):
                    # この競技に参加している行を抽出する処理
                    game_rows = []
                    for _, row in df.iterrows():
                        games_str = str(row['競技'])
                        indices = [i.strip() for i in games_str.split(',')]
                        # 該当する競技のインデックス（例: 0）が含まれているか
                        target_idx_str = str(game_options[game_name])
                        if target_idx_str in indices:
                            game_rows.append(row)
                            
                    if not game_rows:
                        st.info("この競技に参加するメンバーはまだいません。")
                    else:
                        game_df = pd.DataFrame(game_rows)
                        
                        # 部門ごとに分ける
                        for dept in departments:
                            dept_df = game_df[game_df['部門'] == dept]
                            
                            red_members = dept_df[dept_df['チーム'] == 'Red']['氏名'].tolist()
                            white_members = dept_df[dept_df['チーム'] == 'White']['氏名'].tolist()
                            
                            st.markdown(f"**【 {dept}部門 】** (赤: {len(red_members)}人 / 白: {len(white_members)}人)")
                            
                            col_r, col_w = st.columns(2)
                            with col_r:
                                st.markdown(f"🔴 **赤チーム**: {', '.join(red_members) if red_members else 'なし'}")
                            with col_w:
                                st.markdown(f"⚪ **白チーム**: {', '.join(white_members) if white_members else 'なし'}")
                            
                            st.markdown("---")

# ----------------------------------------
# 【タブ3】全体バランス調整機能
# ----------------------------------------
with tab_optimize:
    st.header("⚖️ 全体バランスの最適化チェック")
    st.write("受付が全員終わった後に、現在のチーム分けの偏りを診断し、いくつかのチームを入れ替えることでバランスが良くなるか検証します。")
    
    if df.empty:
        st.info("データがありません。")
    else:
        if st.button("🔍 全体のバランスを診断・最適化案を探す", type="primary"):
            groups = []
            for timestamp, group_df in df.groupby('日時'):
                current_team = group_df.iloc[0]['チーム']
                members = []
                for _, row in group_df.iterrows():
                    games_indices = [int(g.strip()) for g in str(row['競技']).split(',') if g.strip().isdigit()]
                    members.append({
                        'name': row['氏名'],
                        'dept': row['部門'],
                        'games': games_indices
                    })
                groups.append({
                    'timestamp': timestamp,
                    'current_team': current_team,
                    'members': members
                })
            
            def calc_total_score(current_groups):
                temp_counts = {team: {d: [0]*4 for d in ['初心者', '中級者', '上級者']} for team in ['Red', 'White']}
                for grp in current_groups:
                    t = grp['current_team']
                    for m in grp['members']:
                        d = m['dept']
                        for g in m['games']:
                            temp_counts[t][d][g] += 1
                
                score = 0
                for d in ['初心者', '中級者', '上級者']:
                    for g in range(4):
                        score += abs(temp_counts['Red'][d][g] - temp_counts['White'][d][g])
                return score, temp_counts

            base_score, base_counts = calc_total_score(groups)
            st.metric("現在の不均衡スコア（数値が小さいほどバランスが良い）", f"{base_score}点")
            
            best_score = base_score
            best_groups = copy.deepcopy(groups)
            improved = False
            
            for i in range(len(groups)):
                test_groups = copy.deepcopy(groups)
                test_groups[i]['current_team'] = 'White' if test_groups[i]['current_team'] == 'Red' else 'Red'
                
                test_score, _ = calc_total_score(test_groups)
                if test_score < best_score:
                    best_score = test_score
                    best_groups = test_groups
                    improved = True

            if improved:
                st.success(f"✨ 改善案が見つかりました！ 入れ替えを行うと、不均衡スコアが **{base_score}点 ⇒ {best_score}点** に改善されます。")
                
                st.markdown("### 📋 変更されるご家族の提案一覧")
                changes_count = 0
                for old_g, new_g in zip(groups, best_groups):
                    if old_g['current_team'] != new_g['current_team']:
                        names = ", ".join([m['name'] for m in new_g['members']])
                        st.markdown(f"- **{names}** ご家族： `{old_g['current_team']}` チーム ➡ **`{new_g['current_team']}` チーム** へ変更")
                        changes_count += 1
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                if st.button("🚀 この最適化案を実行して名簿を書き換える", type="primary"):
                    new_rows = []
                    for g in best_groups:
                        t = g['current_team']
                        ts = g['timestamp']
                        for m in g['members']:
                            games_str = ",".join(map(str, m['games']))
                            new_rows.append({
                                "日時": ts,
                                "氏名": m['name'],
                                "チーム": t,
                                "部門": m['dept'],
                                "競技": games_str
                            })
                    
                    new_df = pd.DataFrame(new_rows)
                    new_df.to_csv(CSV_FILE, index=False)
                    st.success("全データのチームバランスを最適化し、名簿を更新しました！「最新のデータに更新」ボタンを押すか、他のタブを確認してください。")
                    st.balloons()
            else:
                st.info("👍 現在のチーム分けはすでに十分バランスが取れており、入れ替えによる改善案は見つかりませんでした。このまま本番を迎えて大丈夫です！")

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
            st.session_state.my_timestamps = []
            st.session_state.last_family_data = None
            st.success("すべてのデータをリセットしました！")
            st.rerun()
