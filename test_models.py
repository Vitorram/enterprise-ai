from backend.app.core.database import Base
from backend.app.models import Organization, User, Membership

print("Tabelas reconhecidas:")
print(Base.metadata.tables.keys())