from example.storage.database import engine, Base
import example.storage.models

# Создание таблиц в базе данных
Base.metadata.create_all(bind=engine)

print("✅ База данных инициализирована")
