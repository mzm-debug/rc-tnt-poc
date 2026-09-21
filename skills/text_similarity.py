import re


def tokens(text: str) -> set[str]:
    return {x for x in re.split(r"\W+", (text or "").lower()) if len(x) > 2}


def jaccard(a: str, b: str) -> float:
    aa, bb = tokens(a), tokens(b)
    if not aa or not bb:
        return 0.0
    return len(aa & bb) / len(aa | bb)
