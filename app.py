import streamlit as st
import pandas as pd
import graphviz
import unicodedata # 全角変換のためにインポート
from pyvis.network import Network
import streamlit.components.v1 as components
import tempfile
import os
import platform

# Import custom utilities
from utils.formatters import format_hover_text
from utils.graph_builder import GraphBuilder

# ページのレイアウトをワイドに設定
st.set_page_config(layout="wide")

# 日本語フォントを取得する関数
def get_japanese_font():
    """
    システムに応じて利用可能な日本語フォントを返す
    Streamlit Cloud (Linux) 用に複数のフォールバック設定
    """
    system = platform.system()

    if system == 'Darwin':  # macOS
        return 'Hiragino Sans'
    elif system == 'Windows':
        return 'MS Gothic'
    else:  # Linux (including Streamlit Cloud)
        # Streamlit Cloud uses Debian/Ubuntu
        # fonts-noto-cjk package provides these fonts
        # Try multiple font names as fallback
        linux_fonts = [
            'Noto Sans CJK JP',
            'Noto Sans JP',
            'IPAGothic',
            'VL Gothic',
            'DejaVu Sans'  # Fallback (doesn't support Japanese well, but won't crash)
        ]
        # Return first font (will be installed via packages.txt)
        return linux_fonts[0]

# 日本語フォント名を取得
JAPANESE_FONT = get_japanese_font()

# サイドバーでグラフエンジンを選択
st.sidebar.title("表示設定")
graph_engine = st.sidebar.radio(
    "グラフ表示スタイル",
    options=["インタラクティブ", "固定表示・PDF出力"],
    index=0,
    help="インタラクティブはズーム・パン・ドラッグ可能、固定表示はPDF出力可能"
)

# デバッグ情報（フォント設定を表示）
with st.sidebar.expander("ℹ️ システム情報", expanded=False):
    st.text(f"OS: {platform.system()}")
    st.text(f"使用フォント: {JAPANESE_FONT}")

# アプリケーションのタイトルを設定
st.title("図番親子関係グラフ")
st.write("図番親子関係台帳をアップロードして図番の親子関係グラフを表示します。")

# エンジンに応じた説明を表示
if graph_engine == "インタラクティブ":
    st.info("**インタラクティブ・モード**：グラフをズーム・パン・ドラッグできます。ノードをクリックすると詳細データが表示されます。")
else:
    st.info("**固定表示モード**：固定画像を表示します。拡大しても鮮明表示できるPDFファイルを出力できます。")

# 1. ファイルアップローダーの設置
uploaded_file = st.file_uploader(
    "図番親子関係台帳Excelファイル (.xlsx) をここにドラッグ＆ドロップするか、クリックして選択してください",
    type=["xlsx"]
)

# 2. Excelファイルを読み込む関数
@st.cache_data(ttl=600) # データを10分間キャッシュする
def load_data(file_object):
    """
    アップロードされたExcelファイルオブジェクトからデータを読み込み、DataFrameとして返す。
    """
    try:
        df = pd.read_excel(file_object)

        # 必須カラムを定義 (A列, B列に相当)
        fixed_columns = ['Child', 'Parent']

        # 必要な固定カラムがDataFrameに存在するかチェック
        if not all(col in df.columns for col in fixed_columns):
            missing_cols = [col for col in fixed_columns if col not in df.columns]
            st.error(f"エラー: Excelファイルに必要な固定カラムが見つかりません。以下のカラムが必要です: {', '.join(fixed_columns)}。見つからないカラム: {', '.join(missing_cols)}")
            return pd.DataFrame()

        # C列以降の動的カラムを取得
        dynamic_columns = [col for col in df.columns if col not in fixed_columns]

        # 全てのカラムを選択し、順序を保証する (固定カラムが先頭に来るように)
        all_columns = fixed_columns + dynamic_columns
        df = df[all_columns]

        # NaN (欠損値) を空文字列に変換して、グラフ描画や表示でエラーが出ないようにする
        df = df.fillna('')

        # 日付が datetime オブジェクトとして読み込まれる場合があるので、文字列に変換
        if 'Date' in df.columns:
            df['Date'] = df['Date'].apply(lambda x: x.strftime('%Y/%m/%d') if isinstance(x, pd.Timestamp) else str(x).strip())

        # Recorded Date を yy-mm-dd hh:mm:ss 形式に変換
        if 'Recorded Date' in df.columns:
            df['Recorded Date'] = df['Recorded Date'].apply(
                lambda x: x.strftime('%y-%m-%d %H:%M:%S') if isinstance(x, pd.Timestamp) else str(x).strip()
            )

        # 全ての列を文字列型に変換してArrow変換エラーを防ぐ
        for col in df.columns:
            df[col] = df[col].astype(str).str.strip()

        return df
    except Exception as e:
        st.error(f"データの読み込み中にエラーが発生しました: {e}")
        st.info("Excelファイルの必要なカラム名 ('Child', 'Parent') が正確であることを確認してください。また、C列以降のタイトル名も確認してください。")
        return pd.DataFrame()


