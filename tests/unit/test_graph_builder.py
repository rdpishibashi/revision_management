"""
Unit tests for utils/graph_builder.py
"""
import sys
import os
import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from utils.graph_builder import (
    GraphBuilder,
    normalize_parent_value,
    find_search_component_nodes,
    compute_edge_curvature,
    BASE_EDGE_ROUNDNESS,
    EDGE_ROUNDNESS_STEP,
    MAX_EDGE_ROUNDNESS,
)


class TestNormalizeParentValue:
    """normalize_parent_value(): 'None' placeholder -> '' """

    def test_lowercase_none_becomes_empty(self):
        assert normalize_parent_value('none') == ''

    def test_uppercase_none_becomes_empty(self):
        assert normalize_parent_value('NONE') == ''

    def test_mixed_case_none_becomes_empty(self):
        assert normalize_parent_value('None') == ''

    def test_none_with_surrounding_whitespace_becomes_empty(self):
        assert normalize_parent_value('  None  ') == ''

    def test_real_drawing_number_is_unchanged(self):
        assert normalize_parent_value('EE3273-601-09B') == 'EE3273-601-09B'

    def test_already_empty_string_is_unchanged(self):
        assert normalize_parent_value('') == ''


def build(rows, dynamic_cols=('Relation',)):
    df = pd.DataFrame(rows)
    builder = GraphBuilder(df, list(dynamic_cols))
    node_details, root_nodes = builder.build()
    return builder, node_details, root_nodes


class TestNoneParentIndependentNode:
    """Child rows whose Parent was normalized to '' become independent nodes
    with their own full data (not the reduced ROOT-only display)."""

    def test_independent_node_keeps_full_data_not_root(self):
        rows = [
            {'Child': 'EE1000-001-01A', 'Parent': '', 'Relation': '完全新規図面'},
            {'Child': 'EE2000-001-01A', 'Parent': 'EE1000-001-01A', 'Relation': '流用'},
        ]
        builder, node_details, root_nodes = build(rows)

        assert 'EE1000-001-01A' not in root_nodes
        assert node_details['EE1000-001-01A'] == {'Relation': '完全新規図面'}

    def test_no_edge_created_for_independent_node(self):
        rows = [
            {'Child': 'EE1000-001-01A', 'Parent': '', 'Relation': '完全新規図面'},
        ]
        builder, _, _ = build(rows)
        edges = builder.get_edges()
        assert edges == []


class TestExplicitEdgesAreSolid:
    """Any row explicitly recorded in the ledger produces a solid edge,
    regardless of the Relation column's value."""

    def test_revup_relation_row_is_solid(self):
        rows = [
            {'Child': 'EE1000-001-01B', 'Parent': 'EE1000-001-01A', 'Relation': 'RevUp'},
        ]
        builder, _, _ = build(rows)
        edges = builder.get_edges()
        assert edges == [('EE1000-001-01A', 'EE1000-001-01B', False)]

    def test_reuse_relation_row_is_solid(self):
        rows = [
            {'Child': 'EE2000-001-01A', 'Parent': 'EE1000-001-01A', 'Relation': '流用'},
        ]
        builder, _, _ = build(rows)
        edges = builder.get_edges()
        assert edges == [('EE1000-001-01A', 'EE2000-001-01A', False)]


