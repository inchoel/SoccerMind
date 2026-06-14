"""국가명 별칭 테이블 — 표준키(ISO/FIFA alpha-3) ↔ 한/영 별칭 + 소스별 식별자.

설계 불변식 #4: 소스마다 팀명이 다르므로 매핑을 여기 한 곳에 집중한다.

- elo_name: **eloratings.net 의 2글자 코드**(예: 한국=KR, 체코=CZ, 잉글랜드=EN).
  주의: 풀네임이 아니다! World.tsv 가 코드를 쓰므로 코드가 아니면 매칭 실패 → 기본 1500.
  여기 값들은 라이브 World.tsv 로 검증됨.
- wikipedia: 영문 문서 제목 (스쿼드/폼 파싱용).
- fd_id/api_football_id: 검증된 값만. 잘못된 ID 는 다른 팀 스쿼드를 가져온다
  (예: football-data 770 = England ≠ Korea) → 미검증이면 None.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TeamAlias:
    key: str  # ISO/FIFA alpha-3
    display: str  # 한국어 표시명
    aliases: tuple[str, ...]  # 한/영 입력 별칭 (display·key 는 자동 포함)
    elo_name: str  # eloratings.net 2글자 코드 (검증 완료)
    wikipedia: str  # Wikipedia 문서 제목
    fd_id: int | None = None
    api_football_id: int | None = None


# 월드컵·대륙대회 주요 진출국. elo_name 은 라이브 World.tsv 로 검증된 2글자 코드.
# 별칭은 소문자 비교되므로 대소문자 무관.
TEAMS: tuple[TeamAlias, ...] = (
    # --- UEFA ---
    TeamAlias("ESP", "스페인", ("spain", "espana", "españa"), "ES",
              "Spain national football team"),
    TeamAlias("FRA", "프랑스", ("france",), "FR", "France national football team"),
    TeamAlias("ENG", "잉글랜드", ("england",), "EN", "England national football team"),
    TeamAlias("POR", "포르투갈", ("portugal",), "PT", "Portugal national football team"),
    TeamAlias("NED", "네덜란드", ("netherlands", "holland", "nederland"), "NL",
              "Netherlands national football team"),
    TeamAlias("GER", "독일", ("germany", "deutschland"), "DE",
              "Germany national football team"),
    TeamAlias("CRO", "크로아티아", ("croatia", "hrvatska"), "HR",
              "Croatia national football team"),
    TeamAlias("ITA", "이탈리아", ("italy", "italia"), "IT", "Italy national football team"),
    TeamAlias("BEL", "벨기에", ("belgium",), "BE", "Belgium national football team"),
    TeamAlias("TUR", "튀르키예", ("turkey", "türkiye", "turkiye", "터키"), "TR",
              "Turkey national football team"),
    TeamAlias("DEN", "덴마크", ("denmark",), "DK", "Denmark national football team"),
    TeamAlias("SUI", "스위스", ("switzerland", "swiss"), "CH",
              "Switzerland national football team"),
    TeamAlias("AUT", "오스트리아", ("austria",), "AT", "Austria national football team"),
    TeamAlias("NOR", "노르웨이", ("norway",), "NO", "Norway national football team"),
    TeamAlias("UKR", "우크라이나", ("ukraine",), "UA", "Ukraine national football team"),
    TeamAlias("SRB", "세르비아", ("serbia",), "RS", "Serbia national football team"),
    TeamAlias("SCO", "스코틀랜드", ("scotland",), "SQ", "Scotland national football team"),
    TeamAlias("WAL", "웨일스", ("wales",), "WA", "Wales national football team"),
    TeamAlias("IRL", "아일랜드", ("ireland", "republic of ireland"), "IE",
              "Republic of Ireland national football team"),
    TeamAlias("GRE", "그리스", ("greece",), "GR", "Greece national football team"),
    TeamAlias("HUN", "헝가리", ("hungary",), "HU", "Hungary national football team"),
    TeamAlias("SWE", "스웨덴", ("sweden",), "SE", "Sweden men's national football team"),
    TeamAlias("POL", "폴란드", ("poland",), "PL", "Poland national football team"),
    TeamAlias("CZE", "체코", ("czech", "czechia", "czech republic"), "CZ",
              "Czech Republic national football team"),
    TeamAlias("SVK", "슬로바키아", ("slovakia",), "SK", "Slovakia national football team"),
    TeamAlias("SVN", "슬로베니아", ("slovenia",), "SI", "Slovenia national football team"),
    TeamAlias("ROU", "루마니아", ("romania",), "RO", "Romania national football team"),
    TeamAlias("GEO", "조지아", ("georgia", "그루지야"), "GE", "Georgia national football team"),
    # --- CONMEBOL ---
    TeamAlias("ARG", "아르헨티나", ("argentina",), "AR", "Argentina national football team"),
    TeamAlias("BRA", "브라질", ("brazil", "brasil"), "BR", "Brazil national football team"),
    TeamAlias("URU", "우루과이", ("uruguay",), "UY", "Uruguay national football team"),
    TeamAlias("COL", "콜롬비아", ("colombia",), "CO", "Colombia national football team"),
    TeamAlias("ECU", "에콰도르", ("ecuador",), "EC", "Ecuador national football team"),
    TeamAlias("CHI", "칠레", ("chile",), "CL", "Chile national football team"),
    TeamAlias("PAR", "파라과이", ("paraguay",), "PY", "Paraguay national football team"),
    TeamAlias("PER", "페루", ("peru",), "PE", "Peru national football team"),
    TeamAlias("VEN", "베네수엘라", ("venezuela",), "VE", "Venezuela national football team"),
    TeamAlias("BOL", "볼리비아", ("bolivia",), "BO", "Bolivia national football team"),
    # --- CONCACAF ---
    TeamAlias("MEX", "멕시코", ("mexico",), "MX", "Mexico national football team"),
    TeamAlias("USA", "미국", ("united states", "usa", "us"), "US",
              "United States men's national soccer team"),
    TeamAlias("CAN", "캐나다", ("canada",), "CA", "Canada men's national soccer team"),
    TeamAlias("CRC", "코스타리카", ("costa rica",), "CR", "Costa Rica national football team"),
    TeamAlias("PAN", "파나마", ("panama",), "PA", "Panama national football team"),
    TeamAlias("HON", "온두라스", ("honduras",), "HN", "Honduras national football team"),
    TeamAlias("JAM", "자메이카", ("jamaica",), "JM", "Jamaica national football team"),
    # --- AFC ---
    TeamAlias("JPN", "일본", ("japan",), "JP", "Japan national football team"),
    TeamAlias("KOR", "대한민국", ("한국", "남한", "korea", "south korea", "korea republic",
              "republic of korea"), "KR", "South Korea national football team"),
    TeamAlias("PRK", "북한", ("조선", "north korea", "dpr korea", "korea dpr"), "KP",
              "North Korea national football team"),
    TeamAlias("IRN", "이란", ("iran",), "IR", "Iran national football team"),
    TeamAlias("KSA", "사우디아라비아", ("사우디", "saudi arabia", "saudi"), "SA",
              "Saudi Arabia national football team"),
    TeamAlias("QAT", "카타르", ("qatar",), "QA", "Qatar national football team"),
    TeamAlias("IRQ", "이라크", ("iraq",), "IQ", "Iraq national football team"),
    TeamAlias("UAE", "아랍에미리트", ("uae", "united arab emirates", "에미리트"), "AE",
              "United Arab Emirates national football team"),
    TeamAlias("UZB", "우즈베키스탄", ("uzbekistan", "우즈벡"), "UZ",
              "Uzbekistan national football team"),
    TeamAlias("JOR", "요르단", ("jordan",), "JO", "Jordan national football team"),
    TeamAlias("AUS", "호주", ("australia", "오스트레일리아"), "AU",
              "Australia men's national soccer team"),
    # --- CAF ---
    TeamAlias("MAR", "모로코", ("morocco", "maroc"), "MA", "Morocco national football team"),
    TeamAlias("SEN", "세네갈", ("senegal",), "SN", "Senegal national football team"),
    TeamAlias("GHA", "가나", ("ghana",), "GH", "Ghana national football team"),
    TeamAlias("NGA", "나이지리아", ("nigeria",), "NG", "Nigeria national football team"),
    TeamAlias("CMR", "카메룬", ("cameroon",), "CM", "Cameroon national football team"),
    TeamAlias("CIV", "코트디부아르", ("ivory coast", "cote d'ivoire", "cote divoire"), "CI",
              "Ivory Coast national football team"),
    TeamAlias("ALG", "알제리", ("algeria",), "DZ", "Algeria national football team"),
    TeamAlias("TUN", "튀니지", ("tunisia",), "TN", "Tunisia national football team"),
    TeamAlias("EGY", "이집트", ("egypt",), "EG", "Egypt national football team"),
    TeamAlias("RSA", "남아프리카공화국", ("south africa", "남아공"), "ZA",
              "South Africa national football team"),
    TeamAlias("MLI", "말리", ("mali",), "ML", "Mali national football team"),
    TeamAlias("CPV", "카보베르데", ("cape verde",), "CV", "Cape Verde national football team"),
    TeamAlias("COD", "콩고민주공화국", ("dr congo", "콩고", "democratic republic of congo"),
              "CD", "DR Congo national football team"),
    # --- OFC ---
    TeamAlias("NZL", "뉴질랜드", ("new zealand",), "NZ",
              "New Zealand men's national football team"),
)
