"""Pruebas de vistas, permisos y protecciones del sitio.

Se corren con: python manage.py test
"""

import numpy as np
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from apps.core.auth_views import LOGIN_MAX_FAILURES
from apps.core.models import CatalogItem
from apps.vibration import views as vibration_views


class AccessAndSecurityTests(TestCase):

    def setUp(self):
        cache.clear()
        CatalogItem.objects.create(name="CDC-2", category="antivibratorios", subcategory="colgantes")

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response["Location"])

    def test_product_detail_404_when_missing(self):
        self.assertEqual(self.client.get("/catalogo/producto/CDC-2/").status_code, 200)
        self.assertEqual(self.client.get("/catalogo/producto/NO-EXISTE/").status_code, 404)

    def test_pages_cannot_be_framed(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response["X-Frame-Options"], "DENY")


class LoginRateLimitTests(TestCase):

    def setUp(self):
        cache.clear()
        get_user_model().objects.create_user("marcos", password="clave-correcta-123")

    def login(self, password):
        return self.client.post(reverse("login"), {"username": "marcos", "password": password}, follow=True)

    def test_correct_password_logs_in(self):
        response = self.login("clave-correcta-123")
        self.assertTrue(response.context["user"].is_authenticated)

    def test_blocks_after_too_many_failures(self):
        for _ in range(LOGIN_MAX_FAILURES):
            self.login("mala")

        # Ni con la contraseña correcta entra mientras dura el bloqueo
        response = self.login("clave-correcta-123")
        self.assertFalse(response.context["user"].is_authenticated)
        messages = [str(message) for message in response.context["messages"]]
        self.assertTrue(any("Demasiados intentos" in message for message in messages), messages)


class DashboardPaginationTests(TestCase):

    def setUp(self):
        cache.clear()
        for index in range(30):
            CatalogItem.objects.create(name=f"PROD-{index:02d}", category="accionamiento")
        user = get_user_model().objects.create_user("marcos", password="x")
        user.user_permissions.add(Permission.objects.get(codename="view_catalogitem"))
        user.user_permissions.add(Permission.objects.get(codename="view_vibrationmeasurement"))
        self.client.force_login(user)

    def test_products_are_paginated_and_keep_filters(self):
        first = self.client.get(reverse("productos_dashboard"), {"q": "PROD"})
        self.assertEqual(len(first.context["page_obj"].object_list), 25)
        self.assertContains(first, "q=PROD&amp;page=2")

        second = self.client.get(reverse("productos_dashboard"), {"q": "PROD", "page": 2})
        self.assertEqual(len(second.context["page_obj"].object_list), 5)

    def test_measurements_dashboard_loads(self):
        response = self.client.get(reverse("measurements_dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "0")


class MeasurementPdfTests(TestCase):

    def setUp(self):
        cache.clear()
        times = np.arange(600) / 60.0
        self.samples = [
            {"t": t * 1000.0, "x": 0.0, "y": 0.0, "z": float(np.sin(2 * np.pi * 14.4 * t))}
            for t in times
        ]

    def post_pdf(self, token):
        return self.client.post(
            reverse("measurement-pdf"),
            data={"samples": self.samples, "measurement_token": token},
            content_type="application/json",
        )

    def test_same_token_returns_same_pdf(self):
        token = "6a0f0a3e-3b1e-4c55-9d5a-2f1b9c7e4d10"
        first = self.post_pdf(token)
        second = self.post_pdf(token)

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first["X-SMAV-Folio"], second["X-SMAV-Folio"])

    def test_pdf_rate_limit(self):
        original = vibration_views.PDF_RATE_LIMIT
        vibration_views.PDF_RATE_LIMIT = 2
        try:
            self.assertEqual(self.post_pdf("11111111-1111-4111-8111-111111111111").status_code, 200)
            self.assertEqual(self.post_pdf("22222222-2222-4222-8222-222222222222").status_code, 200)
            self.assertEqual(self.post_pdf("33333333-3333-4333-8333-333333333333").status_code, 429)
        finally:
            vibration_views.PDF_RATE_LIMIT = original
