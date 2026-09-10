from app.common.url_safety import es_url_redireccion_segura


def test_url_https_permitida() -> None:
    assert es_url_redireccion_segura("https://demo.example.com/path") is True


def test_url_http_rechazada() -> None:
    assert es_url_redireccion_segura("http://inseguro.example.com") is False


def test_url_javascript_rechazada() -> None:
    assert es_url_redireccion_segura("javascript:alert(1)") is False
