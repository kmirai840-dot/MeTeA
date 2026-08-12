"""職務経歴書ファイルの読み取り処理。"""
from dataclasses import dataclass
import json

from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph
from openai import OpenAI


@dataclass
class ParsedCareerHistory:
    """AIが抽出した部署・役割情報。"""

    department: str
    position: str
    occupation: str
    start_year: int | None
    start_month: int | None
    end_year: int | None
    end_month: int | None
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


def parse_career_document(
    extracted_text: str,
) -> list[ParsedCareer]:
    """職務経歴書テキストをAIで会社・職歴単位に整理する。"""

    client = OpenAI()

    response = client.responses.create(
        model="gpt-5-mini",
        store=False,
        input=[
            {
                "role": "system",
                "content": (
                    "あなたは日本語の職務経歴書を"
                    "構造化するアシスタントです。"
                    "文書に書かれていない情報は推測せず、"
                    "不明な文字列項目は空文字、"
                    "不明な年月はnullにしてください。"
                    "同じ会社内で部署や役割が変わっている場合は、"
                    "historiesを複数件に分けてください。"
                    "会社ごとに職務経歴を完全に分離してください。"
                    "ある会社に記載された部署名、役職、業務内容、"
                    "実績を、別の会社のhistoriesに"
                    "含めてはいけません。"
                    "新しい会社名が現れた場合は、"
                    "それ以前の会社の情報と混在させず、"
                    "必ず別のcareerとして扱ってください。"
                    "同じ会社内でも、文書上で異なる部署名として"
                    "明記されている部署を統合しないでください。"
                    "例えば、事務センターと"
                    "カスタマーセンターが別々の所属部署として"
                    "記載されている場合は、"
                    "それぞれ別のhistoryにしてください。"
                    "historiesは、文書から所属部署や在籍期間が"
                    "明確に区切れる場合に分けてください。"
                    "プロジェクトへの参画、PMO担当、"
                    "一時的な役割の追加だけでは"
                    "新しいhistoryを作成しないでください。"
                    "元の所属部署から異動したことが"
                    "文書に明記されていない場合は、"
                    "直前の所属部署のhistoryに含めてください。"
                    "プロジェクトや兼務の内容は、"
                    "そのhistoryのjob_descriptionまたは"
                    "achievementsに含めてください。"
                    "会社名、部署名、役職、在籍期間などの"
                    "事実情報は、文書に書かれていない内容を"
                    "推測しないでください。"
                    "industryは事業内容の説明文ではなく、"
                    "一般的な業種カテゴリを簡潔に設定してください。"
                    "商品名やサービス名、具体的な事業説明は"
                    "industryに含めないでください。"
                    "例えば、SaaS・ソフトウェア、"
                    "金融・クレジットカードなどの粒度で"
                    "設定してください。"
                    "ただしoccupationのみ、文書に記載された"
                    "実際の業務内容を根拠として、"
                    "一般的な職種名に分類してください。"
                    "occupationは空文字にせず、"
                    "一般事務、カスタマーサポート、"
                    "業務企画、業務改善など、"
                    "最も近い職種名を設定してください。"
                    "部署名そのものを職種名として"
                    "使用しないでください。"
                ),
            },
            {
                "role": "user",
                "content": extracted_text,
            },
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": "career_document",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "careers": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "company_name": {
                                        "type": "string"
                                    },
                                    "employment_type": {
                                        "type": "string"
                                    },
                                    "industry": {
                                        "type": "string"
                                    },
                                    "start_year": {
                                        "type": "integer"
                                    },
                                    "start_month": {
                                        "type": "integer"
                                    },
                                    "end_year": {
                                        "type": [
                                            "integer",
                                            "null",
                                        ]
                                    },
                                    "end_month": {
                                        "type": [
                                            "integer",
                                            "null",
                                        ]
                                    },
                                    "is_current": {
                                        "type": "boolean"
                                    },
                                    "histories": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "department": {
                                                    "type": "string"
                                                },
                                                "position": {
                                                    "type": "string"
                                                },
                                                "occupation": {
                                                    "type": "string"
                                                },
                                                "start_year": {
                                                    "type": [
                                                        "integer",
                                                        "null",
                                                    ]
                                                },
                                                "start_month": {
                                                    "type": [
                                                        "integer",
                                                        "null",
                                                    ]
                                                },
                                                "end_year": {
                                                    "type": [
                                                        "integer",
                                                        "null",
                                                    ]
                                                },
                                                "end_month": {
                                                    "type": [
                                                        "integer",
                                                        "null",
                                                    ]
                                                },
                                                "job_description": {
                                                    "type": "string"
                                                },
                                                "achievements": {
                                                    "type": "string"
                                                },
                                            },
                                            "required": [
                                                "department",
                                                "position",
                                                "occupation",
                                                "start_year",
                                                "start_month",
                                                "end_year",
                                                "end_month",
                                                "job_description",
                                                "achievements",
                                            ],
                                            "additionalProperties": False,
                                        },
                                    },
                                },
                                "required": [
                                    "company_name",
                                    "employment_type",
                                    "industry",
                                    "start_year",
                                    "start_month",
                                    "end_year",
                                    "end_month",
                                    "is_current",
                                    "histories",
                                ],
                                "additionalProperties": False,
                            },
                        },
                    },
                    "required": [
                        "careers"
                    ],
                    "additionalProperties": False,
                },
            }
        },
    )

    parsed_data = json.loads(
        response.output_text
    )

    careers = []

    for career_data in parsed_data["careers"]:

        histories = [
            ParsedCareerHistory(
                **history_data
            )
            for history_data in career_data[
                "histories"
            ]
        ]

        career = ParsedCareer(
            company_name=career_data[
                "company_name"
            ],
            employment_type=career_data[
                "employment_type"
            ],
            industry=career_data[
                "industry"
            ],
            start_year=career_data[
                "start_year"
            ],
            start_month=career_data[
                "start_month"
            ],
            end_year=career_data[
                "end_year"
            ],
            end_month=career_data[
                "end_month"
            ],
            is_current=career_data[
                "is_current"
            ],
            histories=histories,
        )

        careers.append(career)

    return careers