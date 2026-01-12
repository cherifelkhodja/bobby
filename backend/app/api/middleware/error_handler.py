"""Error handling middleware."""

import logging
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse

from app.domain.exceptions import (
    CandidateAlreadyExistsError,
    CooptationNotFoundError,
    DomainError,
    InvalidCredentialsError,
    InvalidEmailError,
    InvalidPhoneError,
    InvalidTokenError,
    OpportunityNotFoundError,
    UserAlreadyExistsError,
    UserNotFoundError,
    UserNotVerifiedError,
)

logger = logging.getLogger(__name__)


async def error_handler_middleware(
    request: Request,
    call_next: Callable,
) -> Response:
    """Handle exceptions and convert to HTTP responses."""
    try:
        return await call_next(request)
    except InvalidCredentialsError:
        return JSONResponse(
            status_code=401,
            content={"detail": "Invalid email or password"},
        )
    except UserNotVerifiedError:
        return JSONResponse(
            status_code=403,
            content={"detail": "Email not verified. Please check your inbox."},
        )
    except InvalidTokenError as e:
        return JSONResponse(
            status_code=401,
            content={"detail": str(e.message)},
        )
    except UserNotFoundError as e:
        return JSONResponse(
            status_code=404,
            content={"detail": str(e.message)},
        )
    except UserAlreadyExistsError as e:
        return JSONResponse(
            status_code=409,
            content={"detail": str(e.message)},
        )
    except CandidateAlreadyExistsError as e:
        return JSONResponse(
            status_code=409,
            content={"detail": str(e.message)},
        )
    except OpportunityNotFoundError as e:
        return JSONResponse(
            status_code=404,
            content={"detail": str(e.message)},
        )
    except CooptationNotFoundError as e:
        return JSONResponse(
            status_code=404,
            content={"detail": str(e.message)},
        )
    except InvalidEmailError as e:
        return JSONResponse(
            status_code=422,
            content={"detail": str(e.message)},
        )
    except InvalidPhoneError as e:
        return JSONResponse(
            status_code=422,
            content={"detail": str(e.message)},
        )
    except DomainError as e:
        logger.warning(f"Domain error: {e.message}")
        return JSONResponse(
            status_code=400,
            content={"detail": str(e.message)},
        )
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={"detail": str(e)},
        )
    except Exception as e:
        logger.exception(f"Unhandled exception: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )
