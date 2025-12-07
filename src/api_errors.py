"""
Gestion standardisée des erreurs API - TASK-14
Format uniforme pour toutes les réponses d'erreur
"""

from datetime import datetime, timezone

from flask import jsonify, request


def error_response(message: str, code: int = 400, extra: dict = None):
    """
    Crée une réponse d'erreur standardisée

    Args:
        message: Message d'erreur lisible
        code: Code HTTP (400, 404, 429, 500, etc.)
        extra: Données supplémentaires optionnelles

    Returns:
        tuple: (response_json, status_code)
    """
    response = {
        "error": message,
        "code": code,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "path": request.path if request else "unknown",
    }

    if extra:
        response.update(extra)

    return jsonify(response), code


def bad_request(message: str = "Bad request"):
    """Erreur 400 - Requête invalide"""
    return error_response(message, 400)


def not_found(message: str = "Resource not found"):
    """Erreur 404 - Ressource introuvable"""
    return error_response(message, 404)


def rate_limit_exceeded(message: str = "Rate limit exceeded"):
    """Erreur 429 - Limite de taux dépassée"""
    return error_response(message, 429)


def internal_error(message: str = "Internal server error"):
    """Erreur 500 - Erreur serveur interne"""
    return error_response(message, 500)
