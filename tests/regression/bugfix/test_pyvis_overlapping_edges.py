"""
Bugfix regression: 2026-07-31, インタラクティブ(Pyvis)表示で実線矢印が消えて見える

不具合: 図番検索で単一ツリーに絞り込んだ際（例: EE3273-608-34A で検索）、
EE3273-608-26D から複数の子（EE3273-608-34A・EE3273-608-34C）へ向かう
2本の実線（流用）エッジが縦一直線に重なり、片方が完全に隠れて見えなく
なっていた。PDF（Graphviz）では正しく2本表示されていたため、データではなく
Pyvis（vis-network）の階層レイアウトが直線エッジしか描画しない設定だった
ことが原因（ノードをドラッグで動かすと隠れていたエッジが現れることで確認済み）。

修正（第1版）: app.py の render_pyvis() の net.set_options() に
edges.smooth（type: "curvedCW"）を一律追加し、エッジを常にわずかに湾曲させる
ことで、始点・終点が一直線上に並ぶ複数エッジでも視覚的に重ならないようにした。

追加報告（同日）: 上記だけでは、同一始点（例: EE3273-608-26D）から複数の
RevUpチェーンノード（34A/34B/34C/34D）へ向かう4本の実線が、湾曲の強さが
一律だったため依然として見分けにくいままだった。PDF（Graphviz）ではエッジ
ごとに湾曲を変えて自然に扇状に見せていたことにヒントを得て、
utils/graph_builder.compute_edge_curvature() を新設し、同一始点から出る
エッジを左右交互（curvedCW/curvedCCW）・徐々に強く湾曲させるよう変更。
net.set_options() の一律 edges.smooth 設定は不要になったため削除し、
net.add_edge() 呼び出し時に個別の smooth オプションを渡す方式に変更した。

保証したいこと:
- render_pyvis() が compute_edge_curvature() を使ってエッジごとに
  smooth オプションを付与していること（一律固定の湾曲設定に戻さないこと）
"""
from pathlib import Path

APP_PY = Path(__file__).resolve().parents[3] / 'app.py'


def _render_pyvis_source():
    text = APP_PY.read_text(encoding='utf-8')
    start = text.index('def render_pyvis(')
    end = text.index('\nif uploaded_file', start + 1)
    return text[start:end]


def test_render_pyvis_uses_per_edge_curvature():
    source = _render_pyvis_source()
    assert 'compute_edge_curvature(' in source, (
        "render_pyvis() が compute_edge_curvature() を使わなくなっています。"
        "同一始点から出る複数エッジが再び一直線に重なって見えなくなる可能性があります。"
    )
    assert 'net.add_edge(' in source and 'smooth=' in source, (
        "net.add_edge() にエッジごとの smooth オプションが渡されていません。"
    )
