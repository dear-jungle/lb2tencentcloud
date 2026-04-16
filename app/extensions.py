"""Flask 扩展实例（避免循环导入）"""
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from app.models.base import Base

db = SQLAlchemy(model_class=Base)
migrate = Migrate()
