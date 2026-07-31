"""
Spec regression: 2026-07-31, 矢印の実線・破線の振り分け仕様

受入条件（ユーザーとの確認内容の要約）:
- Revision（Relation）列が空欄の行は存在しない（前提）
- 台帳（入力Excel）に明示的に記録されている Child-Parent 行は、
  Relation列の値（流用・RevUp等）にかかわらず実線で表示する
- 台帳に明示的な行がない Child-Parent の組でも、図番の末尾文字が
  A, B, C, ... のように同一base（末尾1文字を除き完全一致）で
  昇順の関係にある場合は、その順（例: Parent=A側, Child=B側）を
  「推測されたRevUp」として破線で表示する
- 同一baseの中で複数のノードが存在する場合、既存ノードの中で
  「隣接する」リビジョン同士だけを繋ぐ（歯抜けのA,C,Dなら A-C, C-D。A-Dは繋がない）
- 台帳に既に明示的な行がある組み合わせには、重複して破線エッジを追加しない

境界:
- 図番の末尾文字が英字でない場合や、baseが異なる場合は対象外（エッジなし）
- 台帳から見て「Parent側の文字がChild側より後（降順）」の場合は対象外
"""
import sys
import os
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from utils.graph_builder import GraphBuilder


def test_all_ledger_rows_are_solid_regardless_of_relation_value():
    df = pd.DataFrame([
        {'Child': 'DE5150-405-23D', 'Parent': 'DE5150-405-23C', 'Relation': 'RevUp'},
        {'Child': 'DE5330-545-01A', 'Parent': 'DE5313-545-01B', 'Relation': '流用'},
    ])
    builder = GraphBuilder(df, ['Relation'])
    builder.build()
    edges = builder.get_edges()

    assert ('DE5150-405-23C', 'DE5150-405-23D', False) in edges
    assert ('DE5313-545-01B', 'DE5330-545-01A', False) in edges


def test_gap_in_revision_chain_is_inferred_and_dashed():
    # 統合図面管理台帳.xlsx 相当のケース: 同一base(EE3273-608-34)で
    # 34A, 34C, 34D はそれぞれ別の行で登場するが、34A-34C間の行は台帳にない
    df = pd.DataFrame([
        {'Child': 'EE3273-608-34A', 'Parent': 'EE3273-608-26D', 'Relation': '流用'},
        {'Child': 'EE3273-608-34C', 'Parent': 'EE3273-608-26D', 'Relation': '流用'},
        {'Child': 'EE3273-608-34D', 'Parent': 'EE3273-608-34C', 'Relation': 'RevUp'},
    ])
    builder = GraphBuilder(df, ['Relation'])
    builder.build()
    edges = builder.get_edges()

    # 34A -> 34C は台帳にないため推測・破線
    assert ('EE3273-608-34A', 'EE3273-608-34C', True) in edges
    # 34C -> 34D は台帳に明示的に存在するため実線のまま（重複破線を追加しない）
    assert ('EE3273-608-34C', 'EE3273-608-34D', False) in edges
    assert ('EE3273-608-34C', 'EE3273-608-34D', True) not in edges


def test_fully_recorded_chain_produces_no_dashed_edges():
    # 統合図面管理台帳.xlsx の実データ相当: 全リビジョンが台帳に記録済みの場合、
    # 推測エッジは1件も生成されない
    df = pd.DataFrame([
        {'Child': 'EE3273-608-34B', 'Parent': 'EE3273-608-34A', 'Relation': 'RevUp'},
        {'Child': 'EE3273-608-34C', 'Parent': 'EE3273-608-34B', 'Relation': 'RevUp'},
        {'Child': 'EE3273-608-34D', 'Parent': 'EE3273-608-34C', 'Relation': 'RevUp'},
    ])
    builder = GraphBuilder(df, ['Relation'])
    builder.build()
    edges = builder.get_edges()

    dashed = [e for e in edges if e[2]]
    assert dashed == []


def test_unrelated_base_numbers_are_not_connected():
    df = pd.DataFrame([
        {'Child': 'EE1111-001-01A', 'Parent': 'EE9999-999-99Z', 'Relation': '流用'},
        {'Child': 'EE2222-002-02B', 'Parent': 'EE8888-888-88Y', 'Relation': '流用'},
    ])
    builder = GraphBuilder(df, ['Relation'])
    builder.build()
    edges = builder.get_edges()

    dashed = [e for e in edges if e[2]]
    assert dashed == []
