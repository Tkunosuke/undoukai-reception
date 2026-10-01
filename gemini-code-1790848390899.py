import streamlit as st
import copy

# ===== 先ほどの判定アルゴリズム（そのまま） =====
class TeamAssigner:
    def __init__(self):
        self.teams = ['Red', 'White']
        self.departments = ['子供', '大人', 'シニア']
        self.num_games = 4
        
        self.counts = {
            team: {
                dept: [0] * self.num_games for dept in self.departments
            }
            for team in self.teams
        }

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

        for member in family_members:
            dept = member['dept']
            for game_idx in member['games']:
                self.counts[best_team][dept][game_idx] += 1
                
        return best_team


# ===== ここからWeb画面（Streamlit）の実装 =====

# 1. 状態の初期化（画面が更新されてもデータを保持するための仕組み）
if 'assigner' not in st.session_state:
    st.session_state.assigner = TeamAssigner()

st.title("🚩 運動会 当日受付システム")

# 選択肢の定義
departments = ['子供', '大人', 'シニア']
game_options = {'第1競技': 0, '第2競技': 1, '第3競技': 2, '第4競技': 3}

# 2. 受付入力フォーム
st.subheader("👥 ご家族の受付")
num_members = st.number_input("ご家族の人数を入力してください", min_value=1, max_value=10, value=1)

family_data = []

# 人数分の入力枠をループで生成
for i in range(num_members):
    st.markdown(f"**メンバー {i+1}**")
    col1, col2 = st.columns([1, 2]) # 1:2の幅で横並びに
    
    with col1:
        # 部門の選択
        dept = st.selectbox("部門", departments, key=f"dept_{i}", label_visibility="collapsed")
    with col2:
        # 参加競技の複数選択（リストで返ってきます）
        selected_games = st.multiselect("参加競技", list(game_options.keys()), key=f"games_{i}", label_visibility="collapsed", placeholder="参加する競技を選択...")
    
    # アルゴリズムに渡すためのインデックス（0〜3）に変換
    games_indices = [game_options[g] for g in selected_games]
    family_data.append({'dept': dept, 'games': games_indices})
    
    st.divider() # 区切り線

# 3. 判定ボタンと結果表示
if st.button("この家族のチームを判定！", type="primary", use_container_width=True):
    # 競技が1つも選ばれていない人がいる場合の警告
    if any(len(member['games']) == 0 for member in family_data):
        st.warning("⚠️️ 参加競技が選択されていないメンバーがいます。確認してください。")
    else:
        # アルゴリズムを実行してチームを決定
        assigned_team = st.session_state.assigner.assign_family(family_data)
        
        # 画面に大きく結果を表示
        if assigned_team == 'Red':
            st.error("🎉 判定結果: 【 赤チーム 】 です！") # st.errorは背景が赤っぽくなるので代用
        else:
            st.info("🎉 判定結果: 【 白チーム 】 です！")  # st.infoは背景が青/白っぽくなる
        
        st.balloons() # ちょっとしたお祝いアニメーション

# 4. 現在の状況（サイドバーに表示）
st.sidebar.header("📊 現在のバランス状況")
for dept in departments:
    st.sidebar.markdown(f"**{dept}部門**")
    
    # 競技ごとに赤と白の人数を横並びで表示
    for game_name, game_idx in game_options.items():
        red_count = st.session_state.assigner.counts['Red'][dept][game_idx]
        white_count = st.session_state.assigner.counts['White'][dept][game_idx]
        st.sidebar.text(f"{game_name} - 赤:{red_count}人 | 白:{white_count}人")
    st.sidebar.divider()