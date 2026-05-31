#!/usr/bin/env python3
"""행정안전부 도로명주소 DB → 건물명 가제티어 빌드.

juso 원본(공동주택/건물 DB)을 증류해 ``building_names.txt.gz`` 로 만든다.
**런타임이 아니라 빌드타임 도구** — 패키지에 넣을 정적 리소스를 한 번 생성한다.

소스 받기:
    business.juso.go.kr → 주소제공 → 공동주택 DB(권장, 가벼움) 또는 건물 DB
    (KOGL Type 1, 회원가입 필요). 압축 해제하면 ``|`` 구분 cp949 텍스트.

사용:
    python scripts/build_address_gazetteer.py \
        --src ~/Downloads/공동주택_전체분.txt \
        --col 9 --encoding cp949 \
        --out src/ko_pii/dictionaries/building_names.txt.gz \
        --max 50000

    # --col 은 건물명/단지명이 들어있는 0-기반 컬럼 인덱스.
    #   파일 첫 줄을 열어 어느 컬럼이 단지명인지 확인 후 지정.

접미사(빌딩/타워/자이/래미안 등)로 끝나는 이름은 패턴 룰이 이미 처리하므로
가제티어에서 제외한다 — 비접미사 고유명만 남겨 용량·오탐을 줄인다.
"""
from __future__ import annotations

import argparse
import gzip
import sys
from pathlib import Path

# 패턴 룰이 이미 잡는 접미사 — 가제티어에서 제외 (address._BLDG_SUFFIX 와 동기화)
_RULE_SUFFIXES = (
    "빌딩", "타워", "센터", "스퀘어", "플라자", "프라자", "오피스텔",
    "아파트", "맨션", "하이츠", "캐슬", "팰리스", "레지던스", "펜트하우스",
    "자이", "래미안", "푸르지오", "더샵", "아이파크", "힐스테이트", "디에이치",
    "e편한세상", "위브", "센트레빌", "롯데캐슬", "데시앙", "스위첸", "꿈에그린",
    "베르디움", "리슈빌", "코아루", "우미린", "한라비발디", "효성해링턴",
    "어울림", "하늘채", "호반써밋", "아크로", "써밋", "주공",
)


def _clean(name: str) -> str | None:
    name = name.strip().strip('"').strip()
    if not (2 <= len(name) <= 20):
        return None
    if name.isdigit():
        return None
    if any(name.endswith(sfx) for sfx in _RULE_SUFFIXES):
        return None  # 룰이 이미 처리
    # 한글/영숫자만 (공백·특수문자 포함 이름은 토큰 매칭 불가)
    if not all("가" <= c <= "힣" or c.isalnum() for c in name):
        return None
    return name


def main() -> int:
    ap = argparse.ArgumentParser(description="juso DB → 건물명 가제티어")
    ap.add_argument("--src", required=True, type=Path, help="juso 원본 텍스트")
    ap.add_argument("--col", required=True, type=int, help="건물명 컬럼 (0-기반)")
    ap.add_argument("--delim", default="|", help="구분자 (기본 |)")
    ap.add_argument("--encoding", default="cp949", help="인코딩 (기본 cp949)")
    ap.add_argument("--out", required=True, type=Path, help="출력 .txt.gz")
    ap.add_argument("--max", type=int, default=0, help="최대 항목 수 (0=무제한)")
    args = ap.parse_args()

    if not args.src.exists():
        print(f"[err] 소스 없음: {args.src}", file=sys.stderr)
        return 1

    names: set[str] = set()
    rows = 0
    with args.src.open(encoding=args.encoding, errors="replace") as f:
        for line in f:
            rows += 1
            parts = line.rstrip("\n").split(args.delim)
            if args.col >= len(parts):
                continue
            cleaned = _clean(parts[args.col])
            if cleaned:
                names.add(cleaned)

    ordered = sorted(names)
    if args.max and len(ordered) > args.max:
        ordered = ordered[: args.max]

    header = [
        "# ko-pii 건물명/단지명 가제티어",
        "# 출처: 행정안전부 도로명주소 DB (business.juso.go.kr, KOGL Type 1)",
        f"# 원본 {rows:,}행 → 비접미사 고유명 {len(ordered):,}건",
        "# 생성: scripts/build_address_gazetteer.py",
    ]
    body = "\n".join(header + ordered) + "\n"
    args.out.write_bytes(gzip.compress(body.encode("utf-8")))
    print(f"[ok] {rows:,}행 → {len(ordered):,}건 → {args.out} "
          f"({args.out.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
