"""職務経歴書ファイルの読み取り処理。"""

from docx import Document


def extract_text_from_docx(
    file,
) -> str:
    """Wordファイルから本文テキストを取り出す。"""

    document = Document(file)

    paragraphs = [
        paragraph.text.strip()
        for paragraph in document.paragraphs
        if paragraph.text.strip()
    ]

    return "\n".join(paragraphs)