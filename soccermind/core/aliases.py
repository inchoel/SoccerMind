"""국가명 별칭 테이블 — 표준키(ISO alpha-3) ↔ 한/영 별칭 + 소스별 식별자.

설계 불변식 #4: 소스마다 팀명이 다르므로 매핑을 여기 한 곳에 집중한다.
숫자 ID(fd_id/api_football_id)는 확실한 경우만 채우고 불확실하면 None — 잘못된 ID는
빈 값보다 나쁘다. Provider 는 elo_name/wikipedia/display 로 폴백 조회할 수 있다.
확장 방법: 아래 TEAMS 에 항목 추가 (월드컵 본선 진출국 위주).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TeamAlias:
    key: str  # ISO 3166-1 alpha-3
    display: str  # 한국어 표시명
    aliases: tuple[str, ...]  # 한/영 입력 별칭 (display·key 는 자동 포함)
    elo_name: str  # eloratings.net 표기
    wikipedia: str  # Wikipedia 문서 제목
    fd_id: int | None = None
    api_football_id: int | None = None


# 월드컵 단골 진출국 (확장 가능). 별칭은 소문자 비교되므로 대소문자 무관.
TEAMS: tuple[TeamAlias, ...] = (
    # 주의: fd_id/api_football_id 는 검증된 값만 채울 것. 잘못된 ID 는 다른 팀 스쿼드를
    # 가져오는 심각한 버그를 유발한다(예: football-data id 770 = England ≠ Korea).
    # 미검증이면 None 으로 두면 Wikipedia(문서 제목 기반)가 올바른 스쿼드를 제공한다.
    TeamAlias("KOR", "대한민국", ("한국", "남한", "korea", "south korea", "korea republic",
              "republic of korea"), "Korea South", "South Korea national football team"),
    TeamAlias("PRK", "북한", ("조선", "north korea", "dpr korea", "korea dpr"),
              "Korea North", "North Korea national football team"),
    TeamAlias("JPN", "일본", ("japan",), "Japan", "Japan national football team"),
    TeamAlias("BRA", "브라질", ("brazil", "brasil"), "Brazil", "Brazil national football team"),
    TeamAlias("ARG", "아르헨티나", ("argentina",), "Argentina",
              "Argentina national football team"),
    TeamAlias("FRA", "프랑스", ("france",), "France", "France national football team"),
    TeamAlias("ESP", "스페인", ("spain", "espana", "españa"), "Spain",
              "Spain national football team"),
    TeamAlias("ENG", "잉글랜드", ("england",), "England", "England national football team"),
    TeamAlias("GER", "독일", ("germany", "deutschland"), "Germany",
              "Germany national football team"),
    TeamAlias("NED", "네덜란드", ("netherlands", "holland", "nederland"), "Netherlands",
              "Netherlands national football team"),
    TeamAlias("POR", "포르투갈", ("portugal",), "Portugal", "Portugal national football team"),
    TeamAlias("BEL", "벨기에", ("belgium",), "Belgium", "Belgium national football team"),
    TeamAlias("ITA", "이탈리아", ("italy", "italia"), "Italy", "Italy national football team"),
    TeamAlias("CRO", "크로아티아", ("croatia", "hrvatska"), "Croatia",
              "Croatia national football team"),
    TeamAlias("URU", "우루과이", ("uruguay",), "Uruguay", "Uruguay national football team"),
    TeamAlias("COL", "콜롬비아", ("colombia",), "Colombia", "Colombia national football team"),
    TeamAlias("MEX", "멕시코", ("mexico",), "Mexico", "Mexico national football team"),
    TeamAlias("USA", "미국", ("united states", "usa", "us"), "USA",
              "United States men's national soccer team"),
    TeamAlias("CAN", "캐나다", ("canada",), "Canada", "Canada men's national soccer team"),
    TeamAlias("MAR", "모로코", ("morocco", "maroc"), "Morocco",
              "Morocco national football team"),
    TeamAlias("SEN", "세네갈", ("senegal",), "Senegal", "Senegal national football team"),
    TeamAlias("GHA", "가나", ("ghana",), "Ghana", "Ghana national football team"),
    TeamAlias("NGA", "나이지리아", ("nigeria",), "Nigeria", "Nigeria national football team"),
    TeamAlias("CMR", "카메룬", ("cameroon",), "Cameroon", "Cameroon national football team"),
    TeamAlias("SUI", "스위스", ("switzerland", "swiss"), "Switzerland",
              "Switzerland national football team"),
    TeamAlias("DEN", "덴마크", ("denmark",), "Denmark", "Denmark national football team"),
    TeamAlias("POL", "폴란드", ("poland",), "Poland", "Poland national football team"),
    TeamAlias("SRB", "세르비아", ("serbia",), "Serbia", "Serbia national football team"),
    TeamAlias("AUS", "호주", ("australia", "오스트레일리아"), "Australia",
              "Australia men's national soccer team"),
    TeamAlias("KSA", "사우디아라비아", ("사우디", "saudi arabia", "saudi"), "Saudi Arabia",
              "Saudi Arabia national football team"),
    TeamAlias("IRN", "이란", ("iran",), "Iran", "Iran national football team"),
    TeamAlias("ECU", "에콰도르", ("ecuador",), "Ecuador", "Ecuador national football team"),
)
