"""評価済みの点数を変えず、利用者向けの説明を整える。"""
import re


def normalize_matching_points(text: str) -> str:
    lines = (text or '').splitlines()
    employment = None
    for line in lines:
        if re.match(r'^\s*[・●-]?\s*雇用形態[：:]', line):
            old = re.search(r'求人の雇用形態「([^」]+)」は、希望する雇用形態に含まれています', line)
            current = re.search(r'希望する雇用形態「([^」]+)」と求人の雇用形態「\1」が一致しています', line)
            found = old or current
            if found:
                employment = found.group(1)
                break
    if employment is None:
        return text
    result = []
    for line in lines:
        line = re.sub(r'求人の雇用形態「([^」]+)」は、希望する雇用形態に含まれています', r'希望する雇用形態「\1」と求人の雇用形態「\1」が一致しています', line)
        title, separator, reason = line.lstrip(' ・●-').partition('：')
        if (separator and title.strip() == employment and '雇用形態' in reason
                and employment in reason and ('合致' in reason or '一致' in reason)
                and not any(word in reason for word in ('不一致', '一部一致', '登用', '試用', '転換'))):
            continue
        result.append(line)
    return '\n'.join(result)
