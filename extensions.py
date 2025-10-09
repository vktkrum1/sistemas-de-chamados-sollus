# extensions.py
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_wtf import CSRFProtect

# Flask-Mail opcional
try:
    from flask_mail import Mail  # pacote presente? ok
except Exception:
    class Mail:                  # pacote ausente? dummy
        def init_app(self, app):
            pass

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()
mail = Mail()   # real ou dummy, conforme disponibilidade do pacote


login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'warning'
