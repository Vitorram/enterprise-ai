from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
import os

# Carrega as variáveis do arquivo .env
load_dotenv()

# Recupera a URL de conexão com o MySQL
DATABASE_URL = os.getenv("SQLALCHEMY_DATABASE_URL")
engine = create_engine(
    DATABASE_URL,
    echo=False
)
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)
Base = declarative_base()


def get_db():
    """Provide one database session per request and always close it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Função para criar as tabelas no banco de dados
def create_tables():
    Base.metadata.create_all(bind=engine)
