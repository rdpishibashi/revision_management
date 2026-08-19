"""
Spec regression: 2026-08-06, ノード色を入力エッジの種類で決める仕様
2026-08-20 更新: 流用とRevUp両方の入力エッジを持つノードは流用エッジ自体が
削除される仕様に変更されたため（test_reuse_edge_deleted_when_both_present.py
参照）、「両方」の色分類（旧 light yellow）は発生しなくなった。本ファイルの
受入条件からも該当項目を削除。

受入条件（ユーザーとの確認内容の要約）:
- 入力エッジ（矢印）を1つも受け取らないノード（ROOTノード、または親を持たない
  独立新規ノード）は白 (#FFFFFF)
- 流用エッジのみを受け取るノードは light green (#90EE90)
- RevUpエッジのみを受け取るノード（台帳に明示された行・推測された破線エッジの
  いずれでもよい）は light blue (#ADD8E6)

境界:
- 色はノード自身の行が持つ Relation 属性ではなく、そのノードへの入力エッジの
  種類の集合で決まる
"""
import sys
import os
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from utils.graph_builder import GraphBuilder


def test_root_and_independent_nodes_are_white():
    df = pd.DataFrame([
        {'Child': 'EE3273-608-34A', 'Parent': 'EE3273-608-26D', 'Relation': '流用'},
        {'Child': 'EE9000-001-01A', 'Parent': '', 'Relation': '完全新規図面'},
    ])
    builder = GraphBuilder(df, ['Relation'])
    builder.build()

    assert builder.get_node_color('EE3273-608-26D') == GraphBuilder.ROOT_COLOR  # ROOTノード
    assert builder.get_node_color('EE9000-001-01A') == GraphBuilder.ROOT_COLOR  # 独立新規ノード


def test_node_receiving_only_reuse_edge_is_light_green():
    df = pd.DataFrame([
        {'Child': 'EE3273-608-34A', 'Parent': 'EE3273-608-26D', 'Relation': '流用'},
    ])
    builder = GraphBuilder(df, ['Relation'])
    builder.build()

    assert builder.get_node_color('EE3273-608-34A') == GraphBuilder.REUSE_COLOR


def test_node_with_both_reuse_and_inferred_revup_keeps_only_revup_color():
    # 統合図面管理台帳.xlsx 相当のケース: 34C は台帳明記の流用（26D->34C）と、
    # 34Bが存在しないために推測される破線RevUp（34A->34C）の両方を受け取るが、
    # 流用エッジは削除されるため RevUp のみの色になる
    df = pd.DataFrame([
        {'Child': 'EE3273-608-34A', 'Parent': 'EE3273-608-26D', 'Relation': '流用'},
        {'Child': 'EE3273-608-34C', 'Parent': 'EE3273-608-26D', 'Relation': '流用'},
        {'Child': 'EE3273-608-34D', 'Parent': 'EE3273-608-34C', 'Relation': 'RevUp'},
    ])
    builder = GraphBuilder(df, ['Relation'])
    builder.build()
    edges = builder.get_edges()

    assert ('EE3273-608-34A', 'EE3273-608-34C', True) in edges  # 前提確認: 推測破線
    assert ('EE3273-608-26D', 'EE3273-608-34C', False) not in edges  # 流用エッジは削除される
    assert builder.get_node_color('EE3273-608-34C') == GraphBuilder.REVUP_COLOR
    # 34D は明示RevUpのみを受け取る
    assert builder.get_node_color('EE3273-608-34D') == GraphBuilder.REVUP_COLOR


def test_ledger_without_relation_column_defaults_every_node_to_white():
    # Relation列自体が存在しない台帳（例: shutter.xlsx）でもクラッシュせず、
    # 流用/RevUpどちらとも判定できないため全ノードが白扱いになる
    df = pd.DataFrame([
        {'Child': 'EE5283-601-01C', 'Parent': 'EE3273-601-09B', 'Function': '新法規対応'},
    ])
    builder = GraphBuilder(df, ['Function'])
    builder.build()

    assert builder.get_node_color('EE5283-601-01C') == GraphBuilder.ROOT_COLOR
