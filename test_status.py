#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests unitaires pour l'endpoint /status de l'application Flask.
"""

import pytest

from app import app


@pytest.fixture
def client():
    """
    Fixture pytest qui fournit un client de test Flask.

    Returns:
        FlaskClient: Client de test pour l'application Flask.
    """
    with app.test_client() as client:
        yield client


def test_status_endpoint_ok(client):
    """
    Test de l'endpoint GET /status.

    Vérifie que l'endpoint retourne:
    - Code HTTP 200
    - Content-Type JSON
    - Payload JSON {"status": "ok"}

    Args:
        client: Client de test Flask fourni par la fixture.
    """
    # Appel de l'endpoint
    resp = client.get("/status")

    # Vérification du code de statut
    assert resp.status_code == 200

    # Vérification du Content-Type JSON
    assert resp.is_json is True

    # Vérification du payload JSON
    assert resp.get_json() == {"status": "ok"}
