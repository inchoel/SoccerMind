"""DataProvider 추상 인터페이스 (아키텍처 §4.2).

각 외부 소스는 이 뒤에 격리된다. available() 로 키/소스 부재 시 자동 스킵
→ graceful degradation (설계 불변식 #5).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..core.models import PartialTeamData, ResolvedTeam


class DataProvider(ABC):
    name: str = "base"

    @abstractmethod
    def available(self) -> bool:
        """키·네트워크 등 사용 가능 여부."""

    @abstractmethod
    def fetch(self, team: ResolvedTeam) -> PartialTeamData:
        """팀의 부분 데이터 반환. 실패 시 예외 대신 빈 PartialTeamData 권장."""
