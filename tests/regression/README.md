# tests/regression/

## bugfix/

| 不具合ID | 内容 | 対応テスト | 修正内容の要点 |
|---|---|---|---|
| 2026-07-31 None-parent | Parent列が"None"（大文字小文字問わず）の図面が、共有の"None"ノードにぶら下がり、属性が`{'Relation': 'ROOT'}`のみに縮退して表示されていた | `bugfix/test_none_parent_treated_as_independent.py` | `utils/graph_builder.normalize_parent_value()`を新設し、`app.py`の`load_data()`でParent列に適用。"None"系プレースホルダーを空文字列に正規化し、独立ノード（自身の全属性を保持）として扱う |
| 2026-07-31 Pyvis重複エッジ | インタラクティブ(Pyvis)表示で、同一始点から出る複数の実線エッジが一直線に重なり、片方が完全に隠れて見えなくなっていた（PDF/Graphvizでは正しく2本表示）。図番検索で単一ツリーに絞り込むと特に顕在化。第1版（一律`edges.smooth`）だけでは4本以上重なるケース（例: EE3273-608-26Dから34A/34B/34C/34Dへの4本）でまだ見分けにくかった | `bugfix/test_pyvis_overlapping_edges.py` | `utils/graph_builder.compute_edge_curvature()`を新設し、同一始点から出るエッジを左右交互（curvedCW/curvedCCW）・徐々に強く湾曲させてファン状に表示するよう変更 |

## spec/

| 受入条件 | 対応テスト |
|---|---|
| 台帳に明示的に記録された行はRelation値によらず実線 | `spec/test_revup_dashed_edges.py::test_all_ledger_rows_are_solid_regardless_of_relation_value` |
| 台帳にない同一base・リビジョン昇順の隣接ペアは推測RevUpとして破線 | `spec/test_revup_dashed_edges.py::test_gap_in_revision_chain_is_inferred_and_dashed` |
| 全リビジョンが台帳に記録済みなら推測エッジは0件 | `spec/test_revup_dashed_edges.py::test_fully_recorded_chain_produces_no_dashed_edges` |
| base（同一図番）が異なるノード同士は接続しない | `spec/test_revup_dashed_edges.py::test_unrelated_base_numbers_are_not_connected` |
| 検索欄が空欄なら全体を表示する | `spec/test_search_filter.py::test_blank_query_shows_everything` |
| 部分一致した図番の連結成分（ツリー）のみに絞り込む | `spec/test_search_filter.py::test_partial_match_shows_only_the_containing_tree` |
| 複数ツリーにヒットした場合は該当する全ツリーを表示する | `spec/test_search_filter.py::test_match_across_multiple_trees_shows_all_of_them` |
| 一致なしの場合は空集合を返す | `spec/test_search_filter.py::test_no_match_returns_empty_set` |
