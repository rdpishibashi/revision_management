# TECHNICAL.md — Drawing-genealogy

## 概要

図番親子関係台帳（Excel）をアップロードして、図番の親子関係を有向グラフで可視化する Streamlit アプリ。
インタラクティブ表示（Pyvis）と固定表示・PDF出力（Graphviz）の 2 モードを持つ。

---

## ディレクトリ構成

```
Drawing-genealogy/
├── app.py                  # Streamlit エントリポイント
├── requirements.txt
├── packages.txt            # Streamlit Cloud 用 OS パッケージ（日本語フォント）
├── shutter.xlsx            # サンプルデータ
├── utils/
│   ├── graph_builder.py    # グラフデータ構築（Pyvis/Graphviz 共通ロジック）
│   └── formatters.py       # Pyvis ホバーテキスト HTML 生成
├── lib/                    # Pyvis 同梱 JS ライブラリ（vis-9.1.2 等）
└── tests/
    ├── unit/                    # utils/graph_builder.py の純粋関数テスト
    └── regression/
        ├── spec/                # 仕様確認（受入条件の固定）
        └── bugfix/              # 不具合再発防止
```

---

## アーキテクチャ

### データフロー

```
Excel アップロード
  → load_data()                        # pd.read_excel + @st.cache_data(ttl=600)
                                        # + normalize_parent_value()（"None"系プレースホルダーを空文字列化）
  → [図番検索が入力されている場合]
      GraphBuilder.build() (全体)      # 検索フィルタ用に一旦全体を構築
      → find_search_component_nodes()  # ヒットしたノードの連結成分を抽出
      → data を該当ノードで絞り込み
  → GraphBuilder.build()               # ノード収集 → ルート判定 → 属性付与
  → render_pyvis() / render_graphviz()
  → Streamlit 表示 / PDF ダウンロード
```

### Excel 入力仕様

| 列名 | 必須 | 説明 |
|------|------|------|
| `Child` | ◎ | 子図番 |
| `Parent` | ◎ | 親図番（空欄、または "None" 系プレースホルダーで「親なし」を表す） |
| `Relation` | — | 動的属性の一つ。値の有無が矢印の実線/破線判定に使われる（下記参照） |
| 任意列 | — | その他の動的属性（Title, Date 等）|

- `Date` → `YYYY/MM/DD`、`Recorded Date` → `yy-mm-dd HH:MM:SS` に正規化
- NaN は空文字列に変換
- Parent列の値が "None"（大文字小文字問わず、前後空白許容）の場合も空文字列に正規化される
  （`normalize_parent_value()`）。空文字列の Parent は「親なし＝独立ノード」として扱われ、
  共有の "None" ノードにぶら下がることはない。自身の行が持つ動的属性（Relation 等）は
  そのまま表示される（ROOTノードのような縮退表示にはならない）

---

## コアロジック（`utils/graph_builder.py`）

### モジュール関数（`GraphBuilder` 非依存の純粋関数）

| 関数 | 役割 |
|---------|------|
| `normalize_parent_value(value)` | Parent列の "None" 系プレースホルダーを空文字列に正規化 |
| `find_search_component_nodes(all_nodes, edges, query)` | 図番検索（部分一致・NFKC正規化）でヒットしたノードが属する連結成分（ツリー）を返す。クエリが空欄なら全ノードを返す |
| `compute_edge_curvature(edges)` | 同一始点から出る複数エッジに、左右交互・徐々に強くなる湾曲（vis-network の `smooth` オプション）を割り当てる。Pyvis 表示専用 |

### `GraphBuilder` クラス

`GraphBuilder` クラスがグラフ構築の全ロジックを担う。

| メソッド | 役割 |
|---------|------|
| `_identify_root_nodes()` | Parent にあり Child にないノードをルートと判定 |
| `get_node_color()` | `Relation == '流用'` → `#FFFFE0`、その他 → `#F0F8FF` |
| `get_edges()` | `(parent, child, is_dashed)` タプルリストを返す（下記「矢印スタイル」参照） |
| `_infer_revision_up_edges()` | 台帳に明示的な行がない同一base・リビジョン昇順の隣接ノード間に、推測RevUpエッジを追加する |

