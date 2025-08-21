import streamlit as st
import pandas as pd
import networkx as nx
import plotly.graph_objects as go

# ページのレイアウトをワイドに設定
st.set_page_config(layout="wide")

# アプリケーションのタイトルを設定
st.title("図番親子関係の家系図")
st.write("Excelファイル (.xlsx) をアップロードして、図番の親子関係グラフを表示します。")

# 1. ファイルアップローダーの設置
uploaded_file = st.file_uploader(
    "Excelファイル (.xlsx) をここにドラッグ＆ドロップするか、クリックして選択してください",
    type=["xlsx"]
)

# 2. Excelファイルを読み込む関数
@st.cache_data(ttl=600)
def load_data(file_object):
    """
    アップロードされたExcelファイルオブジェクトからデータを読み込み、DataFrameとして返す。
    """
    try:
        df = pd.read_excel(file_object, sheet_name='Sheet1')
        expected_columns = ['Child', 'Parent', 'Creator', 'Date']
        
        if not all(col in df.columns for col in expected_columns):
            missing_cols = [col for col in expected_columns if col not in df.columns]
            st.error(f"エラー: Excelファイルに必要なカラムが見つかりません。以下のカラムが必要です: {', '.join(expected_columns)}。見つからないカラム: {', '.join(missing_cols)}")
            return pd.DataFrame()

        df = df[expected_columns]
        df = df.fillna('')
        
        if 'Date' in df.columns:
            df['Date'] = df['Date'].apply(lambda x: x.strftime('%Y/%m/%d') if isinstance(x, pd.Timestamp) else str(x).strip())
        
        return df
    except Exception as e:
        st.error(f"データの読み込み中にエラーが発生しました: {e}")
        st.info("Excelファイルのシート名が 'Sheet1' であること、または必要なカラム名 ('Child', 'Parent', 'Creator', 'Date') が正確であることを確認してください。")
        return pd.DataFrame()

