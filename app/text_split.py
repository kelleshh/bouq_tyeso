MAX_TG_MESSAGE_LEN = 4000  # чуть меньше 4096, чтобы наверняка


def split_text_for_telegram(text: str, limit: int = MAX_TG_MESSAGE_LEN) -> list[str]:
    """
    Режем длинный текст на куски не длиннее limit, по строкам.
    Стараемся не рвать посреди строки.
    """
    lines = text.split("\n")
    chunks: list[str] = []
    current_lines: list[str] = []
    current_len = 0

    for line in lines:
        # +1 за символ перевода строки
        add_len = len(line) + 1
        if current_lines and current_len + add_len > limit:
            chunks.append("\n".join(current_lines))
            current_lines = [line]
            current_len = len(line) + 1
        else:
            current_lines.append(line)
            current_len += add_len

    if current_lines:
        chunks.append("\n".join(current_lines))

    return chunks
