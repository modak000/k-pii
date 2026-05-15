"""사전 (Dictionaries) — 한국 공공 부문 도메인 특화 어휘 자원.

데이터 출처는 각 모듈의 docstring 참고. 모두 공개데이터 / 공식 자료에서 추출.
"""
from k_pii.dictionaries.surnames import KOREAN_SURNAMES, is_surname
from k_pii.dictionaries.titles import (
    TITLES, TITLES_GOV, ALL_GOV_TITLES,
    TITLES_POLICE, TITLES_FIRE, TITLES_MILITARY,
    TITLES_DIPLOMAT, TITLES_PROSECUTOR, TITLES_JUDGE,
    is_title, is_gov_title, title_domain,
)
from k_pii.dictionaries.agencies import (
    AGENCIES, MINISTRIES, SERVICES, AGENCIES_CHEONG,
    COMMISSIONS, JUDICIAL, LOCAL_GOV, PUBLIC_CORPS,
    is_agency, is_ministry, is_cheong, is_commission, is_local_gov,
)
from k_pii.dictionaries.agency_abbrev import (
    KOR_ABBREV_TO_FULL, ENG_ABBREV_TO_KOR,
    DOC_ID_PREFIXES, normalize_agency, is_doc_id_prefix,
)
from k_pii.dictionaries.districts import (
    PROVINCES, PROVINCE_ABBREV,
    SEOUL_DISTRICTS, METRO_DISTRICTS, ALL_CITIES_GUNS, ALL_DISTRICTS,
    is_province, is_district, is_admin_unit, normalize_province,
)
from k_pii.dictionaries.field_labels import FIELD_LABELS, is_field_label
from k_pii.dictionaries.common_words import COMMON_WORDS, is_common_word

__all__ = [
    # surnames
    "KOREAN_SURNAMES", "is_surname",
    # titles
    "TITLES", "TITLES_GOV", "ALL_GOV_TITLES",
    "TITLES_POLICE", "TITLES_FIRE", "TITLES_MILITARY",
    "TITLES_DIPLOMAT", "TITLES_PROSECUTOR", "TITLES_JUDGE",
    "is_title", "is_gov_title", "title_domain",
    # agencies
    "AGENCIES", "MINISTRIES", "SERVICES", "AGENCIES_CHEONG",
    "COMMISSIONS", "JUDICIAL", "LOCAL_GOV", "PUBLIC_CORPS",
    "is_agency", "is_ministry", "is_cheong", "is_commission", "is_local_gov",
    # abbreviations
    "KOR_ABBREV_TO_FULL", "ENG_ABBREV_TO_KOR",
    "DOC_ID_PREFIXES", "normalize_agency", "is_doc_id_prefix",
    # districts
    "PROVINCES", "PROVINCE_ABBREV",
    "SEOUL_DISTRICTS", "METRO_DISTRICTS", "ALL_CITIES_GUNS", "ALL_DISTRICTS",
    "is_province", "is_district", "is_admin_unit", "normalize_province",
    # other
    "FIELD_LABELS", "is_field_label",
    "COMMON_WORDS", "is_common_word",
]