class TestInferredRevUpEdgesAreDashed:
    """Same-base, ascending-revision-letter node pairs with no explicit row
    connecting them get an inferred dashed RevUp edge."""

    def test_gap_between_siblings_via_unrelated_rows_is_dashed(self):
        # EE1000-001-01A and EE1000-001-01B never appear together in a row,
        # but both exist as nodes (via unrelated 流用 relationships).
        rows = [
            {'Child': 'EE1000-001-01A', 'Parent': 'EE9999-999-99Z', 'Relation': '流用'},
            {'Child': 'EE8888-888-88Y', 'Parent': 'EE1000-001-01B', 'Relation': '流用'},
        ]
        builder, _, _ = build(rows)
        edges = builder.get_edges()
        assert ('EE1000-001-01A', 'EE1000-001-01B', True) in edges

    def test_existing_explicit_edge_is_not_duplicated_as_dashed(self):
        rows = [
            {'Child': 'EE1000-001-01B', 'Parent': 'EE1000-001-01A', 'Relation': 'RevUp'},
        ]
        builder, _, _ = build(rows)
        edges = builder.get_edges()
        assert edges == [('EE1000-001-01A', 'EE1000-001-01B', False)]
        assert ('EE1000-001-01A', 'EE1000-001-01B', True) not in edges

    def test_chain_connects_only_adjacent_existing_revisions(self):
        # A, C, D exist as nodes (no B) -> expect A-C and C-D, not A-D
        rows = [
            {'Child': 'EE1000-001-01A', 'Parent': 'EE9999-999-99Z', 'Relation': '流用'},
            {'Child': 'EE1000-001-01C', 'Parent': 'EE8888-888-88Y', 'Relation': '流用'},
            {'Child': 'EE1000-001-01D', 'Parent': 'EE7777-777-77X', 'Relation': '流用'},
        ]
        builder, _, _ = build(rows)
        edges = builder.get_edges()
        dashed = {(p, c) for p, c, d in edges if d}
        assert dashed == {('EE1000-001-01A', 'EE1000-001-01C'), ('EE1000-001-01C', 'EE1000-001-01D')}

    def test_different_base_drawing_numbers_produce_no_inferred_edge(self):
        rows = [
            {'Child': 'EE1000-001-01A', 'Parent': 'EE9999-999-99Z', 'Relation': '流用'},
            {'Child': 'EE2000-002-02B', 'Parent': 'EE8888-888-88Y', 'Relation': '流用'},
        ]
        builder, _, _ = build(rows)
        edges = builder.get_edges()
        dashed = [e for e in edges if e[2]]
        assert dashed == []

    def test_none_parent_child_without_sibling_stays_independent(self):
        # Genuinely new drawing (completely-new tag) with no lettered sibling anywhere
        rows = [
            {'Child': 'EE5000-001-01A', 'Parent': '', 'Relation': '完全新規図面'},
        ]
        builder, _, _ = build(rows)
        edges = builder.get_edges()
        assert edges == []

    def test_none_parent_child_with_real_sibling_gets_inferred_dashed_edge(self):
        # EE5000-001-01A recorded as Parent elsewhere; 01B's own row has no
        # parent recorded (normalized to ''), but a sibling exists -> inferred dashed
        rows = [
            {'Child': 'EE9000-000-00Z', 'Parent': 'EE5000-001-01A', 'Relation': '流用'},
            {'Child': 'EE5000-001-01B', 'Parent': '', 'Relation': '完全新規図面'},
        ]
        builder, _, _ = build(rows)
        edges = builder.get_edges()
        assert ('EE5000-001-01A', 'EE5000-001-01B', True) in edges