ルートノードは属性を `{'Relation': 'ROOT'}` のみに強制上書きする（自身の行を持たない
＝台帳上でChildとして一度も登場しない、純粋に「他の図面のParent値としてのみ存在する」
ノードに限る。Parent="None"正規化による独立ノードはこれに該当しない）。

### 矢印スタイル（実線・破線）

| ケース | 表示 |
|---|---|
| 台帳に明示的に記録された行（Parent, Childとも実図番） | 実線（Relation列の値は問わない） |
| 台帳に記録がない同一base（末尾1文字を除き完全一致）・リビジョン昇順の隣接ペア | 破線（推測RevUp） |
| 上記の推測RevUpペアが既に明示的な行として存在する場合 | 実線のまま（重複して破線を追加しない） |
| base が異なる、または末尾が英字でない等パターン非該当 | エッジなし |

「隣接」とは、実在するノードの中でリビジョン文字順に隣り合う組のみを指す
（例: A, C, D というノードが存在する場合 A-C, C-D を接続。Bが存在しなければ A-D は繋がない）。

### 図番検索・ツリー絞り込み

サイドバーの検索欄（`app.py`）に図番の一部を入力すると、部分一致（大文字小文字を
区別せず、全角/半角は NFKC 正規化して比較）でヒットした図番が属する連結成分
（明示エッジ・推測RevUpエッジの両方をたどる）だけを表示する。複数のツリーに
またがってヒットした場合は該当する全ツリーを並べて表示する。空欄の場合は
フィルタなし（全体表示）。ヒットが0件の場合は `st.warning()` を表示しグラフ・
台帳データ表示をスキップする。

---

## 表示モード

### Pyvis（インタラクティブ）

- 階層的レイアウト（`direction: UD`、物理シミュレーション無効）
- エッジは `compute_edge_curvature()` によりノードごとに湾曲を変えてファン状に描画
  （同一始点から出る複数エッジが縦一直線に重なって見えなくなるのを防ぐ）
- 一時 HTML → `components.html()` で iframe 表示
- ノードクリック → ホバーテキストで属性一覧表示

### Graphviz（固定・PDF）

- ノード属性を HTML `<TABLE>` 形式で記述
- `dot.pipe(format='pdf')` → `st.download_button` でダウンロード

---

## 日本語フォント

| 環境 | フォント |
|------|---------|
| macOS | Hiragino Sans |
| Windows | MS Gothic |
| Linux / Streamlit Cloud | Noto Sans CJK JP |

Streamlit Cloud: `packages.txt` に `fonts-noto-cjk` を記載。
Graphviz PDF: OS の Graphviz 本体のフォント設定に依存（`packages.txt` に `graphviz` も必要）。

---

## 依存パッケージ

```
streamlit>=1.40.0, pandas>=1.5.3, graphviz, pyvis>=0.3.1
openpyxl>=3.0.0, numpy>=1.24.0
```

---

## 既知の制限

| 制限 | 詳細 |
|------|------|
| 大規模グラフ | ノード数数百超でレイアウト計算が遅延する。図番検索でツリーを絞り込むことで軽減できる |
| 循環参照 | 検出・警告の仕組みなし |
| 複数シート Excel | 先頭シートのみ読み込む |
| PDF 日本語 | Graphviz 本体と日本語フォントが OS に必要 |
| エッジ湾曲のヒューリスティック | `compute_edge_curvature()` は同一始点のエッジ数のみで湾曲を決めるため、1つのノードに非常に多くのエッジが集中する場合は依然として見づらくなりうる |

---

## 機能拡張ポイント

| テーマ | 実装アプローチ |
|--------|--------------|
| 循環参照検出 | `networkx.find_cycle()` を導入 |
| 複数シート対応 | `load_data()` に `st.selectbox` でシート選択 |
| CSV エクスポート | `get_edges()` → DataFrame → `st.download_button` |
| 検索結果のノードハイライト | 現状は該当ツリーへの絞り込みのみ。ヒットしたノード自体を強調表示する場合は Pyvis の選択ノード色変更 API を利用 |

---

*最終更新: 2026-07-31（Parent="None"系プレースホルダーの独立ノード化、矢印の実線/破線判定
（台帳明示行=実線、推測RevUp=破線）、図番検索によるツリー絞り込み、Pyvisエッジ湾曲による
視認性改善を追加。`tests/` ディレクトリ新設）*
