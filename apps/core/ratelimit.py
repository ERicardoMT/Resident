"""Límite de intentos con el caché de Django (sin paquetes extra).

Se usa para el login y para el PDF de mediciones. Con el caché por defecto
(LocMemCache) el conteo vive en el proceso de runserver; si algún día se usan
varios procesos, configurar un caché compartido (Redis o base de datos).
"""

from __future__ import annotations

from django.core.cache import cache


def client_ip(request) -> str:
    """IP del cliente. Detrás del túnel REMOTE_ADDR siempre es 127.0.0.1,
    así que se usa la primera IP de X-Forwarded-For cuando existe."""
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "") or "desconocida"


def _key(scope: str, ident: str) -> str:
    return f"smav-ratelimit:{scope}:{ident}"


def is_limited(scope: str, ident: str, limit: int) -> bool:
    """True si ident ya llegó al límite en la ventana actual."""
    return cache.get(_key(scope, ident), 0) >= limit


def hit(scope: str, ident: str, window_s: int) -> int:
    """Suma un intento; la ventana empieza con el primer intento."""
    key = _key(scope, ident)
    if cache.add(key, 1, timeout=window_s):
        return 1
    try:
        return cache.incr(key)
    except ValueError:
        # Expiró entre add() e incr()
        cache.set(key, 1, timeout=window_s)
        return 1


def reset(scope: str, ident: str) -> None:
    cache.delete(_key(scope, ident))