class TestGetNodeColor:
    """get_node_color(): ノードへの入力エッジの種類（流用/RevUp）の組み合わせで色を決める。
    入力エッジなし(ROOT/独立新規ノード)=白、流用のみ=light green、RevUpのみ=light blue。
    流用とRevUp両方を受け取るノードは流用エッジが削除されるため（get_edges()参照）、
    「両方」の色分類自体が発生しない。"""

    def test_root_placeholder_node_is_white(self):
        rows = [
            {'Child': 'EE2000-001-01A', 'Parent': 'EE1000-001-01A', 'Relation': '流用'},
        ]
        builder, node_details, root_nodes = build(rows)
        assert 'EE1000-001-01A' in root_nodes
        assert builder.get_node_color('EE1000-001-01A') == GraphBuilder.ROOT_COLOR

    def test_independent_new_drawing_with_no_incoming_edge_is_white(self):
        rows = [
            {'Child': 'EE1000-001-01A', 'Parent': '', 'Relation': '完全新規図面'},
        ]
        builder, _, _ = build(rows)
        assert builder.get_node_color('EE1000-001-01A') == GraphBuilder.ROOT_COLOR

    def test_reuse_only_incoming_edge_is_light_green(self):
        rows = [
            {'Child': 'EE2000-001-01A', 'Parent': 'EE1000-001-01A', 'Relation': '流用'},
        ]
        builder, _, _ = build(rows)
        assert builder.get_node_color('EE2000-001-01A') == GraphBuilder.REUSE_COLOR

    def test_explicit_revup_only_incoming_edge_is_light_blue(self):
        rows = [
            {'Child': 'EE1000-001-01B', 'Parent': 'EE1000-001-01A', 'Relation': 'RevUp'},
        ]
        builder, _, _ = build(rows)
        assert builder.get_node_color('EE1000-001-01B') == GraphBuilder.REVUP_COLOR

    def test_inferred_dashed_revup_only_incoming_edge_is_light_blue(self):
        # A, C exist as nodes (no explicit row between them) -> inferred dashed A->C
        rows = [
            {'Child': 'EE1000-001-01A', 'Parent': 'EE9999-999-99Z', 'Relation': '流用'},
            {'Child': 'EE8888-888-88Y', 'Parent': 'EE1000-001-01C', 'Relation': '流用'},
        ]
        builder, _, _ = build(rows)
        assert builder.get_node_color('EE1000-001-01C') == GraphBuilder.REVUP_COLOR

    def test_reuse_edge_deleted_when_explicit_revup_also_present(self):
        # Same node receives an explicit 流用 edge from one parent and an
        # explicit RevUp edge from a different parent -> 流用 edge is deleted,
        # only the RevUp edge (and color) remain.
        rows = [
            {'Child': 'EE1000-001-01B', 'Parent': 'EE9999-999-99Z', 'Relation': '流用'},
            {'Child': 'EE1000-001-01B', 'Parent': 'EE1000-001-01A', 'Relation': 'RevUp'},
        ]
        df = pd.DataFrame(rows)
        builder = GraphBuilder(df, ['Relation'])
        builder.build()
        edges = builder.get_edges()
        assert ('EE9999-999-99Z', 'EE1000-001-01B', False) not in edges
        assert ('EE1000-001-01A', 'EE1000-001-01B', False) in edges
        assert builder.get_node_color('EE1000-001-01B') == GraphBuilder.REVUP_COLOR

    def test_reuse_edge_deleted_when_inferred_revup_also_present(self):
        # OVERVIEW.md example: 34C has an explicit 流用 edge from 26D, and
        # (with 34B absent) an inferred dashed RevUp edge from 34A -> the
        # explicit 流用 edge is deleted, leaving only the inferred RevUp edge.
        rows = [
            {'Child': 'EE3273-608-34A', 'Parent': 'EE3273-608-26D', 'Relation': '流用'},
            {'Child': 'EE3273-608-34C', 'Parent': 'EE3273-608-26D', 'Relation': '流用'},
        ]
        builder, _, _ = build(rows)
        edges = builder.get_edges()
        assert ('EE3273-608-26D', 'EE3273-608-34C', False) not in edges
        assert ('EE3273-608-34A', 'EE3273-608-34C', True) in edges
        assert builder.get_node_color('EE3273-608-34C') == GraphBuilder.REVUP_COLOR

    def test_all_reuse_edges_deleted_when_multiple_reuse_parents_and_revup(self):
        # A child with two explicit 流用 parents and one explicit RevUp parent
        # loses both 流用 edges, keeping only the RevUp edge.
        rows = [
            {'Child': 'EE1000-001-01C', 'Parent': 'EE9999-999-99Z', 'Relation': '流用'},
            {'Child': 'EE1000-001-01C', 'Parent': 'EE8888-888-88Y', 'Relation': '流用'},
            {'Child': 'EE1000-001-01C', 'Parent': 'EE1000-001-01B', 'Relation': 'RevUp'},
        ]
        df = pd.DataFrame(rows)
        builder = GraphBuilder(df, ['Relation'])
        builder.build()
        edges = builder.get_edges()
        assert ('EE9999-999-99Z', 'EE1000-001-01C', False) not in edges
        assert ('EE8888-888-88Y', 'EE1000-001-01C', False) not in edges
        assert ('EE1000-001-01B', 'EE1000-001-01C', False) in edges
        assert builder.get_node_color('EE1000-001-01C') == GraphBuilder.REVUP_COLOR

    def test_unknown_node_id_defaults_to_root_color(self):
        rows = [
            {'Child': 'EE2000-001-01A', 'Parent': 'EE1000-001-01A', 'Relation': '流用'},
        ]
        builder, _, _ = build(rows)
        assert builder.get_node_color('EE9999-999-99Z') == GraphBuilder.ROOT_COLOR


