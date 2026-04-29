"""
Buenas prácticas frente a inyección SQL en este proyecto.

- Usar SQLAlchemy ORM (``select(Model).where(Model.campo == valor)``); los
  parámetros van enlazados, no concatenados a la cadena SQL.
- Evitar ``text("SELECT ... " + variable)``; si hace falta SQL crudo, usar
  ``text("SELECT ... WHERE x = :p").bindparams(p=valor)``.
- Entradas HTTP: validar con Pydantic (longitudes, tipos); limita textos largos
  y reduce superficie de abuso (DoS por payload).

La capa de repositorio actual no construye SQL dinámico desde strings de usuario.
"""
