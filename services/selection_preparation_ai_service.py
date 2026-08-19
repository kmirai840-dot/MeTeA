"""選考準備テーマを整理するためのAI材料生成。"""

import json

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field

from services.job_matching_evaluation_service import load_ai_matching_context


load_dotenv()

AI_MODEL = "gpt-5-mini"
STAR_ALLOWED_THEME_KEYS = {"achievement", "strengths"}
AI_SECTION_MARKERS = (
    "【回答に使える情報】",
    "【STARで整理した例】",
    "【回答の構成例】",
    "【前職・現職とのGAP】",
    "【追加で整理・確認すること】",
)

THEME_INSTRUCTIONS = {
    "self_intro": (
        "面接冒頭の30秒から1分の自己紹介を本人が組み立てるため、"
        "氏名、現在までの職務領域、応募先で再現性の高い強み、簡潔な締めに使える材料を選ぶ。"
        "経歴を年代順に羅列せず、実績は応募先との関連が強い代表例を最大2件に絞る。"
        "勤務地、給与、休日、入社時期など条件面の希望は一切含めない。"
        "完成した自己紹介文は作らず、話す順番が分かる短い箇条書きにする。"
    ),
    "career_reason": (
        "面接で45秒から1分の転職理由を本人が組み立てるため、"
        "『これまで一貫して取り組んだこと』『転職を考えた前向きな契機』"
        "『次の環境で実現したいこと』に分けて使える材料を提示する。経歴や実績は絞り、"
        "実績数値の列挙、自己PR、志望動機、入社後の貢献、応募したという結論を混ぜない。"
        "現職や過去の会社への不満、給与・勤務地・休日など条件面を含めない。"
        "職歴が変化していても、その根底にある課題意識・選択基準・仕事の方向性を一本だけ示し、"
        "『なぜ今、環境を変える必要があるのか』が企業側にも納得できる回答にする。"
        "必ず、前職・現職で実現できていたこと／実現しにくかったことと、"
        "今後実現したい状態とのGAPを中心に整理する。GAPは対象顧客、役割範囲、"
        "意思決定への関与、身につけたい能力等の具体的な違いで示す。"
        "GAPは本人のキャリア上の差分であり、応募求人が求める経験・ツール・業界知識の不足ではない。"
        "求人の必須条件、歓迎条件、広告・媒体・RPA等の応募先固有スキルをGAPに使用しない。"
        "同じ本人であれば応募先が変わっても概ね成立する転職理由にする。"
        "前職・現職を否定せず、そこで得た経験を次へ広げる前向きな差分として扱う。"
        "企業名、求人名、『応募した・応募を決めた』、志望理由、入社後の貢献は一切出さない。"
        "このテーマではSTAR、具体的な実績エピソード、企業へ尋ねる逆質問を出さない。"
        "追加質問や利用者による追加入力を前提にせず、登録済み情報だけで完結させる。"
        "明示的な転職の契機が登録されていない場合も、事実を創作せず、登録済みの職歴・役割・"
        "取り組みから一貫して読み取れる方向性を、断定しすぎない整理案として提示する。"
        "usable_pointsは『目指す姿』『前職・現職で実現できたこと』『前職・現職とのGAP』"
        "『GAPを埋めるために必要な経験・能力』の区分が分かる短い材料にする。"
    ),
    "motivation": (
        "面接で1分程度の志望動機を本人が組み立てる材料として、応募先が現在必要としている役割・課題、"
        "その企業・ポジションを選ぶ具体的理由、最も関連する強み1つ、入社後の貢献の順にまとめる。"
        "何でもできるという見せ方を避け、求人の中心課題へ最も刺さる経験を主役にする。"
        "組織フェーズ、事業課題、カルチャーは求人情報から確認できる範囲だけを事実として扱い、"
        "確認できない内容は仮説と明記してquestionsへ回す。"
    ),
    "achievement": (
        "面接で説明できる代表的な実績を1件選び、状況・課題、行動、結果の順で簡潔に整理する。"
        "本人が登録していない数値や役割は補わない。"
    ),
    "strengths": (
        "面接で伝える強みを1つに絞り、結論、根拠となる経験、応募先での再現方法の順にまとめる。"
    ),
    "questions": (
        "求人情報を読めば分かる質問を避け、業務の期待値、評価基準、体制、入社後の課題を"
        "具体的に確認できる逆質問を3件以内で提示する。"
    ),
}


class STARMaterial(BaseModel):
    """登録済みの具体的経験をSTARで短く整理した例。"""

    title: str = Field(description="エピソードを識別できる短い名称")
    situation_task: str = Field(description="SituationとTask。合計2文以内")
    action: str = Field(description="本人が取ったAction。2文以内")
    result: str = Field(description="登録情報で確認できるResult。2文以内")


class CareerGapMaterial(BaseModel):
    """転職理由で必ず分けて確認する、前職・現職と目指す姿の差。"""

    achieved: str = Field(description="前職・現職で実現できていたこと")
    limitation: str = Field(description="前職・現職では実現しにくかったこと。否定表現にしない")
    desired: str = Field(description="今後実現したいこと")
    gap: str = Field(description="現状と今後の具体的なGAP")
    transition_necessity: str = Field(description="GAPを埋めるうえで転職が必要な理由")