class TestGetDisplayData:
    """get_display_data(): 削除された流用接続の台帳行を、表示用データから除外する。
    グラフ描画・ノード属性が参照する self.data 自体は変更しない。"""

    def test_deleted_reuse_row_is_excluded(self):
        rows = [
            {'Child': 'EE3273-608-34A', 'Parent': 'EE3273-608-26D', 'Relation': '流用'},
            {'Child': 'EE3273-608-34C', 'Parent': 'EE3273-608-26D', 'Relation': '流用'},
        ]
        builder, _, _ = build(rows)
        display_data = builder.get_display_data()
        remaining_pairs = set(zip(display_data['Parent'], display_data['Child']))
        assert ('EE3273-608-26D', 'EE3273-608-34C') not in remaining_pairs
        assert ('EE3273-608-26D', 'EE3273-608-34A') in remaining_pairs

    def test_no_deletion_returns_all_rows_unchanged(self):
        rows = [
            {'Child': 'EE2000-001-01A', 'Parent': 'EE1000-001-01A', 'Relation': '流用'},
        ]
        builder, _, _ = build(rows)
        display_data = builder.get_display_data()
        assert len(display_data) == len(builder.data)

    def test_revup_row_for_the_same_child_is_kept(self):
        rows = [
            {'Child': 'EE1000-001-01B', 'Parent': 'EE9999-999-99Z', 'Relation': '流用'},
            {'Child': 'EE1000-001-01B', 'Parent': 'EE1000-001-01A', 'Relation': 'RevUp'},
        ]
        df = pd.DataFrame(rows)
        builder = GraphBuilder(df, ['Relation'])
        builder.build()
        display_data = builder.get_display_data()
        remaining_pairs = set(zip(display_data['Parent'], display_data['Child']))
        assert ('EE9999-999-99Z', 'EE1000-001-01B') not in remaining_pairs
        assert ('EE1000-001-01A', 'EE1000-001-01B') in remaining_pairs


class TestFindSearchComponentNodes:
    """find_search_component_nodes(): 図番検索によるツリー（連結成分）絞り込み"""

    def _two_tree_setup(self):
        rows = [
            # ツリー1: EE1000系
            {'Child': 'EE1000-001-01B', 'Parent': 'EE1000-001-01A', 'Relation': 'RevUp'},
            {'Child': 'EE2000-002-02A', 'Parent': 'EE1000-001-01B', 'Relation': '流用'},
            # ツリー2: EE3000系（EE1000系とは無関係）
            {'Child': 'EE3000-003-03B', 'Parent': 'EE3000-003-03A', 'Relation': 'RevUp'},
        ]
        builder, _, _ = build(rows)
        all_nodes = builder.all_children | builder.all_parents
        edges = builder.get_edges()
        return all_nodes, edges

    def test_blank_query_returns_all_nodes(self):
        all_nodes, edges = self._two_tree_setup()
        result = find_search_component_nodes(all_nodes, edges, '')
        assert result == all_nodes

    def test_whitespace_only_query_returns_all_nodes(self):
        all_nodes, edges = self._two_tree_setup()
        result = find_search_component_nodes(all_nodes, edges, '   ')
        assert result == all_nodes

    def test_no_match_returns_empty_set(self):
        all_nodes, edges = self._two_tree_setup()
        result = find_search_component_nodes(all_nodes, edges, 'ZZ9999')
        assert result == set()

    def test_partial_match_returns_whole_containing_tree(self):
        all_nodes, edges = self._two_tree_setup()
        result = find_search_component_nodes(all_nodes, edges, '1000-001-01A')
        assert result == {'EE1000-001-01A', 'EE1000-001-01B', 'EE2000-002-02A'}

    def test_match_in_multiple_trees_returns_union_of_both(self):
        all_nodes, edges = self._two_tree_setup()
        # "EE" matches nodes in both trees
        result = find_search_component_nodes(all_nodes, edges, 'EE')
        assert result == all_nodes

    def test_search_is_case_insensitive(self):
        all_nodes, edges = self._two_tree_setup()
        result = find_search_component_nodes(all_nodes, edges, 'ee1000-001-01a')
        assert result == {'EE1000-001-01A', 'EE1000-001-01B', 'EE2000-002-02A'}

    def test_search_normalizes_full_width_input(self):
        all_nodes, edges = self._two_tree_setup()
        # 全角文字での入力でも半角図番にヒットする（NFKC正規化）
        full_width_query = 'ＥＥ１０００－００１－０１Ａ'
        result = find_search_component_nodes(all_nodes, edges, full_width_query)
        assert result == {'EE1000-001-01A', 'EE1000-001-01B', 'EE2000-002-02A'}

    def test_match_reaches_across_inferred_dashed_edge(self):
        # 台帳にない同一base・リビジョン昇順の推測RevUpエッジも連結成分の探索対象に含める
        rows = [
            {'Child': 'EE4000-004-04A', 'Parent': 'EE9999-999-99Z', 'Relation': '流用'},
            {'Child': 'EE4000-004-04C', 'Parent': 'EE8888-888-88Y', 'Relation': '流用'},
        ]
        builder, _, _ = build(rows)
        all_nodes = builder.all_children | builder.all_parents
        edges = builder.get_edges()
        assert ('EE4000-004-04A', 'EE4000-004-04C', True) in edges  # 前提確認

        result = find_search_component_nodes(all_nodes, edges, 'EE4000-004-04A')
        assert 'EE4000-004-04C' in result  # 破線（推測）エッジ経由でも到達できる

    def test_independent_node_matches_only_itself(self):
        rows = [
            {'Child': 'EE5000-005-05A', 'Parent': '', 'Relation': '完全新規図面'},
        ]
        builder, _, _ = build(rows)
        all_nodes = builder.all_children | builder.all_parents
        edges = builder.get_edges()

        result = find_search_component_nodes(all_nodes, edges, 'EE5000-005-05A')
        assert result == {'EE5000-005-05A'}


