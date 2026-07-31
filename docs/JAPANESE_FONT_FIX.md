# Japanese Font Fix for PDF Output

## Problem

The PDF output from Drawing-genealogy (`family_tree.pdf`) was not displaying full-width (Japanese) characters correctly. Characters like `図番`, `流用`, `親子関係`, etc. were either missing or showed as boxes/question marks.

## Root Cause

Graphviz, the library used to generate the PDF, uses a default font that doesn't support Japanese (CJK) characters. When no font is specified, Graphviz falls back to basic Latin fonts which cannot render Japanese text.

## Solution

Added explicit Japanese font configuration to the Graphviz Digraph object:

### Code Changes in `app.py`

#### 1. Added platform detection and font selection (lines 9, 18-34)

```python
import platform

def get_japanese_font():
    """
    システムに応じて利用可能な日本語フォントを返す
    """
    system = platform.system()

    if system == 'Darwin':  # macOS
        return 'Hiragino Sans'
    elif system == 'Windows':
        return 'MS Gothic'
    else:  # Linux
        return 'Noto Sans CJK JP'

JAPANESE_FONT = get_japanese_font()
```

#### 2. Updated `render_graphviz()` function (lines 114-129)

**Before:**
```python
dot = graphviz.Digraph(comment='Family Tree', format='pdf', graph_attr={'rankdir': 'TB'})
```

**After:**
```python
dot = graphviz.Digraph(
    comment='Family Tree',
    format='pdf',
    graph_attr={
        'rankdir': 'TB',
        'fontname': JAPANESE_FONT  # Japanese font support
    },
    node_attr={
        'fontname': JAPANESE_FONT
    },
    edge_attr={
        'fontname': JAPANESE_FONT
    }
)
```

## Font Selection by Platform

| Platform | Font | Availability |
|----------|------|--------------|
| **macOS** | Hiragino Sans | Built-in (default) |
| **Windows** | MS Gothic | Built-in (default) |
| **Linux** | Noto Sans CJK JP | Requires installation |

### Linux Font Installation

If you're on Linux and Japanese characters still don't display:

```bash
# Ubuntu/Debian
sudo apt-get install fonts-noto-cjk

# Fedora/RHEL
sudo dnf install google-noto-sans-cjk-jp-fonts

# Arch Linux
sudo pacman -S noto-fonts-cjk
```

## Testing

A test script `test_japanese_font.py` is provided to verify the fix:

```bash
cd Drawing-genealogy
python3 test_japanese_font.py
```

This will:
1. Detect your system and select the appropriate font
2. Generate a test PDF (`test_japanese_font.pdf`) with Japanese text
3. Report success or provide troubleshooting steps

**Expected output:**
```
System: Darwin
Using font: Hiragino Sans

Generating test PDF...
✓ Success! PDF generated: test_japanese_font.pdf
✓ File size: 9,157 bytes

Please open test_japanese_font.pdf and verify that Japanese characters display correctly.
```

## Verification

To verify the fix works in the main application:

1. Run the Streamlit app:
   ```bash
   streamlit run app.py
   ```

2. Upload a Parent-Child list Excel file

3. Select **"固定表示・PDF出力"** mode

4. Click **"PDFファイルをダウンロード"**

5. Open the downloaded `family_tree.pdf`

6. Verify that all Japanese characters display correctly:
   - Node labels (図番)
   - Relation types (流用, RevUp, ROOT)
   - Column names (e.g., 変更区分, 関連図面)

## Technical Details

### Why Font Specification is Needed

Graphviz uses different rendering backends:
- **PNG/SVG**: Can use system fonts with Unicode support
- **PDF**: Embeds fonts in the file - must specify fonts explicitly

### Font Embedding

When you specify `fontname`, Graphviz:
1. Looks up the font on the system
2. Embeds the necessary glyphs in the PDF
3. Creates proper character mappings

Without this, Graphviz uses a minimal Latin-only font.

### Hiragino Sans Details (macOS)

**Hiragino Sans** (ヒラギノ角ゴシック):
- Standard system font since macOS El Capitan
- Full Unicode support including CJK
- Professional-grade typeface designed by Dainippon Screen
- Clean, modern sans-serif appearance
- Excellent readability for technical documents

Alternative macOS fonts that also work:
- `Hiragino Kaku Gothic ProN`
- `Arial Unicode MS` (older systems)

### MS Gothic Details (Windows)

**MS Gothic** (MS ゴシック):
- Standard system font on all Windows versions
- Full Japanese character support
- Monospace font - all characters same width
- Good for technical diagrams

Alternative Windows fonts:
- `Meiryo` - Modern sans-serif
- `Yu Gothic` - Windows 8.1+

## Troubleshooting

### Issue: "Font not found" error

**Solution:**
Specify a different font in `app.py`:

```python
def get_japanese_font():
    system = platform.system()

    if system == 'Darwin':
        return 'Arial Unicode MS'  # Try alternative
    # ... etc
```

### Issue: Characters still show as boxes

**Possible causes:**
1. Graphviz not properly installed
2. Font not found on system
3. PDF viewer issue

**Solutions:**
```bash
# Reinstall Graphviz (macOS)
brew reinstall graphviz

# Check available fonts
fc-list | grep -i "hiragino\|gothic\|noto"

# Try opening PDF in different viewer
open -a Preview family_tree.pdf
```

### Issue: Different characters on different systems

This is expected - each platform uses its own native font. The rendering will look slightly different but all characters should display correctly.

## Files Modified

| File | Changes |
|------|---------|
| `app.py` | Added font detection and configuration |
| `test_japanese_font.py` | New test script |
| `JAPANESE_FONT_FIX.md` | This documentation |

## Related Issues

- Original issue: Full-width characters not displaying in PDF
- Affected file: `/Users/ryozo/Downloads/family_tree.pdf`
- Date fixed: 2025-12-24

## References

- [Graphviz Node Attributes](https://graphviz.org/doc/info/attrs.html#d:fontname)
- [Hiragino Font Family](https://en.wikipedia.org/wiki/Hiragino)
- [MS Gothic Documentation](https://docs.microsoft.com/en-us/typography/font-list/ms-gothic)
