from backend.app.core.security import hash_password, verify_password

password = "Empresa@123"

hashed = hash_password(password)

print("Senha original:", password)
print("Hash gerado:", hashed)

print("Senha correta:", verify_password("Empresa@123", hashed))
print("Senha incorreta:", verify_password("SenhaErrada", hashed))