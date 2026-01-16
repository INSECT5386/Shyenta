import json

PUA_START = 0xE000

PHONEME_LIST = [
    # 모음
    "a","i","u","e","o",
    "w", "y",

    # 자음
    "n","m","h","s","c","k","f",
    "j","v","t","r","l","g", "d"
]

# 길이 긴 음소 우선 매칭을 위해 정렬
PHONEME_ORDER = sorted(PHONEME_LIST, key=len, reverse=True)

ROMA_TO_PUA = {
    roma: chr(PUA_START + i)
    for i, roma in enumerate(PHONEME_ORDER)
}

def roman_to_pua(s: str) -> str:
    out = []
    i = 0
    while i < len(s):
        matched = False
        for roma in PHONEME_ORDER:
            if s.startswith(roma, i):
                out.append(ROMA_TO_PUA[roma])
                i += len(roma)
                matched = True
                break
        if not matched:
            # 매칭 안 되는 문자는 그대로 통과
            out.append(s[i])
            i += 1
    return "".join(out)

def convert_all(obj):
    if isinstance(obj, dict):
        new_dict = {}
        for k, v in obj.items():
            new_key = roman_to_pua(k) if isinstance(k, str) else k
            new_dict[new_key] = convert_all(v)
        return new_dict
    elif isinstance(obj, list):
        return [convert_all(x) for x in obj]
    elif isinstance(obj, str):
        return roman_to_pua(obj)
    else:
        return obj

def main():
    with open("ConlangV2.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    converted = convert_all(data)

    with open("conlang_pua.json", "w", encoding="utf-8") as f:
        json.dump(converted, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
