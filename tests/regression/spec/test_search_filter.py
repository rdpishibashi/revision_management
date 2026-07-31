"""
Spec regression: 2026-07-31, 図番検索によるツリー絞り込み仕様

受入条件（ユーザーとの確認内容の要約）:
- サイドバーの検索欄に図番（Child/Parentどちらでも）の一部を入力すると、
  部分一致（大文字小文字を区別しない）でヒットした図番が属するツリー
  （連結成分）だけを表示する
- 複数の図番がヒットし、それぞれ異なるツリーに属する場合は、該当する
  全ツリーを並べて表示する（1件に絞り込まない）
- 検索欄が空欄の場合は、従来通り全体を表示する（フィルタなし）
- 一致する図番が1件もない場合は空集合を返す（呼び出し側で「該当なし」表示に使う）
"""
import sys
import os
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from utils.graph_builder import GraphBuilder, find_search_component_nodes


def _build_two_tree_graph():
    rows = [
        {'Child': 'EE1000-001-01B', 'Parent': 'EE1000-001-01A', 'Relation': 'RevUp'},
        {'Child': 'EE2000-002-02A', 'Parent': 'EE1000-001-01B', 'Relation': '流用'},
        {'Child': 'EE3000-003-03B', 'Parent': 'EE3000-003-03A', 'Relation': 'RevUp'},
    ]
    df = pd.DataFrame(rows)
    builder = GraphBuilder(df, ['Relation'])
    builder.build()
    all_nodes = builder.all_children | builder.all_parents
    edges = builder.get_edges()
    return all_nodes, edges


def test_blank_query_shows_everything():
    all_nodes, edges = _build_two_tree_graph()
    result = find_search_component_nodes(all_nodes, edges, '')
    assert result == all_nodes


def test_partial_match_shows_only_the_containing_tree():
    all_nodes, edges = _build_two_tree_graph()
    result = find_search_component_nodes(all_nodes, edges, '1000-001')
    assert result == {'EE1000-001-01A', 'EE1000-001-01B', 'EE2000-002-02A'}
    assert 'EE3000-003-03A' not in result
    assert 'EE3000-003-03B' not in result


def test_match_across_multiple_trees_shows_all_of_them():
    all_nodes, edges = _build_two_tree_graph()
    result = find_search_component_nodes(all_nodes, edges, 'EE')  # 両ツリーにヒット
    assert result == all_nodes


def test_no_match_returns_empty_set():
    all_nodes, edges = _build_two_tree_graph()
    result = find_search_component_nodes(all_nodes, edges, 'NOT-A-REAL-DRAWING')
    assert result == set()
