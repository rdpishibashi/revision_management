"""
Bugfix regression: 2026-08-30, multi-sheet Excel with Child/Parent data ignored

不具合: app.py の load_data() は pd.read_excel(file_object) を既定引数で呼んでいたため、
常に先頭シートのみを読み込んでいた。台帳Excelが複数シート構成（例: Summary シートが
先頭、Child/Parent データは別シート）の場合、先頭シートに Child/Parent 列が無ければ
「必要な固定カラムが見つかりません」と誤って失敗し、実際にはデータを持つシートが
存在していても読み込まれなかった。

修正: utils/graph_builder.select_data_sheet() を新設し、以下の優先順位でシートを選ぶ。
  1. シート名が "Master"（大文字小文字問わず）のシートを最優先で選ぶ
  2. なければ、Child列・Parent列を両方持つシートのうち最初に見つかったものを選ぶ
  3. どちらも無ければ None を返し、呼び出し側（app.py load_data()）は先頭シートに
     フォールバックして従来通りのカラム欠落エラーを出す

保証したいこと:
- "Master" という名前のシートがあれば、他にデータを持つシートがあっても "Master" が
  最優先で選ばれること（大文字小文字を問わない）
- "Master" が無い場合、Child/Parent 列を持つ最初のシートが選ばれること（多シート構成の
  台帳を先頭シートの制約なく読み込めること）
- どのシートにも該当が無い場合は None を返し、エラー経路が従来通り機能すること
"""
import sys
import os
import io
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from utils.graph_builder import select_data_sheet


def _make_excel_file(sheets):
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
        for name, df in sheets.items():
            df.to_excel(writer, sheet_name=name, index=False)
    buf.seek(0)
    return pd.ExcelFile(buf)


def test_master_sheet_selected_over_summary_first_sheet():
    """以前の実装ではSummaryが先頭シートのため常にSummaryが読まれ、
    'Child'/'Parent' カラムが見つからないと誤ってエラーになっていた。"""
    summary_df = pd.DataFrame({'エンティティ統計': ['削除図形 総数'], 'Unnamed: 1': [10]})
    master_df = pd.DataFrame({'Child': ['B1'], 'Parent': ['A1']})
    excel_file = _make_excel_file({'Summary': summary_df, 'Master': master_df})

    assert select_data_sheet(excel_file) == 'Master'


def test_data_sheet_selected_when_not_named_master_and_not_first():
    """Masterという名前のシートが無い多シート台帳でも、Child/Parent列を持つ
    シート（先頭でなくても）が正しく選ばれること。"""
    summary_df = pd.DataFrame({'エンティティ統計': ['削除図形 総数'], 'Unnamed: 1': [10]})
    data_df = pd.DataFrame({'Child': ['B1'], 'Parent': ['A1']})
    excel_file = _make_excel_file({
        'Summary': summary_df,
        'Diff List': data_df,
        'Drawing List': summary_df,
    })

    assert select_data_sheet(excel_file) == 'Diff List'
