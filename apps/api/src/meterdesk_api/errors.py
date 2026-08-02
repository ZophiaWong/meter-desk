from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ApiErrorBody(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
    request_id: str


class MeterDeskAPIError(Exception):
    def __init__(
        self,
        *,
        status_code: int,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details or {}
        self.headers = headers or {}

    def body(self, *, request_id: str) -> dict[str, Any]:
        return ApiErrorBody(
            code=self.code,
            message=self.message,
            details=self.details,
            request_id=request_id,
        ).model_dump()
