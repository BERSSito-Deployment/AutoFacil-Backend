import bcrypt


def hashear_password(password: str) -> str:

    bytes_password = password.encode("utf-8")
    if len(bytes_password) > 72:
        raise ValueError(
            "La contraseña es demasiado larga (maximo 72 bytes en UTF-8)."
        )
    sal = bcrypt.gensalt()
    return bcrypt.hashpw(bytes_password, sal).decode("utf-8")


def verificar_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(
            password.encode("utf-8"), password_hash.encode("utf-8")
        )
    except ValueError:
        return False
