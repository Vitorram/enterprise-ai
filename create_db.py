from backend.app.core.database import create_tables
from backend.app.models import Organization, User, Membership

create_tables()

print("Tabelas criadas com sucesso!")