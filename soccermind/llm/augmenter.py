"""ClaudeAugmenter — Anthropic SDK 로 득점자 재랭킹 + 해설 (설계 불변식 #3).

가드레일: 구조화 출력(JSON 스키마) + 스쿼드 멤버십 검증 + 실패 시 통계/템플릿 폴백.
Opus 4.8 은 temperature 미지원이므로 결정성은 스키마·검증·effort=low 로 확보.
client 주입으로 네트워크 없이 테스트 가능. anthropic 미설치/키 부재 시 available()=False.
"""

from __future__ import annotations

import json
import os

from .base import AugmentInput, AugmentResult, validate_against_squads
from .fallback import FallbackAugmenter, template_explanation
from .prompts import OUTPUT_SCHEMA, SYSTEM_PROMPT, build_input_payload

MODEL = "claude-opus-4-8"


class ClaudeAugmenter:
    name = "claude"

    def __init__(self, client=None, model: str = MODEL) -> None:
        self._client = client
        self.model = model
        self._fallback = FallbackAugmenter()

    def available(self) -> bool:
        if self._client is not None:
            return True
        if not os.environ.get("ANTHROPIC_API_KEY"):
            return False
        try:
            import anthropic  # noqa: F401
        except ImportError:
            return False
        return True

    def _make_client(self):
        import anthropic

        return anthropic.Anthropic()

    def run(self, inp: AugmentInput) -> AugmentResult:
        try:
            client = self._client or self._make_client()
            payload = build_input_payload(inp)
            resp = client.messages.create(
                model=self.model,
                max_tokens=2000,
                system=SYSTEM_PROMPT,
                output_config={"format": {"type": "json_schema", "schema": OUTPUT_SCHEMA},
                               "effort": "low"},
                messages=[{"role": "user", "content": json.dumps(payload, ensure_ascii=False)}],
            )
            text = next(b.text for b in resp.content if getattr(b, "type", None) == "text")
            data = json.loads(text)

            names_a = data["refined_scorers"]["a"]
            names_b = data["refined_scorers"]["b"]
            explanation = data.get("explanation") or template_explanation(inp)

            # 가드레일: 스쿼드 검증 실패 시 통계 랭킹으로 폴백 (불변식 #3)
            scorers_a = validate_against_squads(names_a, inp.squad_a, inp.scorers_a) or inp.scorers_a
            scorers_b = validate_against_squads(names_b, inp.squad_b, inp.scorers_b) or inp.scorers_b

            return AugmentResult(scorers_a=scorers_a, scorers_b=scorers_b, explanation=explanation)
        except Exception:
            # 네트워크/파싱/API 오류 → 통계 + 템플릿 폴백 (graceful degradation)
            return self._fallback.run(inp)
