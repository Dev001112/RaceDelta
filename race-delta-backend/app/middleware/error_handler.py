# app/middleware/error_handler.py
"""
Centralized error handling middleware for consistent API error responses.
"""
from flask import jsonify, request
import traceback
import logging

logger = logging.getLogger(__name__)


def register_error_handlers(app):
    """
    Register error handlers for the Flask application.
    Provides consistent error response format across all routes.
    """
    
    @app.errorhandler(400)
    def bad_request(error):
        """Handle 400 Bad Request errors"""
        return jsonify({
            "error": "Bad Request",
            "message": str(error.description) if hasattr(error, 'description') else "Invalid request parameters",
            "status_code": 400
        }), 400
    
    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 Not Found errors"""
        return jsonify({
            "error": "Not Found",
            "message": str(error.description) if hasattr(error, 'description') else "Resource not found",
            "status_code": 404,
            "path": request.path
        }), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 Internal Server errors"""
        logger.error(f"Internal Server Error: {error}", exc_info=True)
        return jsonify({
            "error": "Internal Server Error",
            "message": "An unexpected error occurred",
            "status_code": 500
        }), 500
    
    @app.errorhandler(Exception)
    def handle_exception(error):
        """Handle all unhandled exceptions"""
        logger.error(f"Unhandled exception: {error}", exc_info=True)
        
        # In development, include traceback
        if app.config.get("DEBUG"):
            return jsonify({
                "error": type(error).__name__,
                "message": str(error),
                "status_code": 500,
                "traceback": traceback.format_exc()
            }), 500
        
        # In production, return generic error
        return jsonify({
            "error": "Internal Server Error",
            "message": "An unexpected error occurred",
            "status_code": 500
        }), 500

