# example/init_db.py
from example.storage.database import engine, Base

# (далее – модуль models уже регистрируется через импорт)
import example.storage.models   # чтобы SQLAlchemy «видел» все описания таблиц

Base.metadata.create_all(bind=engine)
print("✅ База данных инициализирована")

