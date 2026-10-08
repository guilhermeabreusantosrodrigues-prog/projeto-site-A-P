"""
A&P SENAC - Back-end demonstrativo
Python + FastAPI

Não existe banco de dados nesta versão.
Os registros ficam em memória apenas para demonstrar o fluxo
React -> FastAPI -> dados -> matching.
"""

from datetime import datetime
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(title="A&P SENAC API", version="1.0.0")

# Durante o desenvolvimento, o React (porta 5173) precisa
# poder conversar com a API (porta 8000).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ObjetoPerdido(BaseModel):
    nome_usuario: str
    email_usuario: str
    nome_objeto: str = Field(min_length=2)
    categoria: str
    marca: Optional[str] = None
    modelo: Optional[str] = None
    cor: Optional[str] = None
    data_perda: Optional[str] = None
    local_perda: Optional[str] = None
    descricao: str = Field(min_length=5)


class ObjetoEncontrado(BaseModel):
    nome_objeto: str = Field(min_length=2)
    categoria: str
    marca: Optional[str] = None
    modelo: Optional[str] = None
    cor: Optional[str] = None
    data_encontrado: Optional[str] = None
    local_encontrado: Optional[str] = None
    descricao: str = Field(min_length=5)


# Temporário: no banco real, estas listas serão tabelas PostgreSQL.
perdidos = []
encontrados = []


def normalizar(valor):
    """Padroniza texto para facilitar comparações."""
    return (valor or "").strip().lower()


def calcular_score(perdido, encontrado):
    """
    Matching inicial por regras.
    Não é IA ainda.

    Pesos:
    categoria = 30
    marca     = 20
    cor       = 15
    modelo    = 20
    descrição = 15
    """

    score = 0
    motivos = []

    if normalizar(perdido["categoria"]) == normalizar(encontrado["categoria"]):
        score += 30
        motivos.append("mesma categoria")

    if perdido.get("marca") and normalizar(perdido["marca"]) == normalizar(encontrado.get("marca")):
        score += 20
        motivos.append("mesma marca")

    if perdido.get("cor") and normalizar(perdido["cor"]) == normalizar(encontrado.get("cor")):
        score += 15
        motivos.append("mesma cor")

    if perdido.get("modelo") and normalizar(perdido["modelo"]) == normalizar(encontrado.get("modelo")):
        score += 20
        motivos.append("mesmo modelo")

    palavras_a = set(normalizar(perdido["descricao"]).split())
    palavras_b = set(normalizar(encontrado["descricao"]).split())

    if palavras_a.intersection(palavras_b):
        score += 15
        motivos.append("descrições possuem termos em comum")

    return min(score, 100), motivos


@app.get("/")
def health():
    return {"status": "online", "sistema": "A&P SENAC"}


@app.get("/api/objetos-perdidos")
def listar_perdidos():
    return perdidos


@app.get("/api/objetos-encontrados")
def listar_encontrados():
    return encontrados


@app.post("/api/objetos-perdidos")
def cadastrar_perdido(objeto: ObjetoPerdido):
    registro = objeto.model_dump()
    registro["id"] = len(perdidos) + 1
    registro["status"] = "procurando"
    registro["data_cadastro"] = datetime.now().isoformat()
    perdidos.append(registro)
    return {"mensagem": "Objeto perdido cadastrado.", "objeto": registro}


@app.post("/api/objetos-encontrados")
def cadastrar_encontrado(objeto: ObjetoEncontrado):
    registro = objeto.model_dump()
    registro["id"] = len(encontrados) + 1
    registro["status"] = "aguardando_dono"
    registro["data_cadastro"] = datetime.now().isoformat()
    encontrados.append(registro)
    return {"mensagem": "Objeto encontrado cadastrado.", "objeto": registro}


@app.get("/api/matches")
def matches():
    resultados = []

    for perdido in perdidos:
        for encontrado in encontrados:
            score, motivos = calcular_score(perdido, encontrado)

            if score >= 40:
                resultados.append({
                    "objeto_perdido_id": perdido["id"],
                    "objeto_encontrado_id": encontrado["id"],
                    "score": score,
                    "motivos": motivos,
                    "usuario": perdido["nome_usuario"],
                    "email": perdido["email_usuario"],
                    "perdido": perdido["nome_objeto"],
                    "encontrado": encontrado["nome_objeto"],
                })

    return sorted(resultados, key=lambda x: x["score"], reverse=True)
