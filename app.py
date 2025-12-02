import streamlit as st
import pandas as pd
import graphviz
import unicodedata # 全角変換のためにインポート

# ページのレイアウトをワイドに設定
st.set_page_config(layout="wide")

# アプリケーションのタイトルを設定
st.title("親子関係グラフ")
st.write("親子関係台帳をアップロードして親子関係グラフを表示します。")

# 1. ファイルアップローダーの設置
uploaded_file = st.file_uploader(
    "親子関係台帳Excelファイル (.xlsx) をここにドラッグ＆ドロップするか、クリックして選択してください",
    type=["xlsx"]
)

# 2. Excelファイルを読み込む関数
@st.cache_data(ttl=600) # データを10分間キャッシュする
def load_data(file_object):
    """
    アップロードされたExcelファイルオブジェクトからデータを読み込み、DataFrameとして返す。
    """
    try:
#        df = pd.read_excel(file_object, sheet_name='Sheet1')
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

        # 全ての列を文字列型に変換してArrow変換エラーを防ぐ
        for col in df.columns:
            df[col] = df[col].astype(str).str.strip()

        return df
    except Exception as e:
        st.error(f"データの読み込み中にエラーが発生しました: {e}")
        st.info("Excelファイルの必要なカラム名 ('Child', 'Parent') が正確であることを確認してください。また、C列以降のタイトル名も確認してください。")
        return pd.DataFrame()

# ファイルがアップロードされた場合のみ処理を実行
if uploaded_file is not None:
    data = load_data(uploaded_file)

    if not data.empty:
        st.write("### 親子関係グラフ")

        # Graphvizのグラフオブジェクトを作成
        # format='pdf' に変更してPDF出力を指定
        dot = graphviz.Digraph(comment='Family Tree', format='pdf', graph_attr={'rankdir': 'TB'})

        node_dynamic_details = {}
        dynamic_cols_for_display = [col for col in data.columns if col not in ['Child', 'Parent']]

        # First pass: collect all children and parents
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

        # Second pass: build node details
        for index, row in data.iterrows():
            child = str(row['Child']).strip()
            parent = str(row['Parent']).strip()

            current_node_details = {}
            for col in dynamic_cols_for_display:
                current_node_details[col] = str(row[col]).strip()

            # Childの属性を設定（Childのレコードの属性を使用）
            if child:
                if child not in node_dynamic_details:
                    node_dynamic_details[child] = {}
                node_dynamic_details[child].update(current_node_details)

            # Parentが存在する場合、辞書に登録（属性は後で設定）
            if parent:
                if parent not in node_dynamic_details:
                    node_dynamic_details[parent] = {}

        # Rootノードに対して特別な属性を設定
        for root_node in root_nodes:
            if root_node in node_dynamic_details:
                node_dynamic_details[root_node] = {
                    'Relation': 'ROOT',
                    'Title': '',
                    'Subtitle': ''
                }

        NODE_FILL_COLOR = '#F0F8FF' # AliceBlue (デフォルト)
        RELATION_REUSE_COLOR = '#FFFFE0' # LightYellow (流用用)

        for drawing_id in sorted(node_dynamic_details.keys()):
            details = node_dynamic_details[drawing_id]

            full_width_drawing_id = unicodedata.normalize('NFKC', drawing_id)

            label_html = f'''<
            <TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0">
                <TR><TD ALIGN="CENTER"><B><FONT POINT-SIZE="20">{full_width_drawing_id}</FONT></B></TD></TR>
            '''

            # Rootノードの場合は、Relation、Title、Subtitleのみ表示
            if drawing_id in root_nodes:
                relation_value = details.get('Relation', 'ROOT')
                title_value = details.get('Title', '')
                subtitle_value = details.get('Subtitle', '')

                label_html += f'''
                <TR><TD ALIGN="CENTER" COLSPAN="2"><FONT POINT-SIZE="10">Relation: {relation_value}</FONT></TD></TR>
                <TR><TD ALIGN="CENTER" COLSPAN="2"><FONT POINT-SIZE="10">Title: {title_value}</FONT></TD></TR>
                <TR><TD ALIGN="CENTER" COLSPAN="2"><FONT POINT-SIZE="10">Subtitle: {subtitle_value}</FONT></TD></TR>
                '''
            else:
                # 通常のノードの場合、全ての属性を表示
                for col_name in dynamic_cols_for_display:
                    value = details.get(col_name, '不明')
                    label_html += f'''
                <TR><TD ALIGN="CENTER" COLSPAN="2"><FONT POINT-SIZE="10">{col_name}: {value}</FONT></TD></TR>
                    '''

            label_html += '</TABLE>>'

            # Relationが「流用」の場合は薄い黄色、それ以外はデフォルトの色
            fill_color = NODE_FILL_COLOR
            if 'Relation' in details and details['Relation'] == '流用':
                fill_color = RELATION_REUSE_COLOR

            dot.node(drawing_id, label=label_html, shape='box', style='filled', fillcolor=fill_color)

        for index, row in data.iterrows():
            child = str(row['Child']).strip()
            parent = str(row['Parent']).strip()
            if parent and child:
                dot.edge(parent, child)

        # グラフを中央に表示するためにカラムを使用
        col1, col2, col3 = st.columns([1, 6, 1])
        with col2:
            # Streamlitでグラフを表示 (PNG形式で表示)
            st.graphviz_chart(dot)
            
            # PDFダウンロードボタンをグラフの下に配置
            st.write("---")
            st.write("#### グラフをPDFでダウンロード")
            st.info("PDFは複雑な図でも拡大しても鮮明に表示されます。")
            
            try:
                # GraphvizでPDFデータを生成
                # render() メソッドはファイルを生成しますが、pipe() メソッドはバイナリデータを返します。
                pdf_data = dot.pipe(format='pdf')
                
                st.download_button(
                    label="PDFファイルをダウンロード",
                    data=pdf_data,
                    file_name="family_tree.pdf",
                    mime="application/pdf"
                )
            except Exception as e:
                st.error(f"PDF生成中にエラーが発生しました: {e}")
                st.warning("Graphviz本体が正しくインストールされ、PATHが通っているか確認してください。")


        # 台帳データをグラフの下に移動し、expanderで折りたたみ可能にする
        with st.expander("### 親子関係台帳データを見る（クリックで開閉）"):
            st.dataframe(data)
        
        st.write("---")

    else:
        st.warning("アップロードされたファイルからデータを読み込めませんでした。")

else:
    st.info("親子関係台帳（Excelファイル）をアップロードすると、親子関係グラフを表示します。")
