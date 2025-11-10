import os

from dotenv import load_dotenv
from flask import Flask
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail # 1. Importar Flask-Mail

from core.configuration.configuration import get_app_version
from core.managers.config_manager import ConfigManager
from core.managers.error_handler_manager import ErrorHandlerManager
from core.managers.logging_manager import LoggingManager
from core.managers.module_manager import ModuleManager

load_dotenv()

db = SQLAlchemy()
migrate = Migrate()
mail = Mail() # 2. Crear la instancia global de Mail


def create_app(config_name="development"):
    app = Flask(__name__)

    config_manager = ConfigManager(app)
    config_manager.load_config(config_name=config_name)

    db.init_app(app)
    migrate.init_app(app, db)
    
    # 3. Inicializar Flask-Mail con la app
    mail.init_app(app) 

    module_manager = ModuleManager(app)
    module_manager.register_modules()

    from flask_login import LoginManager

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    @login_manager.user_loader
    def load_user(user_id):
        from app.modules.auth.models import User

        return User.query.get(int(user_id))

    logging_manager = LoggingManager(app)
    logging_manager.setup_logging()

    error_handler_manager = ErrorHandlerManager(app)
    error_handler_manager.register_error_handlers()

    @app.context_processor
    def inject_vars_into_jinja():
        return {
            "FLASK_APP_NAME": os.getenv("FLASK_APP_NAME"),
            "FLASK_ENV": os.getenv("FLASK_ENV"),
            "DOMAIN": os.getenv("DOMAIN", "localhost"),
            "APP_VERSION": get_app_version(),
        }

    try:
        from app.modules.admin.routes import is_admin 

        @app.context_processor
        def inject_admin_status():
            return dict(is_admin=is_admin)
            
    except ImportError as e:
        app.logger.warning(f"Could not import is_admin: {e}. Injecting fallback.")
        @app.context_processor
        def inject_admin_status_fallback():
            return dict(is_admin=lambda: False)

    return app


app = create_app()