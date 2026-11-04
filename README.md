# EnterpriseAI

API para gerenciamento de usuários, organizações e associações, com autenticação JWT. Feita com FastAPI e SQLAlchemy.

## Requisitos

- Python 3.10+
- MySQL

## Configuração

Crie e ative um ambiente virtual, instale as dependências e configure as variáveis no arquivo `.env`:

```env
SECRET_KEY=sua-chave-secreta-com-pelo-menos-32-caracteres
ACCESS_TOKEN_EXPIRE_MINUTES=30
SQLALCHEMY_DATABASE_URL=mysql+pymysql://usuario:senha@localhost/nome_do_banco
```

```bash
python -m venv .venv
```

No Windows, ative com ` .venv\Scripts\activate`; no Linux/macOS, use `source .venv/bin/activate`.

```bash
pip install -r requirements.txt
```

## Executar

Na raiz do projeto, inicie a API:

```bash
uvicorn backend.app.main:app --reload
```

A documentação interativa fica em `http://127.0.0.1:8000/docs`.

## Testes

```bash
pytest
```
