# Database/Session.py

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config import settings


try:
    engine = create_engine(
        settings.DATABASE_URL,
        pool_size=20,          # Увеличен до 20
        max_overflow=40,       # Увеличен до 40 (общий лимит 60)
        pool_timeout=60        # Увеличен до 60 секунд
    )
except Exception as e:
    print(f"❌ Ошибка при создании engine для SQLAlchemy: {e}")
    exit()


SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

print("✅ Инициализация подключения к БД (engine и SessionLocal) прошла успешно.")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