class PreparationMaterial(BaseModel):
    """画面へ返す、利用者が確認・編集可能な準備材料。"""

    usable_points: list[str] = Field(
        min_length=1,
        max_length=6,
        description="本人が回答を組み立てるために使える情報。重要度順の短い箇条書き",
    )
    star_examples: list[STARMaterial] = Field(
        default_factory=list,
        max_length=2,
        description="具体的な経験が役立つ場合だけ示すSTAR整理例。最大2件",
    )
    structure_example: list[str] = Field(
        default_factory=list,
        max_length=3,
        description="STAR以外の回答構成例。各要素は1〜2文、最大3段階",
    )
    career_gap: CareerGapMaterial | None = Field(
        default=None,
        description="転職理由テーマだけで使用する、登録済み情報に基づくGAP整理",
    )
    questions: list[str] = Field(
        default_factory=list,
        max_length=3,
        description="逆質問テーマで企業へ確認する候補（最大3件）。それ以外は空",
    )


class SelectionPreparationAIError(RuntimeError):
    """AI材料を生成できない場合の利用者向け例外。"""


def generate_preparation_material(
    *,
    job_id: int,
    company_name: str,
    job_title: str,
    selection_type: str,
    theme_key: str,
    theme_title: str,
    theme_description: str,
    existing_content: str,
) -> PreparationMaterial:
    """登録済み情報を根拠に、選択テーマの検討材料を生成する。"""

    try:
        context = load_ai_matching_context(job_id)
        # A career reason describes the user's own transition and must not be
        # reverse-engineered from a particular vacancy's requirements.
        if theme_key == "career_reason":
            context = {
                "user_matching_information": context.get("user_matching_information", {})
            }
        verified_existing_content = existing_content
        marker_positions = [
            existing_content.find(marker)
            for marker in AI_SECTION_MARKERS
            if marker in existing_content
        ]
        if marker_positions:
            verified_existing_content = existing_content[:min(marker_positions)].strip()
        response = OpenAI().responses.parse(
            model=AI_MODEL,
            store=False,
            input=[
                {
                    "role": "system",
                    "content": (
                        "あなたは日本の就職・転職活動における選考準備を支援します。"
                        "登録情報にない実績、数値、経験、企業情報を創作してはいけません。"
                        "単なる登録情報の要約や経歴の網羅的な羅列は避け、"
                        "実際の面接で話すことと言わないことを取捨選択してください。"
                        "応募先については、求人情報から『現在期待される役割・解決したい課題・組織フェーズ』を読み取り、"
                        "候補者については、その課題へ最も直接つながる強みを1つ選んでください。"
                        "オールラウンダーとして全経験を並べず、応募先にとって採用する意味が明確になる接点を優先してください。"
                        "ただし企業の課題、選考理由、他候補者との比較または見送り理由を推測で断定してはいけません。"
                        "求人票だけで判断できない点は事実として補完せず、登録情報から確認できる範囲だけで整理してください。"
                        "完成回答、読み上げ用原稿、長い文章は生成しないでください。"
                        "usable_pointsには、本人が取捨選択して自分の言葉で回答を組み立てるための情報を、"
                        "重要度順に最大6件の短い箇条書きで返してください。"
                        "具体的なエピソードを例示する場合だけstar_examplesを使い、最大2件、"
                        "Situation/Task・Action・Resultをそれぞれ2文以内にしてください。"
                        f"STARを使用できるテーマキーは{sorted(STAR_ALLOWED_THEME_KEYS)}だけです。"
                        "それ以外のテーマではstar_examplesを必ず空にしてください。"
                        "career_reasonでは、追加質問を生成せず、登録済み情報の範囲だけを使って、"
                        "career_gapに、前職・現職で実現できたこと、実現しにくかったこと、"
                        "今後実現したいこと、両者の具体的GAP、転職が必要な理由を必ず分けて格納してください。"
                        "明示情報が少ない場合は、職歴・役割・継続している取り組みから確認できる範囲を"
                        "『整理案』として簡潔に表現し、事実にない具体的事情を創作しないでください。"
                        "career_reasonのcareer_gapはnullにせず、questionsは必ず空にしてください。"
                        "structure_exampleを次の3段階で各1〜2文生成してください。"
                        "第1段階は『将来なりたい姿・実現したい価値』、"
                        "第2段階は『前職・現職で実現できたこと／実現しにくかったことと、目指す姿とのGAP』、"
                        "第3段階は『GAPを埋めるために必要な経験・能力と、転職する必要性』です。"
                        "これは完成原稿ではなく構成例です。career_reason以外では、"
                        "明確な回答フレームが役立つ場合だけstructure_exampleを使用してください。"
                        "selected_theme.existing_contentに過去のAI生成文が含まれる可能性があります。"
                        "existing_contentだけに書かれ、registered_informationの他項目で確認できない経験・数値・理由は、"
                        "本人が登録した確定事実として再利用しないでください。"
                        "questionsは逆質問・確認事項テーマの場合だけ、企業へ確認する候補を重要度順に最大3件返してください。"
                        "それ以外のテーマではquestionsを必ず空にし、情報不足を理由に利用者へ回答を求めないでください。"
                        "明示情報が少ない場合も、登録情報から確認できる範囲を断定しすぎない整理案として提示してください。"
                        f"今回のテーマ固有の作成ルール：{THEME_INSTRUCTIONS.get(theme_key, '選考で実際に使える簡潔な口頭回答または準備メモにする。')}"
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "company_name": "" if theme_key == "career_reason" else company_name,
                            "job_title": "" if theme_key == "career_reason" else job_title,
                            "selection_type": selection_type,
                            "selected_theme": {
                                "theme_key": theme_key,
                                "title": theme_title,
                                "description": theme_description,
                                "existing_content": verified_existing_content,
                            },
                            "registered_information": context,
                        },
                        ensure_ascii=False,
                        default=str,
                    ),
                },
            ],
            text_format=PreparationMaterial,
            max_output_tokens=5000,
        )
    except Exception as exc:
        raise SelectionPreparationAIError(
            "AIから材料を取得できませんでした。通信環境またはAPI設定を確認して、もう一度お試しください。"
        ) from exc

    material = response.output_parsed
    if material is None or not material.usable_points:
        raise SelectionPreparationAIError("AIから有効な材料を取得できませんでした。")
    # STAR is useful for behavioural evidence, but it distorts career reasons,
    # motivation, conditions and question preparation into self-promotion.
    if theme_key not in STAR_ALLOWED_THEME_KEYS and material.star_examples:
        material = material.model_copy(update={"star_examples": []})
    if theme_key != "questions" and material.questions:
        material = material.model_copy(update={"questions": []})
    if theme_key == "career_reason":
        filtered_points = [
            point for point in material.usable_points
            if not any(
                word in point
                for word in (
                    "応募", "貴社", company_name, "入社後", "貢献",
                    "転職を考えた", "転職の契機",
                )
            )
        ]
        career_structure = [
            row for row in material.structure_example
            if not any(word in row for word in ("応募", "貴社", company_name, "入社後"))
        ]
        career_gap = material.career_gap
        if career_gap and any(
            word in " ".join(
                (
                    career_gap.achieved,
                    career_gap.limitation,
                    career_gap.desired,
                    career_gap.gap,
                    career_gap.transition_necessity,
                )
            )
            for word in ("応募", "貴社", company_name, "入社後")
        ):
            career_gap = None
        if career_gap is None:
            summary = filtered_points[0] if filtered_points else "登録済みの職歴で継続して取り組んできた領域を次の環境で広げること"
            career_gap = CareerGapMaterial(
                achieved=summary,
                limitation="登録情報から確認できる範囲では、これまでの役割内で改善と価値提供を進めてきたこと",
                desired="これまで培った経験を、より広い対象や役割へ発展させること",
                gap="現在までの役割で実現してきた範囲と、今後広げたい価値提供の範囲に差があること",
                transition_necessity="これまでの経験を土台に、役割と価値提供の範囲を広げられる環境へ移る必要があること",
            )
        material = material.model_copy(
            update={
                "usable_points": filtered_points or [
                    "【整理案】登録済みの職歴で一貫している取り組みを起点に、今後広げたい役割とのGAPを説明する。"
                ],
                "questions": [],
                "star_examples": [],
                "structure_example": career_structure[:3],
                "career_gap": career_gap,
            }
        )
    elif material.career_gap is not None:
        material = material.model_copy(update={"career_gap": None})
    return material


