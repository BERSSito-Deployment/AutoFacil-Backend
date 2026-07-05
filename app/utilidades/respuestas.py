from fastapi import HTTPException, status


def error_no_encontrado(detalle: str) -> HTTPException:

    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detalle)


def error_validacion(detalle: str) -> HTTPException:

    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detalle)


def error_conflicto(detalle: str) -> HTTPException:

    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detalle)


def error_autenticacion(detalle: str) -> HTTPException:

    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detalle,
        headers={"WWW-Authenticate": "Bearer"},
    )