def render_graphviz(data):
    """Graphvizを使用してグラフを描画"""
    st.write("### 図番親子関係グラフ（固定画像）")

    # Graphvizのグラフオブジェクトを作成
    # 日本語表示のためにフォントを指定
    dot = graphviz.Digraph(
        comment='Family Tree',
        format='pdf',
        graph_attr={
            'rankdir': 'TB',
            'fontname': JAPANESE_FONT
        },
        node_attr={
            'fontname': JAPANESE_FONT
        },
        edge_attr={
            'fontname': JAPANESE_FONT
        }
    )

    # Use GraphBuilder to extract common logic
    dynamic_cols_for_display = [col for col in data.columns if col not in ['Child', 'Parent']]
    builder = GraphBuilder(data, dynamic_cols_for_display)
    node_dynamic_details, root_nodes = builder.build()

    for drawing_id in sorted(node_dynamic_details.keys()):
        details = node_dynamic_details[drawing_id]

        full_width_drawing_id = unicodedata.normalize('NFKC', drawing_id)

        label_html = f'''<
        <TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0">
            <TR><TD ALIGN="CENTER"><B><FONT POINT-SIZE="20">{full_width_drawing_id}</FONT></B></TD></TR>
        '''

        # Rootノードの場合は、Relationのみ表示
        if drawing_id in root_nodes:
            relation_value = details.get('Relation', 'ROOT')

            label_html += f'''
            <TR><TD ALIGN="CENTER" COLSPAN="2"><FONT POINT-SIZE="10">Relation: {relation_value}</FONT></TD></TR>
            '''
        else:
            # 通常のノードの場合、全ての属性を表示
            for col_name in dynamic_cols_for_display:
                value = details.get(col_name, '不明')
                label_html += f'''
            <TR><TD ALIGN="CENTER" COLSPAN="2"><FONT POINT-SIZE="10">{col_name}: {value}</FONT></TD></TR>
                '''

        label_html += '</TABLE>>'

        # Use GraphBuilder to determine node color
        fill_color = builder.get_node_color(details)

        dot.node(drawing_id, label=label_html, shape='box', style='filled', fillcolor=fill_color)

    # Add edges using GraphBuilder
    for parent, child in builder.get_edges():
        dot.edge(parent, child)

    # グラフを中央に表示するためにカラムを使用
    col1, col2, col3 = st.columns([1, 6, 1])
    with col2:
        # Streamlitでグラフを表示 (PNG形式で表示)
        st.graphviz_chart(dot)

        # PDFダウンロードボタンをグラフの下に配置
        st.write("---")
        st.write("#### 図番親子関係グラフをPDFでダウンロード")
        st.info("PDFは拡大しても鮮明な表示が可能です。")

        try:
            # GraphvizでPDFデータを生成
            pdf_data = dot.pipe(format='pdf')

            # Custom CSS for blue button
            st.markdown("""
                <style>
                .stDownloadButton button {
                    background-color: #0068C9 !important;
                    color: white !important;
                }
                .stDownloadButton button:hover {
                    background-color: #0054A3 !important;
                }
                </style>
            """, unsafe_allow_html=True)

            st.download_button(
                label="PDFファイルをダウンロード",
                data=pdf_data,
                file_name="family_tree.pdf",
                mime="application/pdf"
            )
        except Exception as e:
            st.error(f"PDF生成中にエラーが発生しました: {e}")
            st.warning("Graphviz本体が正しくインストールされ、PATHが通っているか確認してください。")


