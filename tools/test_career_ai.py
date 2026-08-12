from pathlib import Path

from services.career_document_service import (
    extract_text_from_docx,
    parse_career_document,
)


FILE_PATH = Path(
    r"C:\Users\frontier-Python.LAPTOP-II8992P9\Downloads\久武城未来様_職務経歴書.docx"
)


with FILE_PATH.open("rb") as file:
    extracted_text = extract_text_from_docx(
        file
    )


careers = parse_career_document(
    extracted_text
)


print("=== AI解析結果 ===")
print("会社数:", len(careers))


for index, career in enumerate(
    careers,
    start=1,
):
    print()

    print(
        f"【会社{index}】",
        career.company_name,
    )

    print(
        "雇用形態:",
        career.employment_type,
    )

    print(
        "業種:",
        career.industry,
    )

    print(
        "在籍:",
        career.start_year,
        career.start_month,
        "〜",
        career.end_year,
        career.end_month,
    )

    print(
        "部署・役割数:",
        len(career.histories),
    )

    for history_index, history in enumerate(
        career.histories,
        start=1,
    ):
        print(
            f"  └ 履歴{history_index}:",
            history.department,
            "/",
            history.position,
            "/",
            history.occupation,
        )

        print(
            "     業務内容:",
            history.job_description,
        )

        print(
            "     実績:",
            history.achievements,
        )