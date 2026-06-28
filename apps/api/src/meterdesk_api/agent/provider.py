from __future__ import annotations

import asyncio
import json
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pydantic import BaseModel, ConfigDict, Field, ValidationError


class AgentProviderError(Exception):
    pass


class AgentProviderInput(BaseModel):
    ticket_id: str
    scenario: str = "duplicate_charge"
    account_name: str
    invoice_id: str
    charge_ids: list[str]
    policy_citation: str
    policy_citations: list[str] = Field(default_factory=list)
    decision_outcome: str
    decision_reason: str
    action_type: str | None = None
    amount_display: str | None = None
    target_charge_id: str | None = None
    target_credit_id: str | None = None
    target_subscription_id: str | None = None


class AgentDraftOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    recommendation: str
    internal_resolution: str
    customer_reply: str


class AgentResolutionProvider(Protocol):
    model: str

    async def create_resolution(self, provider_input: AgentProviderInput) -> AgentDraftOutput: ...


class OpenAICompatibleProvider:
    def __init__(self, *, api_key: str, model: str, base_url: str) -> None:
        self._api_key = api_key
        self.model = model
        self._base_url = base_url.rstrip("/")

    async def create_resolution(self, provider_input: AgentProviderInput) -> AgentDraftOutput:
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You draft governed billing-support recommendations for MeterDesk. "
                        "The backend decision_outcome is authoritative; do not reclassify the "
                        "case or include a separate outcome. Customer replies are draft-only and "
                        "must not promise that an unapproved refund or credit has happened."
                    ),
                },
                {
                    "role": "user",
                    "content": provider_input.model_dump_json(),
                },
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "meterdesk_agent_resolution",
                    "strict": True,
                    "schema": AgentDraftOutput.model_json_schema(),
                },
            },
        }

        response_body = await asyncio.to_thread(self._post_chat_completion, payload)
        try:
            data = json.loads(response_body)
            content = data["choices"][0]["message"]["content"]
            output = AgentDraftOutput.model_validate_json(content)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError, ValidationError) as error:
            raise AgentProviderError("invalid structured output") from error

        validate_provider_output(output)
        return output

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
            raise AgentProviderError(f"provider HTTP {error.code}: {body}") from error
        except URLError as error:
            raise AgentProviderError(f"provider request failed: {error.reason}") from error


def validate_provider_output(output: AgentDraftOutput) -> None:
    if not output.recommendation.strip():
        raise AgentProviderError("provider recommendation is empty")
    if not output.internal_resolution.strip():
        raise AgentProviderError("provider internal resolution is empty")
    if not output.customer_reply.strip():
        raise AgentProviderError("provider customer draft is empty")
    if _promises_unapproved_financial_action(output.customer_reply):
        raise AgentProviderError("customer draft promises unapproved financial action")


def _promises_unapproved_financial_action(value: str) -> bool:
    normalized = value.lower()
    unsafe_phrases = (
        "will refund",
        "we will refund",
        "will credit",
        "we will credit",
        "refund has been",
        "credit has been",
        "has been refunded",
        "has been credited",
    )
    return any(phrase in normalized for phrase in unsafe_phrases)
