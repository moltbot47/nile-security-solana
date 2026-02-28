"""Custom exception hierarchy with HTTP status code mapping."""

from fastapi import HTTPException


class NileBaseError(Exception):
    """Base exception for all NILE errors."""

    status_code: int = 500
    detail: str = "Internal server error"

    def __init__(self, detail: str | None = None) -> None:
        self.detail = detail or self.__class__.detail
        super().__init__(self.detail)

    def to_http(self) -> HTTPException:
        return HTTPException(status_code=self.status_code, detail=self.detail)


# --- 4xx Client Errors ---


class BadRequestError(NileBaseError):
    status_code = 400
    detail = "Bad request"


class InvalidAddressError(BadRequestError):
    detail = "Invalid Solana address"


class AuthenticationError(NileBaseError):
    status_code = 401
    detail = "Authentication required"


class ForbiddenError(NileBaseError):
    status_code = 403
    detail = "Access denied"


class NotFoundError(NileBaseError):
    status_code = 404
    detail = "Resource not found"


class ContractNotFoundError(NotFoundError):
    detail = "Contract not found"


class AgentNotFoundError(NotFoundError):
    detail = "Agent not found"


class RateLimitError(NileBaseError):
    status_code = 429
    detail = "Rate limit exceeded"


class CircuitBreakerError(NileBaseError):
    status_code = 423
    detail = "Trading paused — circuit breaker active"


# --- 5xx Server Errors ---


class AnalysisError(NileBaseError):
    status_code = 422
    detail = "Program analysis failed"


class ChainServiceError(NileBaseError):
    status_code = 502
    detail = "Solana RPC request failed"


class OnChainWriteError(NileBaseError):
    status_code = 502
    detail = "Failed to submit transaction on-chain"
