"""
Bugfix regression: 2026-07-31, Parent="None" displayed as a shared parent node

不具合: Parent列に "None"（大文字小文字を問わず）が入力されている図面は、
GraphBuilder が "None" という文字列をそのまま親図番として扱っていたため、
複数の独立した図面が共有の "None" ノードにぶら下がる形で表示され、かつ
_set_root_node_attributes() によって属性が {'Relation': 'ROOT'} のみに
縮退してしまっていた（本来のデータ: Function/Relation等が失われる）。

修正: utils/graph_builder.normalize_parent_value() で "None" 系プレースホルダーを
空文字列に正規化してから GraphBuilder に渡す。空文字列の Parent は
「親なし」として扱われ、共有ノードへの誤接続もエッジ生成もされない。

保証したいこと:
- Parent="None"（大文字小文字混在含む）の図面は、独立ノードとして表示され、
  自身の行が持つ全属性（動的列データ）がそのまま表示されること
- 複数の "None" 親図面が、誤って同一の共有ノードに接続されないこと
"""
import sys
import os
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from utils.graph_builder import GraphBuilder, normalize_parent_value


def test_none_parent_placeholder_normalized_regardless_of_case():
    for placeholder in ['None', 'NONE', 'none', 'NoNe', '  None  ']:
        assert normalize_parent_value(placeholder) == ''


def test_none_parent_drawings_do_not_share_a_common_node():
    df = pd.DataFrame([
        {'Child': 'EE1111-001-01A', 'Parent': normalize_parent_value('None'), 'Function': '新規A'},
        {'Child': 'EE2222-002-02A', 'Parent': normalize_parent_value('none'), 'Function': '新規B'},
    ])
    builder = GraphBuilder(df, ['Function'])
    node_details, root_nodes = builder.build()

    # 以前の実装ではここに "None" という共有ノードが生成されていた
    assert 'None' not in node_details
    assert 'none' not in node_details

    edges = builder.get_edges()
    assert edges == []  # 独立ノードのため、どちらの図面にもエッジが生成されない


def test_none_parent_drawing_keeps_its_own_full_data_not_root_only():
    df = pd.DataFrame([
        {'Child': 'EE1111-001-01A', 'Parent': normalize_parent_value('None'), 'Function': '新規A', 'Relation': '完全新規図面'},
    ])
    builder = GraphBuilder(df, ['Function', 'Relation'])
    node_details, root_nodes = builder.build()

    assert 'EE1111-001-01A' not in root_nodes
    # 以前の実装ではROOTノード扱いで {'Relation': 'ROOT'} のみに縮退していた
    assert node_details['EE1111-001-01A'] == {'Function': '新規A', 'Relation': '完全新規図面'}
