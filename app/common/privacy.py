import re


def enmascarar_email(email: str) -> str:
    limpio = (email or "").strip()
    if "@" not in limpio:
        return "***"
    local, dominio = limpio.rsplit("@", 1)
    prefijo = local[:2] if len(local) >= 2 else local[:1]
    return f"{prefijo}***@{dominio}"


def enmascarar_telefono(telefono: str) -> str:
    digitos = re.sub(r"\D", "", telefono or "")
    if len(digitos) < 4:
        return "***"
    return f"***{digitos[-4:]}"
