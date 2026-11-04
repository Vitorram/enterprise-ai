# EnterpriseAI

O EnterpriseAI é uma plataforma de inteligência artificial empresarial que transforma dados de diferentes empresas em informações estratégicas. A proposta inclui processamento de planilhas, análise de indicadores financeiros e operacionais, identificação de padrões e anomalias e geração de previsões com modelos próprios de Machine Learning treinados do zero. A plataforma também prevê dashboards interativos, autenticação segura e arquitetura multiempresa para apoiar a tomada de decisões baseada em dados.

## Estado atual

Esta versão contém a API inicial, com autenticação JWT e recursos para gerenciamento de usuários, organizações e associações. O processamento e a análise de planilhas, os modelos de Machine Learning e os dashboards fazem parte da visão do projeto e ainda não estão descritos aqui como funcionalidades disponíveis.

## Tecnologias

- Python e FastAPI
- SQLAlchemy
- MySQL

## Requisitos para executar a API

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

No Windows, ative com `.venv\Scripts\activate`; no Linux/macOS, use `source .venv/bin/activate`.

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
