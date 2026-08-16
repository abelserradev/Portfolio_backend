from app.common.privacy import enmascarar_email, enmascarar_telefono


def test_enmascarar_email_oculta_local() -> None:
    assert enmascarar_email("juan@ejemplo.com") == "ju***@ejemplo.com"


def test_enmascarar_telefono_muestra_ultimos_digitos() -> None:
    assert enmascarar_telefono("+584121234567") == "***4567"
