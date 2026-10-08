# A&P SENAC — React + FastAPI

Protótipo front-end + back-end para o sistema de Achados & Perdidos.

## Estrutura

- `frontend/` -> React + Vite
- `backend/` -> Python + FastAPI

## O que já funciona

### Consumidor
- Formulário de objeto perdido.
- Envio para FastAPI.
- Dados mantidos temporariamente em memória.

### SENAC
- Cadastro de objeto encontrado.
- Listagem de objetos encontrados.
- Área de matching.

### Matching
Existe uma primeira versão por regras:
- categoria: 30 pontos
- marca: 20
- cor: 15
- modelo: 20
- descrição: 15

Isso é apenas um protótipo. A futura IA pode substituir essa função por NLP/embeddings.

## Rodar o back-end

Entre em `backend`:

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

Linux/macOS:

```bash
source .venv/bin/activate
```

Depois:

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

API:
`http://127.0.0.1:8000`

Docs:
`http://127.0.0.1:8000/docs`

## Rodar o React

Em outro terminal:

```bash
cd frontend
npm install
npm run dev
```

Abra a URL mostrada pelo Vite, normalmente:

`http://localhost:5173`

## Próximas etapas

1. PostgreSQL.
2. Autenticação aluno/funcionário.
3. Área administrativa protegida.
4. Fotos.
5. Status e histórico.
6. Matches persistentes.
7. Aprovação humana.
8. E-mail.
9. NLP/embeddings.
10. Deploy.
