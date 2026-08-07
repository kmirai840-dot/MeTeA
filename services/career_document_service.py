"""職務経歴書ファイルの読み取り処理。"""
from dataclasses import dataclass

from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph


@dataclass
class ParsedCareerHistory:
    """AIが抽出した部署・役割情報。"""

    department: str
    position: str
    occupation: str
    job_description: str
    achievements: str


@dataclass
class ParsedCareer:
    """AIが抽出した会社単位の職務経歴。"""

    company_name: str
    employment_type: str
    industry: str
    start_year: int
    start_month: int
    end_year: int | None
    end_month: int | None
    is_current: bool
    histories: list[ParsedCareerHistory]


def extract_text_from_docx(
    file,
) -> str:
    """Wordファイルから文書内の順番どおりにテキストを取り出す。"""

    document = Document(file)

    text_parts = []

    for block in document.iter_inner_content():

        if isinstance(block, Paragraph):
            text = block.text.strip()

            if text:
                text_parts.append(text)

        elif isinstance(block, Table):
            for row in block.rows:
                for cell in row.cells:
                    text = cell.text.strip()

                    if text:
                        text_parts.append(text)

    return "\n".join(text_parts)