class TestComputeEdgeCurvature:
    """compute_edge_curvature(): 同一始点の複数エッジを左右交互・徐々に強く湾曲させてファン状にする"""

    def test_single_edge_gets_base_curvature(self):
        edges = [('A', 'B', False)]
        result = compute_edge_curvature(edges)
        assert result == [('A', 'B', False, {'enabled': True, 'type': 'curvedCW', 'roundness': BASE_EDGE_ROUNDNESS})]

    def test_multiple_edges_from_same_source_alternate_direction_and_increase_roundness(self):
        edges = [
            ('P', 'A', False),
            ('P', 'B', False),
            ('P', 'C', False),
            ('P', 'D', False),
        ]
        result = compute_edge_curvature(edges)
        types = [r[3]['type'] for r in result]
        roundness = [r[3]['roundness'] for r in result]

        assert types == ['curvedCW', 'curvedCCW', 'curvedCW', 'curvedCCW']
        assert roundness == [
            BASE_EDGE_ROUNDNESS, BASE_EDGE_ROUNDNESS,
            BASE_EDGE_ROUNDNESS + EDGE_ROUNDNESS_STEP, BASE_EDGE_ROUNDNESS + EDGE_ROUNDNESS_STEP,
        ]

    def test_roundness_is_capped(self):
        edges = [('P', f'child{i}', False) for i in range(20)]
        result = compute_edge_curvature(edges)
        assert all(r[3]['roundness'] <= MAX_EDGE_ROUNDNESS for r in result)

    def test_edges_from_different_sources_have_independent_counters(self):
        edges = [
            ('P1', 'A', False),
            ('P2', 'B', False),
        ]
        result = compute_edge_curvature(edges)
        # 異なる始点ならそれぞれ最初のエッジとして扱われる（インデックスが共有されない）
        assert result[0][3] == {'enabled': True, 'type': 'curvedCW', 'roundness': BASE_EDGE_ROUNDNESS}
        assert result[1][3] == {'enabled': True, 'type': 'curvedCW', 'roundness': BASE_EDGE_ROUNDNESS}

    def test_is_dashed_flag_is_preserved(self):
        edges = [('P', 'A', True)]
        result = compute_edge_curvature(edges)
        assert result[0][2] is True


if __name__ == '__main__':
    sys.exit(pytest.main([__file__, '-v']))
