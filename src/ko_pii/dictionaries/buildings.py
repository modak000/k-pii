"""건물명/단지명 가제티어 — 접미사 룰로 못 잡는 비접미사 고유명 보완.

데이터 출처: 행정안전부 도로명주소 공동주택/건물 DB
(business.juso.go.kr, KOGL Type 1). 번들된 ``building_names.txt.gz`` 는
시드(소량)이며, 전체 가제티어는 ``scripts/build_address_gazetteer.py`` 로
juso 원본에서 생성·교체한다.

**런타임은 완전 오프라인** — 네트워크 접근 없이 번들 리소스만 읽는다.
빌드타임에 juso 데이터를 증류해 패키지에 넣을 뿐, 런타임 의존성은 없다.
"""
from __future__ import annotations

import gzip
from functools import lru_cache
from importlib.resources import files

_RESOURCE = "building_names.txt.gz"


@lru_cache(maxsize=1)
def _load() -> frozenset:
    """번들된 gzip 가제티어를 frozenset 으로 lazy 로드. 없으면 빈 set."""
    try:
        raw = files("ko_pii.dictionaries").joinpath(_RESOURCE).read_bytes()
    except (FileNotFoundError, ModuleNotFoundError, OSError):
        return frozenset()
    text = gzip.decompress(raw).decode("utf-8")
    return frozenset(
        ln.strip() for ln in text.splitlines()
        if ln.strip() and not ln.startswith("#")
    )


def is_building_name(token: str) -> bool:
    """``token`` 이 알려진 건물명/단지명인지 (가제티어 멤버십)."""
    return token in _load()


def building_names() -> frozenset:
    """전체 건물명 가제티어 (frozenset)."""
    return _load()
