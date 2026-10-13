"""API do sistema Achados & Perdidos SENAC.

Versão acadêmica funcional: SQLite persistente, interface pública,
área administrativa autenticada e matching por regras explicáveis.
Para produção, configurar credenciais, HTTPS, política de privacidade,
armazenamento seguro de imagens e revisão de segurança.
"""
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import hashlib
import hmac
import os
import secrets
import smtplib
import sqlite3
import ssl
from email.message import EmailMessage

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.getenv("AP_DB_PATH", BASE_DIR / "achados_perdidos.db"))
app = FastAPI(title="Achados & Perdidos SENAC API", version="2.0.0")

# Permite que o React local converse com a API durante o desenvolvimento.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# Sessões temporárias de demonstração: ao reiniciar o backend, é necessário entrar de novo.
SESSIONS: dict[str, dict] = {}
SESSION_HOURS = 8


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def connect_db():
    """Abre uma conexão SQLite; o arquivo permanece salvo após reiniciar a API."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def hash_password(password: str, salt: Optional[bytes] = None) -> tuple[str, str]:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 240_000)
    return salt.hex(), digest.hex()


def verify_password(password: str, salt_hex: str, expected_hash: str) -> bool:
    _, actual = hash_password(password, bytes.fromhex(salt_hex))
    return hmac.compare_digest(actual, expected_hash)


def init_db():
    """Cria as tabelas e um usuário de demonstração apenas se ainda não existir."""
    with connect_db() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS staff (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            salt TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS lost_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            protocol TEXT NOT NULL UNIQUE,
            user_name TEXT NOT NULL,
            user_email TEXT NOT NULL,
            item_name TEXT NOT NULL,
            category TEXT NOT NULL,
            brand TEXT DEFAULT '', model TEXT DEFAULT '', color TEXT DEFAULT '',
            lost_date TEXT DEFAULT '', lost_time TEXT DEFAULT '',
            lost_location TEXT DEFAULT '', building TEXT DEFAULT '', room TEXT DEFAULT '',
            description TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Aguardando análise',
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS found_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            protocol TEXT NOT NULL UNIQUE,
            item_name TEXT NOT NULL,
            category TEXT NOT NULL,
            brand TEXT DEFAULT '', model TEXT DEFAULT '', color TEXT DEFAULT '',
            found_date TEXT DEFAULT '', found_time TEXT DEFAULT '',
            found_location TEXT DEFAULT '', building TEXT DEFAULT '', room TEXT DEFAULT '',
            description TEXT DEFAULT '', storage_location TEXT DEFAULT '',
            received_by TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Guardado',
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lost_id INTEGER NOT NULL REFERENCES lost_items(id),
            found_id INTEGER NOT NULL REFERENCES found_items(id),
            score INTEGER NOT NULL,
            reasons TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Pendente de revisão',
            created_at TEXT NOT NULL,
            UNIQUE(lost_id, found_id)
        );
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            staff_email TEXT NOT NULL,
            action TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id INTEGER NOT NULL,
            details TEXT DEFAULT '',
            created_at TEXT NOT NULL
        );
        """)
        demo_email = os.getenv("AP_ADMIN_EMAIL", "apoio@senac.com.br").strip().lower()
        demo_password = os.getenv("AP_ADMIN_PASSWORD", "Apoio@12345")
        existing = db.execute("SELECT id FROM staff WHERE email = ?", (demo_email,)).fetchone()
        if not existing:
            salt, pwd_hash = hash_password(demo_password)
            db.execute(
                "INSERT INTO staff(name,email,salt,password_hash,created_at) VALUES(?,?,?,?,?)",
                ("Equipe de Apoio", demo_email, salt, pwd_hash, now_iso()),
            )


@app.on_event("startup")
def startup():
    init_db()


