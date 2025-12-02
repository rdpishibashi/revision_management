"""
Text formatting utilities for graph visualization
"""


def make_bold(text):
    """
    Convert regular text to Unicode bold characters

    Args:
        text: String to convert to bold

    Returns:
        str: Text with Unicode bold characters

    Example:
        >>> make_bold("Hello123")
        "𝗛𝗲𝗹𝗹𝗼𝟭𝟮𝟯"
    """
    bold_map = {
        'A': '𝗔', 'B': '𝗕', 'C': '𝗖', 'D': '𝗗', 'E': '𝗘', 'F': '𝗙', 'G': '𝗚', 'H': '𝗛',
        'I': '𝗜', 'J': '𝗝', 'K': '𝗞', 'L': '𝗟', 'M': '𝗠', 'N': '𝗡', 'O': '𝗢', 'P': '𝗣',
        'Q': '𝗤', 'R': '𝗥', 'S': '𝗦', 'T': '𝗧', 'U': '𝗨', 'V': '𝗩', 'W': '𝗪', 'X': '𝗫',
        'Y': '𝗬', 'Z': '𝗭',
        'a': '𝗮', 'b': '𝗯', 'c': '𝗰', 'd': '𝗱', 'e': '𝗲', 'f': '𝗳', 'g': '𝗴', 'h': '𝗵',
        'i': '𝗶', 'j': '𝗷', 'k': '𝗸', 'l': '𝗹', 'm': '𝗺', 'n': '𝗻', 'o': '𝗼', 'p': '𝗽',
        'q': '𝗾', 'r': '𝗿', 's': '𝘀', 't': '𝘁', 'u': '𝘂', 'v': '𝘃', 'w': '𝘄', 'x': '𝘅',
        'y': '𝘆', 'z': '𝘇',
        '0': '𝟬', '1': '𝟭', '2': '𝟮', '3': '𝟯', '4': '𝟰', '5': '𝟱', '6': '𝟲', '7': '𝟳',
        '8': '𝟴', '9': '𝟵'
    }
    return ''.join(bold_map.get(c, c) for c in text)


def format_hover_text(drawing_id, details, is_root, dynamic_cols):
    """
    Format hover text for graph nodes

    Args:
        drawing_id: Node identifier (drawing number)
        details: Dictionary of node attributes
        is_root: Boolean indicating if this is a root node
        dynamic_cols: List of column names to display

    Returns:
        str: Formatted hover text with bold titles

    Example:
        >>> format_hover_text("DE5313-008-02B", {"Relation": "流用"}, False, ["Relation"])
        "【𝗗𝗘𝟱𝟯𝟭𝟯-𝟬𝟬𝟴-𝟬𝟮𝗕】\n\n𝗥𝗲𝗹𝗮𝘁𝗶𝗼𝗻: 流用"
    """
    # Create header with bold drawing ID
    title_lines = [f"【{make_bold(drawing_id)}】"]
    title_lines.append("")  # Empty line for spacing

    if is_root:
        # Root nodes show only Relation
        relation_value = details.get('Relation', 'ROOT')
        title_lines.append(f"{make_bold('Relation')}: {relation_value}")
    else:
        # Regular nodes show all dynamic columns
        for col_name in dynamic_cols:
            value = details.get(col_name, '不明')
            title_lines.append(f"{make_bold(col_name)}: {value}")

    return "\n".join(title_lines)