# ファイルがアップロードされた場合のみ処理を実行
if uploaded_file is not None:
    data = load_data(uploaded_file)

    if not data.empty:
        st.write("### 親子関係の全体図 (Plotly Interactive)")

        G = nx.DiGraph() # Directed Graph (有向グラフ)

        all_drawings = set()
        drawing_details = {}

        # First pass: collect all children and parents to identify root nodes
        all_children = set()
        all_parents = set()
        
        for index, row in data.iterrows():
            child = str(row['Child']).strip()
            parent = str(row['Parent']).strip()
            
            if child:
                all_children.add(child)
            if parent:
                all_parents.add(parent)

        # Identify root nodes (parents that are never children)
        root_nodes = all_parents - all_children

        # Second pass: build graph and node details
        for index, row in data.iterrows():
            child = str(row['Child']).strip()
            parent = str(row['Parent']).strip()
            creator = str(row['Creator']).strip()
            date = str(row['Date']).strip()

            G.add_node(child)
            if parent:
                G.add_node(parent)
                G.add_edge(parent, child)

            if child:
                all_drawings.add(child)
                drawing_details[child] = {
                    'Parent': parent,
                    'Creator': creator,
                    'Date': date
                }
            if parent:
                all_drawings.add(parent)
                if parent not in drawing_details:
                    if parent in root_nodes:
                        # For root nodes, set ROOT indicators
                        drawing_details[parent] = {'Parent': 'ROOT', 'Creator': 'ROOT', 'Date': 'ROOT'}
                    else:
                        drawing_details[parent] = {'Parent': '', 'Creator': '', 'Date': ''}

        # グラフのレイアウトを計算
        # spring_layout を使用。k値を調整してノード間の距離を広げる
        # iterations を増やすことで、より安定した配置になる可能性
        # k: ノード間の理想的な距離。値を大きくするとノードが広がる傾向。
        # iterations: レイアウト計算の繰り返し回数。増やすと計算時間はかかるが、より安定した配置になる可能性。
        pos = nx.spring_layout(G, k=1.5, iterations=100, seed=42) 

        # ノードの作成 (Plotly go.Scatter)
        node_x = []
        node_y = []
        node_text = [] # ノードのラベルとして表示するテキスト
        node_hover_info = [] # ホバー時に表示する詳細テキスト

        for node in G.nodes():
            x, y = pos[node]
            node_x.append(x)
            node_y.append(y)

            details = drawing_details.get(node, {'Parent': '', 'Creator': '', 'Date': ''})
            hover_text = f"<b>図番</b>: {node}<br>"
            hover_text += f"<b>流用元図面</b>: {details['Parent'] if details['Parent'] else 'なし'}<br>"
            hover_text += f"<b>作成者</b>: {details['Creator'] if details['Creator'] else '不明'}<br>"
            hover_text += f"<b>作成日</b>: {details['Date'] if details['Date'] else '不明'}"
            node_hover_info.append(hover_text)
            node_text.append(node) # ノードのラベルとして図番IDを表示

        node_trace = go.Scatter(
            x=node_x, y=node_y,
            mode='markers+text', # マーカー（点）とテキスト（ラベル）を表示
            hoverinfo='text',
            text=node_text, # ノードのラベル
            textposition='bottom center', # ラベルの位置
            marker=dict(
                showscale=False,
                size=20, # ノードサイズを少し大きくする
                color='lightblue', # マーカーの色
                line_width=1, # マーカーの枠線
                line_color='darkblue'
            ),
            hovertext=node_hover_info, # ホバー時に表示する詳細テキスト
            name='Drawings'
        )

        # ★★★ エッジをAnnotationで表現し、矢印を追加 ★★★
        # Annotation を使用することで、より明確な矢印を描画できる
        annotations = []
        for edge in G.edges():
            x0, y0 = pos[edge[0]] # 親ノードの座標
            x1, y1 = pos[edge[1]] # 子ノードの座標
            
            annotations.append(
                go.layout.Annotation(
                    ax=x0, ay=y0, # 矢印の始点 (親ノードの座標)
                    x=x1, y=y1,   # 矢印の終点 (子ノードの座標)
                    xref='x', yref='y', axref='x', ayref='y', # 座標参照系
                    showarrow=True,
                    arrowhead=2, # 矢印のスタイル (2は三角形)
                    arrowsize=2, # 矢印のサイズ
                    arrowwidth=1.5, # 矢印の線の太さ
                    arrowcolor='#888', # 矢印の色
                    standoff=10, # 矢印の先端とノードの距離
                    startstandoff=10 # 矢印の根元とノードの距離
                )
            )

        fig = go.Figure(
            data=[node_trace], # エッジトレースはAnnotationで置き換えるため、ここではノードトレースのみ
            layout=go.Layout(
                title=dict(
                    text='<br>図番親子関係の家系図',
                    font=dict(size=18)
                ),
                showlegend=False, # 凡例は不要
                hovermode='closest', # ホバー時に最も近い要素を選択
                margin=dict(b=20, l=5, r=5, t=40), # マージン
                # 軸は非表示にする（ネットワークグラフのため）
                xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                height=600, # グラフの高さ
                annotations=annotations # ここで Annotation をレイアウトに追加
            )
        )
        
        st.plotly_chart(fig, use_container_width=True)

        # 台帳データをグラフの下に移動し、expanderで折りたたみ可能にする
        with st.expander("### 台帳データを見る (クリックで開閉)"):
            st.dataframe(data)
        
        st.write("---") # 区切り線

        # 詳細情報 (サイドバーに表示)
        st.sidebar.write("### 詳細情報 (選択式)")
        st.sidebar.info("ドロップダウンから図番を選択すると、その詳細情報が表示されます。")

        sorted_drawings = sorted(list(all_drawings))
        
        selected_drawing_id = st.sidebar.selectbox(
            "詳細を表示する図番を選択",
            [''] + sorted_drawings 
        )

        if selected_drawing_id:
            details = drawing_details.get(selected_drawing_id, {'Parent': '', 'Creator': '', 'Date': ''})
            
            st.sidebar.write(f"#### 図番: {selected_drawing_id}")
            st.sidebar.write(f"**流用元図面**: {details['Parent'] if details['Parent'] else 'なし'}")
            st.sidebar.write(f"**作成者**: {details['Creator']}")
            st.sidebar.write(f"**作成日**: {details['Date']}")
        else:
            st.sidebar.info("上記ドロップダウンから図番を選択してください。")

    else:
        st.warning("アップロードされたファイルからデータを読み込めませんでした。")

else:
    st.info("Excelファイルをアップロードすると、台帳データと家系図が表示されます。")