# Modelos validam os dados recebidos pela API antes de gravar no banco.
class LostItemIn(BaseModel):
    nome_usuario: str = Field(min_length=2, max_length=120)
    email_usuario: EmailStr
    nome_objeto: str = Field(min_length=2, max_length=120)
    categoria: str = Field(min_length=2, max_length=60)
    marca: str = Field(default="", max_length=80)
    modelo: str = Field(default="", max_length=100)
    cor: str = Field(default="", max_length=60)
    data_perda: str = ""
    horario_perda: str = ""
    local_perda: str = ""
    predio: str = ""
    sala: str = ""
    descricao: str = Field(min_length=3, max_length=2000)


class FoundItemIn(BaseModel):
    nome_objeto: str = Field(min_length=2, max_length=120)
    categoria: str = Field(min_length=2, max_length=60)
    marca: str = Field(default="", max_length=80)
    modelo: str = Field(default="", max_length=100)
    cor: str = Field(default="", max_length=60)
    data_encontrado: str = ""
    horario_encontrado: str = ""
    local_encontrado: str = ""
    predio: str = ""
    sala: str = ""
    descricao: str = Field(default="", max_length=2000)
    local_armazenamento: str = Field(default="", max_length=160)


class LoginIn(BaseModel):
    email: EmailStr
    senha: str = Field(min_length=1, max_length=200)


class ReviewIn(BaseModel):
    decisao: str
    observacao: str = ""


class ReturnIn(BaseModel):
    responsavel_retirada: str = Field(min_length=2, max_length=120)
    observacao: str = ""


def normalize(value) -> str:
    return " ".join(str(value or "").strip().lower().split())


def score_match(lost: dict, found: dict) -> tuple[int, list[str]]:
    """Calcula uma pontuação explicável (não é IA generativa)."""
    score, reasons = 0, []
    rules = [
        ("category", 25, "mesma categoria"),
        ("brand", 15, "mesma marca"),
        ("model", 20, "mesmo modelo"),
        ("color", 15, "mesma cor"),
        ("item_name", 10, "nome do objeto semelhante"),
    ]
    for key, points, reason in rules:
        a, b = normalize(lost.get(key)), normalize(found.get(key))
        if a and b and (a == b or (key == "item_name" and (a in b or b in a))):
            score += points
            reasons.append(reason)
    lost_desc = set(normalize(lost.get("description")).split())
    found_desc = set(normalize(found.get("description")).split())
    common = {w for w in lost_desc & found_desc if len(w) >= 4}
    if common:
        score += min(15, 5 + 2 * len(common))
        reasons.append("palavras em comum na descrição: " + ", ".join(sorted(list(common)[:5])))
    lost_loc = normalize(" ".join([lost.get("lost_location", ""), lost.get("building", ""), lost.get("room", "")]))
    found_loc = normalize(" ".join([found.get("found_location", ""), found.get("building", ""), found.get("room", "")]))
    if lost_loc and found_loc and any(part in found_loc for part in lost_loc.split() if len(part) >= 4):
        score += 10
        reasons.append("localização semelhante")
    return min(score, 100), reasons


def create_matches_for_lost(db, lost_id: int):
    lost = dict(db.execute("SELECT * FROM lost_items WHERE id=?", (lost_id,)).fetchone())
    found_rows = db.execute("SELECT * FROM found_items WHERE status != 'Devolvido' ORDER BY id DESC").fetchall()
    for row in found_rows:
        found = dict(row)
        score, reasons = score_match(lost, found)
        if score >= 35:
            db.execute(
                "INSERT OR IGNORE INTO matches(lost_id,found_id,score,reasons,created_at) VALUES(?,?,?,?,?)",
                (lost_id, found["id"], score, "; ".join(reasons) or "Dados semelhantes", now_iso()),
            )


