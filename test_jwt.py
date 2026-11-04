from backend.app.core.security import (
    create_access_token,
    decode_access_token
)

token = create_access_token({"sub": "1"})

adulterado = token[:-5] + "xxxxx"

try:
    decode_access_token(adulterado)
    print("ERRO: token aceito")
except ValueError:
    print("Token adulterado rejeitado corretamente")