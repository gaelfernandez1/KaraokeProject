#hai q meter certas configuracions de seguridade para o acceso publico
import os
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

def setup_security(app):
    
    limiter = Limiter(
        key_func=get_remote_address,
        app=app,
        default_limits=["1000 per hour"],
        storage_uri=os.getenv("REDIS_URL", "redis://redis:6379/0")
    )
    
    @limiter.limit("5 per minute")
    def limite_procesamiento():
        pass
    
    app.view_functions['xerar_karaoke'] = limiter.limit("3 per minute")(app.view_functions['xerar_karaoke'])
    app.view_functions['procesar_letras_manuales'] = limiter.limit("3 per minute")(app.view_functions['procesar_letras_manuales'])
    app.view_functions['xerar_instrumental'] = limiter.limit("5 per minute")(app.view_functions['xerar_instrumental'])
    
    # Excluir endpoints de consulta de estado del rate limiting
    limiter.exempt(app.view_functions['estado_tarea'])
    
    app.secret_key = os.getenv('FLASK_SECRET_KEY', 'karaoke_secret_key_change_in_production')
    
    @app.after_request
    def add_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        return response
    
    return limiter

def validate_file_size(file_size_mb, max_size_mb=100):
    return file_size_mb <= max_size_mb

def sanitize_filename(filename):
    import re
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    filename = filename[:255]
    return filename