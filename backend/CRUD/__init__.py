import sqlalchemy
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError


DATABASE_URL = "postgresql://postgres@localhost:5432/PAS"


try:
    engine = create_engine(DATABASE_URL)
    with engine.connect() as connection:
        print("✅ Соединение с базой данных PostgreSQL установлено успешно!")
        result = connection.execute(sqlalchemy.text("SELECT version()"))
        db_version = result.scalar()
        print(f"   Версия сервера: {db_version}")
except OperationalError as e:
    print("❌ Ошибка подключения к базе данных!")
    print(f"   Детали ошибки: {e}")

except Exception as e:
    print(f"❌ Произошла непредвиденная ошибка: {e}")
