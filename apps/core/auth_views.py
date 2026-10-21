"""Login con límite de intentos fallidos (evita adivinar contraseñas)."""

from django.contrib import messages
from django.contrib.auth.views import LoginView

from .ratelimit import client_ip, hit, is_limited, reset

LOGIN_SCOPE = "login"
LOGIN_MAX_FAILURES = 5
LOGIN_WINDOW_S = 15 * 60


class RateLimitedLoginView(LoginView):
    """5 intentos fallidos por IP o por usuario bloquean 15 minutos."""

    def _idents(self, request):
        username = (request.POST.get("username") or "").strip().casefold()
        idents = ["ip:" + client_ip(request)]
        if username:
            idents.append("user:" + username)
        return idents

    def post(self, request, *args, **kwargs):
        if any(is_limited(LOGIN_SCOPE, ident, LOGIN_MAX_FAILURES) for ident in self._idents(request)):
            messages.error(
                request,
                "Demasiados intentos fallidos. Espera 15 minutos e intenta de nuevo.",
            )
            return self.get(request, *args, **kwargs)
        return super().post(request, *args, **kwargs)

    def form_invalid(self, form):
        for ident in self._idents(self.request):
            hit(LOGIN_SCOPE, ident, LOGIN_WINDOW_S)
        return super().form_invalid(form)

    def form_valid(self, form):
        for ident in self._idents(self.request):
            reset(LOGIN_SCOPE, ident)
        return super().form_valid(form)