def create_matches_for_found(db, found_id: int):
    lost_rows = db.execute("SELECT * FROM lost_items WHERE status != 'Encerrada' ORDER BY id DESC").fetchall()
    found = dict(db.execute("SELECT * FROM found_items WHERE id=?", (found_id,)).fetchone())
    for row in lost_rows:
        lost = dict(row)
        score, reasons = score_match(lost, found)
        if score >= 35:
            db.execute(
                "INSERT OR IGNORE INTO matches(lost_id,found_id,score,reasons,created_at) VALUES(?,?,?,?,?)",
                (lost["id"], found_id, score, "; ".join(reasons) or "Dados semelhantes", now_iso()),
            )


def send_match_email(email: str, lost_protocol: str, found_protocol: str):
    """Envia e-mail se SMTP estiver configurado; sem configuração, não bloqueia o fluxo."""
    host = os.getenv("AP_SMTP_HOST")
    user = os.getenv("AP_SMTP_USER")
    password = os.getenv("AP_SMTP_PASSWORD")
    sender = os.getenv("AP_SMTP_FROM", user or "")
    if not (host and user and password and sender):
        return False
    msg = EmailMessage()
    msg["Subject"] = "Possível correspondência — Achados & Perdidos SENAC"
    msg["From"] = sender
    msg["To"] = email
    msg.set_content(
        f"Olá! O sistema identificou um possível objeto relacionado à ocorrência {lost_protocol}. "
        f"A equipe de apoio fará a validação. Não vá retirar o objeto antes de receber as instruções do SENAC. "
        f"Referência interna: {found_protocol}."
    )
    with smtplib.SMTP(host, int(os.getenv("AP_SMTP_PORT", "587")), timeout=10) as server:
        server.starttls(context=ssl.create_default_context())
        server.login(user, password)
        server.send_message(msg)
    return True


def require_staff(authorization: Optional[str] = Header(default=None)) -> dict:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Faça login na área de apoio.")
    token = authorization.split(" ", 1)[1].strip()
    session = SESSIONS.get(token)
    if not session or session["expires_at"] < datetime.now():
        SESSIONS.pop(token, None)
        raise HTTPException(status_code=401, detail="Sessão expirada. Entre novamente.")
    return session


def record_history(db, staff: dict, action: str, entity_type: str, entity_id: int, details: str = ""):
    db.execute(
        "INSERT INTO history(staff_email,action,entity_type,entity_id,details,created_at) VALUES(?,?,?,?,?,?)",
        (staff["email"], action, entity_type, entity_id, details, now_iso()),
    )


@app.get("/")
def root():
    return {"app": "Achados & Perdidos SENAC", "status": "online", "docs": "/docs"}


@app.post("/api/auth/login")
def login(payload: LoginIn):
    with connect_db() as db:
        row = db.execute("SELECT * FROM staff WHERE email=? AND active=1", (str(payload.email).lower(),)).fetchone()
    if not row or not verify_password(payload.senha, row["salt"], row["password_hash"]):
        raise HTTPException(status_code=401, detail="E-mail ou senha inválidos.")
    token = secrets.token_urlsafe(32)
    SESSIONS[token] = {"email": row["email"], "name": row["name"], "expires_at": datetime.now() + timedelta(hours=SESSION_HOURS)}
    return {"access_token": token, "token_type": "bearer", "nome": row["name"], "email": row["email"], "expires_in_hours": SESSION_HOURS}


@app.get("/api/auth/me")
def me(staff: dict = Depends(require_staff)):
    return {"nome": staff["name"], "email": staff["email"]}


@app.post("/api/auth/logout")
def logout(authorization: Optional[str] = Header(default=None), staff: dict = Depends(require_staff)):
    token = authorization.split(" ", 1)[1].strip()
    SESSIONS.pop(token, None)
    return {"message": "Sessão encerrada."}


