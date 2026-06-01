import logging
from flask import Flask, jsonify, g

logger = logging.getLogger(__name__)


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(400)
    def bad_request(e):
        request_id = getattr(g, "request_id", "unknown")
        return jsonify({"error": "Bad request", "request_id": request_id}), 400

    @app.errorhandler(404)
    def not_found(e):
        request_id = getattr(g, "request_id", "unknown")
        return jsonify({"error": "Not found", "request_id": request_id}), 404

    @app.errorhandler(500)
    def internal_error(e):
        request_id = getattr(g, "request_id", "unknown")
        return jsonify({"error": "Internal error", "request_id": request_id}), 500

    @app.errorhandler(502)
    def bad_gateway(e):
        request_id = getattr(g, "request_id", "unknown")
        return jsonify({"error": "Bad gateway", "request_id": request_id}), 502
