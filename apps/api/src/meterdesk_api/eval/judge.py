from __future__ import annotations

import asyncio
import json
from typing import Literal, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pydantic import BaseModel, ConfigDict, ValidationError


class EvalJudgeError(Exception):
    pass


class EvalDraftJudgeInput(BaseModel):
    outcome: str
    internal_resolution: str
    customer_reply: str


class EvalDraftJudgeOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    score: Literal["pass", "fail"]
    notes: str


class EvalDraftJudge(Protocol):
    async def judge(self, judge_input: EvalDraftJudgeInput) -> EvalDraftJudgeOutput: ...


class OpenAICompatibleEvalJudge:
    def __init__(self, *, api_key: str, model: str, base_url: str) -> None:
        self._api_key = api_key
        self._model = model
        self._base_url = base_url.rstrip("/")

    async def judge(self, judge_input: EvalDraftJudgeInput) -> EvalDraftJudgeOutput:
        payload = {
            "model": self._model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are an advisory evaluator for MeterDesk draft quality. "
                        "Judge clarity, professionalism, and readability only. "
                        "Return pass when the draft is acceptable for human review."
                    ),
                },
                {"role": "user", "content": judge_input.model_dump_json()},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "meterdesk_eval_draft_judge",
                    "strict": True,
                    "schema": EvalDraftJudgeOutput.model_json_schema(),
                },
            },
        }
        response_body = await asyncio.to_thread(self._post_chat_completion, payload)
        try:
            data = json.loads(response_body)
            content = data["choices"][0]["message"]["content"]
            return EvalDraftJudgeOutput.model_validate_json(content)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError, ValidationError) as error:
            raise EvalJudgeError("invalid judge structured output") from error

    def _post_chat_completion(self, payload: dict[str, object]) -> str:
        request = Request(
            f"{self._base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=30) as response:
                return response.read().decode("utf-8")
        except HTTPError as error:
            body = error.read().decode("utf-8", errors="replace")
            raise EvalJudgeError(f"judge HTTP {error.code}: {body}") from error
        except URLError as error:
            raise EvalJudgeError(f"judge request failed: {error.reason}") from error