def format_preparation_material(material: PreparationMaterial, theme_key: str = "") -> str:
    """保存前に利用者が編集できる準備メモへ整形する。"""

    sections = ["【回答に使える情報】\n" + "\n".join(f"・{row}" for row in material.usable_points)]
    if material.star_examples:
        star_rows = []
        for example in material.star_examples:
            star_rows.append(
                f"＜{example.title}＞\n"
                f"S・T：{example.situation_task}\n"
                f"A：{example.action}\n"
                f"R：{example.result}"
            )
        sections.append("【STARで整理した例】\n" + "\n\n".join(star_rows))
    if material.structure_example:
        sections.append(
            "【回答の構成例】\n"
            + "\n".join(
                f"{index}. {row}"
                for index, row in enumerate(material.structure_example, start=1)
            )
        )
    if material.career_gap:
        gap = material.career_gap
        sections.append(
            "【前職・現職とのGAP】\n"
            f"・実現できていたこと：{gap.achieved}\n"
            f"・実現しにくかったこと：{gap.limitation}\n"
            f"・今後実現したいこと：{gap.desired}\n"
            f"・具体的なGAP：{gap.gap}\n"
            f"・転職が必要な理由：{gap.transition_necessity}"
        )
    if material.questions:
        sections.append("【追加で整理・確認すること】\n" + "\n".join(f"・{row}" for row in material.questions))
    return "\n\n".join(sections)
