from pydantic import BaseModel


class ErrorResponse(BaseModel):
    detail: str
    error_code: str


class SuccessResponse(BaseModel):
    message: str
    data: dict | None = None
