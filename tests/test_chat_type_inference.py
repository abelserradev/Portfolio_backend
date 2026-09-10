from app.services.chat_type_inference import (
    formatear_rango_combinado_usd,
    inferir_tipos_proyecto,
    fusionar_tipos_proyecto,
)

MATRIZ_EJEMPLO = {
    "ranges": {
        "landing_simple": {"min_usd": 800, "max_usd": 2500},
        "app_movil": {"min_usd": 5000, "max_usd": 15000},
    }
}


def test_inferir_landing_y_app_en_mismo_mensaje() -> None:
    tipos = inferir_tipos_proyecto("Necesito una web para mi tienda y también una app móvil")
    assert "landing_simple" in tipos
    assert "app_movil" in tipos


def test_fusionar_tipos_mantiene_orden_estable() -> None:
    merged = fusionar_tipos_proyecto(["app_movil"], ["landing_simple"])
    assert merged.index("landing_simple") < merged.index("app_movil")


def test_rango_combinado_suma_min_max() -> None:
    rango = formatear_rango_combinado_usd(["landing_simple", "app_movil"], MATRIZ_EJEMPLO)
    assert rango == "USD 5,800 – 17,500"
