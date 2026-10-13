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

