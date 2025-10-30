from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config import settings


try:
    engine = create_engine(
        settings.DATABASE_URL,
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
