import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / '.env')

def _as_bool(val: str | None, default=False):
    if val is None:
        return default
    return str(val).strip().lower() in {'1', 'true', 'yes', 'on'}

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret')

    # DB
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL',
        'mysql+pymysql://root:121314@localhost:3306/chamados_ti'
    )
    SQLALCHEMY_ENGINE_OPTIONS = {'pool_pre_ping': True, 'pool_recycle': 280}
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    WTF_CSRF_ENABLED = True
    DEFAULT_PAGE_SIZE = int(os.getenv('DEFAULT_PAGE_SIZE', '10'))

    # Uploads
    UPLOADS_DIR = os.getenv('UPLOADS_DIR', str(BASE_DIR / 'uploads'))
    # O routes.py às vezes consulta MAX_CONTENT_MB, então deixamos ambos:
    MAX_CONTENT_MB = int(os.getenv('MAX_CONTENT_MB', '20'))
    MAX_CONTENT_LENGTH = MAX_CONTENT_MB * 1024 * 1024  # limite (bytes) do Flask

    # SLA targets (em horas)
    SLA_TARGETS_HOURS = {
        'low':    int(os.getenv('SLA_LOW_HOURS', '72')),
        'medium': int(os.getenv('SLA_MEDIUM_HOURS', '48')),
        'high':   int(os.getenv('SLA_HIGH_HOURS', '24')),
        'urgent': int(os.getenv('SLA_URGENT_HOURS', '4')),
    }

    # LDAP
    LDAP_ENABLED = _as_bool(os.getenv('LDAP_ENABLED', 'false'))
    LDAP_SERVER = os.getenv('LDAP_SERVER', 'ldap://localhost')
    LDAP_PORT = int(os.getenv('LDAP_PORT', '389'))
    LDAP_USE_SSL = _as_bool(os.getenv('LDAP_USE_SSL', 'false'))
    LDAP_BIND_DN = os.getenv('LDAP_BIND_DN', '')
    LDAP_BIND_PASSWORD = os.getenv('LDAP_BIND_PASSWORD', '')
    LDAP_BASE_DN = os.getenv('LDAP_BASE_DN', '')
    LDAP_USER_ATTR = os.getenv('LDAP_USER_ATTR', 'uid')
    LDAP_MAIL_ATTR = os.getenv('LDAP_MAIL_ATTR', 'mail')
    LDAP_DOMAIN_SUFFIX = os.getenv('LDAP_DOMAIN_SUFFIX', '')

    # --- E-mail (usado pelo mailer.py) ---
    # Se usar Office 365: SERVER=smtp.office365.com, PORT=587, TLS=1, SSL=0
    MAIL_ENABLED = _as_bool(os.getenv('MAIL_ENABLED', '1'))
    MAIL_SERVER = os.getenv('MAIL_SERVER', '')              # ex.: smtp.office365.com
    MAIL_PORT = int(os.getenv('MAIL_PORT', '0') or 0)       # ex.: 587
    MAIL_USE_TLS = _as_bool(os.getenv('MAIL_USE_TLS', '0')) # 1 para TLS
    MAIL_USE_SSL = _as_bool(os.getenv('MAIL_USE_SSL', '0')) # 1 para SSL (mutuamente exclusivo de TLS)
    MAIL_USERNAME = os.getenv('MAIL_USERNAME', '')          # ex.: ti@suaempresa.com
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD', '')          # senha ou app password
    MAIL_DEFAULT_SENDER = os.getenv(
        'MAIL_DEFAULT_SENDER',
        os.getenv('MAIL_USERNAME', '') or 'noreply@example.com'
    )
    # usado para montar links absolutos nos e-mails (visualizar chamado, etc.)
    MAIL_BASE_URL = os.getenv('MAIL_BASE_URL', '')          # ex.: http://192.168.0.26:5920


class DevConfig(Config):
    DEBUG = True


class ProdConfig(Config):
    DEBUG = False


CONFIG_MAP = {'development': DevConfig, 'production': ProdConfig}

def get_config():
    env = os.getenv('FLASK_ENV', 'development')
    return CONFIG_MAP.get(env, DevConfig)