def render_pyvis(data):
    """Pyvisを使用してインタラクティブなグラフを描画"""
    st.write("### 図番親子関係グラフ（インタラクティブ）")

    # Use GraphBuilder to extract common logic
    dynamic_cols_for_display = [col for col in data.columns if col not in ['Child', 'Parent']]
    builder = GraphBuilder(data, dynamic_cols_for_display)
    node_dynamic_details, root_nodes = builder.build()

    # Pyvisネットワークを作成
    net = Network(height='800px', width='100%', directed=True, notebook=False)

    # ノードを追加
    for drawing_id in sorted(node_dynamic_details.keys()):
        details = node_dynamic_details[drawing_id]
        full_width_drawing_id = unicodedata.normalize('NFKC', drawing_id)

        # Use formatters utility to create hover text
        is_root = drawing_id in root_nodes
        title_html = format_hover_text(full_width_drawing_id, details, is_root, dynamic_cols_for_display)

        # Use GraphBuilder to determine node color
        fill_color = builder.get_node_color(details)

        # ノードを追加
        net.add_node(
            drawing_id,
            label=full_width_drawing_id,
            title=title_html,
            color=fill_color,
            shape='box',
            font={'size': 20}
        )

    # Add edges using GraphBuilder
    for parent, child in builder.get_edges():
        net.add_edge(parent, child)

    # 階層的レイアウトを設定
    net.set_options("""
    {
      "layout": {
        "hierarchical": {
          "enabled": true,
          "direction": "UD",
          "sortMethod": "directed",
          "nodeSpacing": 200,
          "levelSeparation": 75,
          "shakeTowards": "roots"
        }
      },
      "physics": {
        "enabled": false
      },
      "interaction": {
        "navigationButtons": true,
        "keyboard": true,
        "hover": true,
        "zoomView": true
      }
    }
    """)

    # HTMLファイルを一時ディレクトリに保存
    with tempfile.NamedTemporaryFile(delete=False, suffix='.html', mode='w', encoding='utf-8') as tmp_file:
        net.save_graph(tmp_file.name)
        tmp_file_path = tmp_file.name

    # HTMLファイルを読み込んで表示
    with open(tmp_file_path, 'r', encoding='utf-8') as f:
        html_content = f.read()

    # iframeとして表示
    components.html(html_content, height=850, scrolling=True)

    # 一時ファイルを削除
    try:
        os.unlink(tmp_file_path)
    except:
        pass


# ファイルがアップロードされた場合のみ処理を実行
if uploaded_file is not None:
    data = load_data(uploaded_file)

    if not data.empty:
        # 選択されたエンジンに応じてグラフを描画
        if graph_engine == "インタラクティブ":
            render_pyvis(data)
        else:
            render_graphviz(data)

        # 台帳データをグラフの下に移動し、expanderで折りたたみ可能にする
        with st.expander("### 図番親子関係台帳データを見る（クリックで開閉）"):
            st.dataframe(data)

        st.write("---")

    else:
        st.warning("アップロードされたファイルからデータを読み込めませんでした。")

else:
    st.info("図番親子関係台帳（Excelファイル）をアップロードすると、図番親子関係グラフを表示します。")