@app.post("/api/objetos-perdidos", status_code=201)
def register_lost(payload: LostItemIn):
    protocol = "PER-" + secrets.token_hex(4).upper()
    with connect_db() as db:
        cur = db.execute("""INSERT INTO lost_items
            (protocol,user_name,user_email,item_name,category,brand,model,color,lost_date,lost_time,lost_location,building,room,description,created_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (protocol, payload.nome_usuario, str(payload.email_usuario).lower(), payload.nome_objeto, payload.categoria,
             payload.marca, payload.modelo, payload.cor, payload.data_perda, payload.horario_perda,
             payload.local_perda, payload.predio, payload.sala, payload.descricao, now_iso()))
        create_matches_for_lost(db, cur.lastrowid)
    return {"message": "Ocorrência registrada.", "protocolo": protocol, "status": "Aguardando análise"}


@app.get("/api/acompanhar/{protocol}")
def track_lost(protocol: str, email: EmailStr = Query(...)):
    with connect_db() as db:
        row = db.execute("SELECT protocol,user_email,item_name,category,status,created_at FROM lost_items WHERE protocol=? AND user_email=?", (protocol.upper(), str(email).lower())).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Não encontramos uma ocorrência com esse protocolo e e-mail.")
        matches = db.execute("SELECT m.score,m.status,f.protocol FROM matches m JOIN found_items f ON f.id=m.found_id WHERE m.lost_id=(SELECT id FROM lost_items WHERE protocol=?) AND m.status='Aprovada' ORDER BY m.score DESC", (protocol.upper(),)).fetchall()
    return {**dict(row), "possui_correspondencia_validada": bool(matches), "instrucoes": "Aguarde o contato da equipe de apoio." if matches else "Ainda não há correspondência validada."}


@app.get("/api/encontrados-publicos")
def public_found():
    # A lista pública não expõe descrição completa, responsável ou localização de armazenamento.
    with connect_db() as db:
        rows = db.execute("SELECT protocol,item_name,category,brand,color,found_date,found_location,building,status FROM found_items WHERE status='Guardado' ORDER BY id DESC").fetchall()
    return [dict(row) for row in rows]


@app.get("/api/apoio/dashboard")
def dashboard(staff: dict = Depends(require_staff)):
    with connect_db() as db:
        counts = {
            "perdidos": db.execute("SELECT COUNT(*) FROM lost_items WHERE status != 'Encerrada'").fetchone()[0],
            "encontrados": db.execute("SELECT COUNT(*) FROM found_items WHERE status != 'Devolvido'").fetchone()[0],
            "matches_pendentes": db.execute("SELECT COUNT(*) FROM matches WHERE status='Pendente de revisão'").fetchone()[0],
            "devolvidos": db.execute("SELECT COUNT(*) FROM found_items WHERE status='Devolvido'").fetchone()[0],
        }
        recent = db.execute("SELECT protocol,item_name,category,status,created_at FROM found_items ORDER BY id DESC LIMIT 5").fetchall()
    return {**counts, "recentes": [dict(r) for r in recent]}


@app.get("/api/apoio/objetos-perdidos")
def staff_lost(staff: dict = Depends(require_staff)):
    with connect_db() as db:
        rows = db.execute("SELECT * FROM lost_items ORDER BY id DESC").fetchall()
    return [dict(r) for r in rows]


@app.get("/api/apoio/objetos-encontrados")
def staff_found(staff: dict = Depends(require_staff)):
    with connect_db() as db:
        rows = db.execute("SELECT * FROM found_items ORDER BY id DESC").fetchall()
    return [dict(r) for r in rows]


@app.post("/api/apoio/objetos-encontrados", status_code=201)
def register_found(payload: FoundItemIn, staff: dict = Depends(require_staff)):
    protocol = "ENC-" + secrets.token_hex(4).upper()
    with connect_db() as db:
        cur = db.execute("""INSERT INTO found_items
            (protocol,item_name,category,brand,model,color,found_date,found_time,found_location,building,room,description,storage_location,received_by,created_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (protocol,payload.nome_objeto,payload.categoria,payload.marca,payload.modelo,payload.cor,payload.data_encontrado,
             payload.horario_encontrado,payload.local_encontrado,payload.predio,payload.sala,payload.descricao,
             payload.local_armazenamento,staff["name"],now_iso()))
        create_matches_for_found(db, cur.lastrowid)
        record_history(db, staff, "Cadastro de objeto encontrado", "found_item", cur.lastrowid, protocol)
    return {"message": "Objeto encontrado cadastrado e comparação executada.", "protocolo": protocol}


@app.get("/api/apoio/matches")
def list_matches(staff: dict = Depends(require_staff)):
    with connect_db() as db:
        rows = db.execute("""SELECT m.id,m.score,m.reasons,m.status,m.created_at,
            l.protocol AS protocolo_perdido,l.user_name,l.user_email,l.item_name AS objeto_perdido,l.category AS categoria_perdida,
            l.brand AS marca_perdida,l.model AS modelo_perdido,l.color AS cor_perdida,l.description AS descricao_perdida,
            f.protocol AS protocolo_encontrado,f.item_name AS objeto_encontrado,f.category AS categoria_encontrada,
            f.brand AS marca_encontrada,f.model AS modelo_encontrado,f.color AS cor_encontrada,f.description AS descricao_encontrada,
            f.storage_location FROM matches m JOIN lost_items l ON l.id=m.lost_id JOIN found_items f ON f.id=m.found_id
            ORDER BY CASE m.status WHEN 'Pendente de revisão' THEN 0 ELSE 1 END, m.score DESC""").fetchall()
    return [dict(r) for r in rows]


@app.post("/api/apoio/matches/{match_id}/revisar")
def review_match(match_id: int, payload: ReviewIn, staff: dict = Depends(require_staff)):
    if payload.decisao not in {"Aprovada", "Rejeitada"}:
        raise HTTPException(status_code=400, detail="Decisão deve ser Aprovada ou Rejeitada.")
    with connect_db() as db:
        row = db.execute("SELECT m.*,l.protocol AS lost_protocol,l.user_email,f.protocol AS found_protocol FROM matches m JOIN lost_items l ON l.id=m.lost_id JOIN found_items f ON f.id=m.found_id WHERE m.id=?", (match_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Correspondência não encontrada.")
        db.execute("UPDATE matches SET status=? WHERE id=?", (payload.decisao, match_id))
        record_history(db, staff, "Revisão de correspondência", "match", match_id, f"{payload.decisao}: {payload.observacao}")
        email_sent = False
        if payload.decisao == "Aprovada":
            db.execute("UPDATE lost_items SET status='Possível correspondência validada' WHERE id=?", (row["lost_id"],))
            try:
                email_sent = send_match_email(row["user_email"], row["lost_protocol"], row["found_protocol"])
            except Exception as exc:
                # Erro de e-mail é registrado, mas não desfaz a decisão administrativa.
                record_history(db, staff, "Falha no envio de e-mail", "match", match_id, str(exc)[:300])
    return {"message": "Revisão registrada.", "status": payload.decisao, "email_enviado": email_sent, "email_configurado": bool(os.getenv("AP_SMTP_HOST"))}


@app.post("/api/apoio/devolucoes/{found_id}")
def return_found(found_id: int, payload: ReturnIn, staff: dict = Depends(require_staff)):
    with connect_db() as db:
        row = db.execute("SELECT * FROM found_items WHERE id=?", (found_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Objeto não encontrado.")
        if row["status"] == "Devolvido":
            raise HTTPException(status_code=409, detail="Este objeto já foi marcado como devolvido.")
        db.execute("UPDATE found_items SET status='Devolvido' WHERE id=?", (found_id,))
        record_history(db, staff, "Objeto devolvido", "found_item", found_id, f"Retirado por: {payload.responsavel_retirada}. {payload.observacao}")
    return {"message": "Devolução registrada."}


@app.get("/api/apoio/historico")
def staff_history(staff: dict = Depends(require_staff)):
    with connect_db() as db:
        rows = db.execute("SELECT * FROM history ORDER BY id DESC LIMIT 100").fetchall()
    return [dict(r) for r in rows]
