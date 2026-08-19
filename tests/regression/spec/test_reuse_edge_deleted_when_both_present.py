"""
Spec regression: 2026-08-20, 流用とRevUp両方の入力エッジを持つノードは流用エッジを削除する仕様

受入条件（ユーザーとの確認内容の要約）:
- あるノード（Child）が「流用」の入力エッジと「RevUp」の入力エッジ（台帳に明示
  された行・推測された破線エッジのいずれでもよい）を同時に持つ場合、流用側の
  エッジを削除する（RevUp側は残す）
- 削除は次の両方に適用される: グラフの矢印（get_edges()の結果）、および
  台帳データ表示テーブル（get_display_data()の結果）
- 1つのノードに複数の流用元がある場合、RevUpを1本でも持てば流用エッジは全て削除される
- 流用のみ、またはRevUpのみを持つノードは削除の対象外（従来通り表示される）
- Relation列が存在しない台帳では流用/RevUpどちらとも判定できないため、削除は発生しない

境界:
- ノード自身の属性（node_dynamic_details、ホバーテキスト等）や root ノード判定は
  台帳の生データ（self.data）を元にしたままであり、この削除の影響を受けない
"""
import sys
import os
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from utils.graph_builder import GraphBuilder


def test_explicit_reuse_edge_deleted_when_explicit_revup_also_present():
    df = pd.DataFrame([
        {'Child': 'EE1000-001-01B', 'Parent': 'EE9999-999-99Z', 'Relation': '流用'},
        {'Child': 'EE1000-001-01B', 'Parent': 'EE1000-001-01A', 'Relation': 'RevUp'},
    ])
    builder = GraphBuilder(df, ['Relation'])
    builder.build()
    edges = builder.get_edges()

    assert ('EE9999-999-99Z', 'EE1000-001-01B', False) not in edges
    assert ('EE1000-001-01A', 'EE1000-001-01B', False) in edges
    assert builder.get_node_color('EE1000-001-01B') == GraphBuilder.REVUP_COLOR


def test_explicit_reuse_edge_deleted_when_inferred_revup_also_present():
    # OVERVIEW.md の例: 34C は台帳明記の流用（26D->34C）と、34Bが存在しない
    # ために推測される破線RevUp（34A->34C）の両方を受け取る
    df = pd.DataFrame([
        {'Child': 'EE3273-608-34A', 'Parent': 'EE3273-608-26D', 'Relation': '流用'},
        {'Child': 'EE3273-608-34C', 'Parent': 'EE3273-608-26D', 'Relation': '流用'},
    ])
    builder = GraphBuilder(df, ['Relation'])
    builder.build()
    edges = builder.get_edges()

    assert ('EE3273-608-26D', 'EE3273-608-34C', False) not in edges
    assert ('EE3273-608-34A', 'EE3273-608-34C', True) in edges
    assert builder.get_node_color('EE3273-608-34C') == GraphBuilder.REVUP_COLOR


def test_all_reuse_edges_deleted_for_child_with_multiple_reuse_parents():
    df = pd.DataFrame([
        {'Child': 'EE1000-001-01C', 'Parent': 'EE9999-999-99Z', 'Relation': '流用'},
        {'Child': 'EE1000-001-01C', 'Parent': 'EE8888-888-88Y', 'Relation': '流用'},
        {'Child': 'EE1000-001-01C', 'Parent': 'EE1000-001-01B', 'Relation': 'RevUp'},
    ])
    builder = GraphBuilder(df, ['Relation'])
    builder.build()
    edges = builder.get_edges()

    assert ('EE9999-999-99Z', 'EE1000-001-01C', False) not in edges
    assert ('EE8888-888-88Y', 'EE1000-001-01C', False) not in edges
    assert ('EE1000-001-01B', 'EE1000-001-01C', False) in edges


def test_reuse_only_child_is_not_affected():
    df = pd.DataFrame([
        {'Child': 'EE2000-001-01A', 'Parent': 'EE1000-001-01A', 'Relation': '流用'},
    ])
    builder = GraphBuilder(df, ['Relation'])
    builder.build()
    edges = builder.get_edges()

    assert ('EE1000-001-01A', 'EE2000-001-01A', False) in edges
    assert builder.get_node_color('EE2000-001-01A') == GraphBuilder.REUSE_COLOR


def test_revup_only_child_is_not_affected():
    df = pd.DataFrame([
        {'Child': 'EE1000-001-01B', 'Parent': 'EE1000-001-01A', 'Relation': 'RevUp'},
    ])
    builder = GraphBuilder(df, ['Relation'])
    builder.build()
    edges = builder.get_edges()

    assert ('EE1000-001-01A', 'EE1000-001-01B', False) in edges
    assert builder.get_node_color('EE1000-001-01B') == GraphBuilder.REVUP_COLOR


def test_ledger_without_relation_column_triggers_no_deletion():
    df = pd.DataFrame([
        {'Child': 'EE5283-601-01C', 'Parent': 'EE3273-601-09B', 'Function': '新法規対応'},
    ])
    builder = GraphBuilder(df, ['Function'])
    builder.build()
    edges = builder.get_edges()

    assert ('EE3273-601-09B', 'EE5283-601-01C', False) in edges
    display_data = builder.get_display_data()
    assert len(display_data) == len(df)


def test_deleted_reuse_row_excluded_from_display_data_but_node_attributes_unaffected():
    df = pd.DataFrame([
        {'Child': 'EE3273-608-34A', 'Parent': 'EE3273-608-26D', 'Relation': '流用', 'Title': 'A図'},
        {'Child': 'EE3273-608-34C', 'Parent': 'EE3273-608-26D', 'Relation': '流用', 'Title': 'C図'},
    ])
    builder = GraphBuilder(df, ['Relation', 'Title'])
    node_dynamic_details, _ = builder.build()

    display_data = builder.get_display_data()
    remaining_pairs = set(zip(display_data['Parent'], display_data['Child']))
    assert ('EE3273-608-26D', 'EE3273-608-34C') not in remaining_pairs
    assert ('EE3273-608-26D', 'EE3273-608-34A') in remaining_pairs

    # ノード自身の属性（ホバーテキスト等に使う node_dynamic_details）は
    # 台帳表示のフィルタと独立して、削除されたはずの行の情報を保持し続ける
    assert node_dynamic_details['EE3273-608-34C']['Title'] == 'C図'
