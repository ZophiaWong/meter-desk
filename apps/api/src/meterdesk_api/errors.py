from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ApiErrorBody(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class MeterDeskAPIError(Exception):
    def __init__(
        self,
        *,
        status_code: int,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details or {}

    def body(self) -> dict[str, Any]:
        return ApiErrorBody(
            code=self.code,
            message=self.message,
            details=self.details,
        ).model_dump()
