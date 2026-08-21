"""
banco.py — Conexão com o SQLite, criação do esquema e carga inicial.

O banco é um arquivo único (`backend/etrilha.db`), sem servidor de banco
separado. É a escolha certa para o porte do projeto: o SQLite roda em processo,
não precisa de instalação nem de configuração, e ainda assim oferece
transações ACID, chaves estrangeiras e gatilhos de verdade — que é o que
garante que o histórico de eventos não seja reescrito.
"""

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

import modelo

PASTA_BACKEND = Path(__file__).resolve().parent
RAIZ = PASTA_BACKEND.parent
CAMINHO_BANCO = PASTA_BACKEND / "etrilha.db"
CAMINHO_SCHEMA = PASTA_BACKEND / "schema.sql"
PASTA_DADOS = RAIZ / "dados"


def agora_iso() -> str:
    """Data e hora em UTC, no formato ISO 8601 — o mesmo que o JavaScript usa."""
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def conectar() -> sqlite3.Connection:
    # isolation_level=None desliga o gerenciamento automático de transações do
    # Python: quem decide onde a transação começa e termina é este módulo, com
    # BEGIN/COMMIT explícitos. Isso é necessário porque as escritas precisam de
    # BEGIN IMMEDIATE (ver `transacao`), que o modo automático não permite.
    conexao = sqlite3.connect(CAMINHO_BANCO, timeout=10, isolation_level=None)
    conexao.row_factory = sqlite3.Row
    # Chaves estrangeiras vêm desligadas por padrão no SQLite e precisam ser
    # ligadas em cada conexão.
    conexao.execute("PRAGMA foreign_keys = ON")
    # WAL permite leituras simultâneas às escritas: vários operadores podem
    # consultar enquanto um registra uma leitura de QR.
    conexao.execute("PRAGMA journal_mode = WAL")
    return conexao


@contextmanager
def transacao(conexao):
    """
    Transação de escrita, com BEGIN IMMEDIATE.

    IMMEDIATE toma o bloqueio de escrita já na abertura, e não no primeiro
    INSERT. Isso importa porque as escritas aqui são do tipo "ler, decidir,
    gravar": sem o bloqueio antecipado, dois operadores lendo o mesmo QR ao
    mesmo tempo poderiam ambos ver "COLETADO" e gravar "EM_TRIAGEM" duas vezes.
    """
    conexao.execute("BEGIN IMMEDIATE")
    try:
        yield conexao
    except Exception:
        conexao.execute("ROLLBACK")
        raise
    else:
        conexao.execute("COMMIT")


def novo_id(prefixo: str) -> str:
    return f"{prefixo}-{uuid.uuid4().hex[:12]}"


# --------------------------------------------------------------------------- #
# Criação e carga inicial
# --------------------------------------------------------------------------- #

def _tabelas_existem(conexao) -> bool:
    linha = conexao.execute(
        "SELECT COUNT(*) AS n FROM sqlite_master WHERE type='table' AND name='itens'"
    ).fetchone()
    return linha["n"] > 0


def preparar(recriar: bool = False) -> None:
    """
    Garante que o banco exista. Com `recriar=True`, apaga tudo e semeia de novo
    (é o que o botão "reiniciar demonstração" faz).

    A reinicialização derruba as tabelas em vez de apagar as linhas porque os
    gatilhos de somente-acréscimo proíbem DELETE em `eventos` — e DROP TABLE
    não dispara gatilhos.
    """
    conexao = conectar()
    try:
        if recriar:
            conexao.executescript(
                """
                PRAGMA foreign_keys = OFF;
                DROP TRIGGER IF EXISTS eventos_sem_update;
                DROP TRIGGER IF EXISTS eventos_sem_delete;
                DROP TABLE IF EXISTS eventos;
                DROP TABLE IF EXISTS itens;
                DROP TABLE IF EXISTS usuarios;
                DROP TABLE IF EXISTS pontos;
                """
            )

        if recriar or not _tabelas_existem(conexao):
            conexao.executescript(CAMINHO_SCHEMA.read_text(encoding="utf-8"))
            _semear(conexao)
    finally:
        conexao.close()


def _semear(conexao) -> None:
    """
    Carrega os pontos de coleta e os itens de demonstração a partir de
    `dados/*.json` — os mesmos arquivos, sem duplicar dados no código.

    As datas dos itens de exemplo são relativas ao momento da carga, para que o
    painel sempre mostre um histórico recente e coerente, com um item
    propositalmente atrasado.
    """
    pontos = json.loads((PASTA_DADOS / "pontos.json").read_text(encoding="utf-8"))
    itens = json.loads((PASTA_DADOS / "itens-demo.json").read_text(encoding="utf-8"))

    referencia = datetime.now(timezone.utc)

    def quando(horas_atras: float) -> str:
        instante = referencia - timedelta(hours=horas_atras)
        return instante.isoformat(timespec="milliseconds").replace("+00:00", "Z")

    with transacao(conexao):
        conexao.executemany(
            """INSERT INTO pontos (id, nome, tipo, municipio, endereco, lat, lng,
                                   aceita, horario, telefone)
               VALUES (:id, :nome, :tipo, :municipio, :endereco, :lat, :lng,
                       :aceita, :horario, :telefone)""",
            [{**p, "aceita": json.dumps(p["aceita"], ensure_ascii=False)} for p in pontos],
        )

        for item in itens:
            trilha = item["trilha"]
            conexao.execute(
                """INSERT INTO itens (codigo, categoria, marca, peso_kg, dono_id,
                                      visitante_id, ponto_origem_id, criado_em,
                                      atualizado_em, etapa_atual, demo)
                   VALUES (?, ?, ?, ?, NULL, NULL, ?, ?, ?, ?, 1)""",
                (
                    item["codigo"], item["categoria"], item["marca"], item["pesoKg"],
                    item["pontoOrigemId"], quando(trilha[0][1]), quando(trilha[-1][1]),
                    trilha[-1][0],
                ),
            )
            conexao.executemany(
                """INSERT INTO eventos (item_codigo, etapa, ponto_id, responsavel, observacao, em)
                   VALUES (?, ?, ?, ?, '', ?)""",
                [(item["codigo"], etapa, ponto, responsavel, quando(horas))
                 for etapa, horas, ponto, responsavel in trilha],
            )


# --------------------------------------------------------------------------- #
# Conversão entre as linhas do banco (snake_case) e o JSON da API (camelCase)
#
# O front-end já foi escrito com os nomes em camelCase; manter a conversão aqui
# evita mexer em todas as telas.
# --------------------------------------------------------------------------- #

def ponto_json(linha) -> dict:
    return {
        "id": linha["id"],
        "nome": linha["nome"],
        "tipo": linha["tipo"],
        "municipio": linha["municipio"],
        "endereco": linha["endereco"],
        "lat": linha["lat"],
        "lng": linha["lng"],
        "aceita": json.loads(linha["aceita"]),
        "horario": linha["horario"],
        "telefone": linha["telefone"],
    }


def item_json(linha) -> dict:
    return {
        "codigo": linha["codigo"],
        "categoria": linha["categoria"],
        "marca": linha["marca"],
        "pesoKg": linha["peso_kg"],
        "donoId": linha["dono_id"],
        "pontoOrigemId": linha["ponto_origem_id"],
        "criadoEm": linha["criado_em"],
        "atualizadoEm": linha["atualizado_em"],
        "etapaAtual": linha["etapa_atual"],
        "demo": bool(linha["demo"]),
    }


def evento_json(linha) -> dict:
    return {
        "id": linha["id"],
        "itemCodigo": linha["item_codigo"],
        "etapa": linha["etapa"],
        "pontoId": linha["ponto_id"],
        "responsavel": linha["responsavel"],
        "observacao": linha["observacao"],
        "em": linha["em"],
    }


# --------------------------------------------------------------------------- #
# Consultas
# --------------------------------------------------------------------------- #

def listar_pontos(conexao) -> list[dict]:
    linhas = conexao.execute("SELECT * FROM pontos ORDER BY municipio, nome").fetchall()
    return [ponto_json(l) for l in linhas]


def listar_itens(conexao) -> list[dict]:
    linhas = conexao.execute("SELECT * FROM itens ORDER BY atualizado_em DESC").fetchall()
    return [item_json(l) for l in linhas]


def listar_eventos(conexao) -> list[dict]:
    linhas = conexao.execute("SELECT * FROM eventos ORDER BY em").fetchall()
    return [evento_json(l) for l in linhas]


def obter_item(conexao, codigo: str) -> dict | None:
    linha = conexao.execute("SELECT * FROM itens WHERE codigo = ?", (codigo,)).fetchone()
    return item_json(linha) if linha else None


def obter_rastreio(conexao, codigo: str) -> dict | None:
    """Item + eventos ordenados, já com o ponto de coleta de cada evento resolvido."""
    item = obter_item(conexao, codigo)
    if item is None:
        return None

    linhas = conexao.execute(
        "SELECT * FROM eventos WHERE item_codigo = ? ORDER BY em, id", (codigo,)
    ).fetchall()
    pontos = {p["id"]: p for p in listar_pontos(conexao)}

    eventos = []
    for linha in linhas:
        evento = evento_json(linha)
        evento["ponto"] = pontos.get(evento["pontoId"])
        eventos.append(evento)

    return {"item": item, "eventos": eventos}


def itens_do_dono(conexao, usuario_id: str | None, visitante_id: str | None) -> list[dict]:
    """Itens de um usuário logado ou, na ausência de conta, do visitante atual."""
    if usuario_id:
        linhas = conexao.execute(
            "SELECT * FROM itens WHERE dono_id = ? ORDER BY atualizado_em DESC",
            (usuario_id,),
        ).fetchall()
    elif visitante_id:
        linhas = conexao.execute(
            """SELECT * FROM itens
               WHERE visitante_id = ? AND dono_id IS NULL
               ORDER BY atualizado_em DESC""",
            (visitante_id,),
        ).fetchall()
    else:
        return []
    return [item_json(l) for l in linhas]


# --------------------------------------------------------------------------- #
# Escritas
# --------------------------------------------------------------------------- #

def criar_item(conexao, *, categoria, marca, peso_kg, ponto_origem_id,
               responsavel, usuario_id, visitante_id) -> dict:
    """Cadastra o dispositivo e já grava o evento REGISTRADO, na mesma transação."""
    agora = agora_iso()

    with transacao(conexao):
        # Colisão de código é improvável (32^7), mas o laço torna impossível.
        for _ in range(10):
            codigo = modelo.gerar_codigo()
            existe = conexao.execute(
                "SELECT 1 FROM itens WHERE codigo = ?", (codigo,)
            ).fetchone()
            if not existe:
                break
        else:
            raise modelo.RegraViolada("Não foi possível gerar um código único.")

        conexao.execute(
            """INSERT INTO itens (codigo, categoria, marca, peso_kg, dono_id,
                                  visitante_id, ponto_origem_id, criado_em,
                                  atualizado_em, etapa_atual, demo)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)""",
            (codigo, categoria, marca, peso_kg, usuario_id,
             None if usuario_id else visitante_id, ponto_origem_id,
             agora, agora, modelo.PRIMEIRA_ETAPA),
        )
        conexao.execute(
            """INSERT INTO eventos (item_codigo, etapa, ponto_id, responsavel, observacao, em)
               VALUES (?, ?, ?, ?, '', ?)""",
            (codigo, modelo.PRIMEIRA_ETAPA, ponto_origem_id,
             responsavel or "Registro do próprio dono", agora),
        )

    return obter_item(conexao, codigo)


def registrar_evento(conexao, codigo, *, etapa, ponto_id, responsavel, observacao) -> dict:
    """
    Acrescenta um elo à cadeia de custódia. A validação da transição roda
    dentro da transação, sobre a etapa lida do banco — nunca sobre o que o
    cliente afirmou ser a etapa atual.
    """
    agora = agora_iso()

    with transacao(conexao):
        linha = conexao.execute(
            "SELECT etapa_atual FROM itens WHERE codigo = ?", (codigo,)
        ).fetchone()
        if linha is None:
            raise modelo.RegraViolada("Código de rastreio não encontrado.")

        # A validação acontece aqui, dentro da transação e do lado do servidor.
        modelo.validar_transicao(linha["etapa_atual"], etapa)

        cursor = conexao.execute(
            """INSERT INTO eventos (item_codigo, etapa, ponto_id, responsavel, observacao, em)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (codigo, etapa, ponto_id, responsavel or "Não informado", observacao, agora),
        )
        # `etapa_atual` é só um espelho do último evento, mantido para consulta
        # rápida. A verdade continua sendo a tabela de eventos.
        conexao.execute(
            "UPDATE itens SET etapa_atual = ?, atualizado_em = ? WHERE codigo = ?",
            (etapa, agora, codigo),
        )

    linha = conexao.execute("SELECT * FROM eventos WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return evento_json(linha)


def criar_usuario(conexao, *, nome: str, email: str, senha_hash: str) -> dict:
    usuario_id = novo_id("u")
    try:
        with transacao(conexao):
            conexao.execute(
                """INSERT INTO usuarios (id, nome, email, senha_hash, criado_em)
                   VALUES (?, ?, ?, ?, ?)""",
                (usuario_id, nome, email.lower(), senha_hash, agora_iso()),
            )
    except sqlite3.IntegrityError:
        # A restrição UNIQUE do e-mail é quem garante isso — verificar antes com
        # um SELECT deixaria uma janela para duas contas iguais serem criadas
        # ao mesmo tempo.
        raise modelo.RegraViolada("Já existe uma conta com esse e-mail.")
    return {"id": usuario_id, "nome": nome, "email": email.lower()}


def buscar_usuario_por_email(conexao, email: str):
    return conexao.execute(
        "SELECT * FROM usuarios WHERE email = ?", (str(email).strip().lower(),)
    ).fetchone()


def obter_usuario(conexao, usuario_id: str) -> dict | None:
    linha = conexao.execute(
        "SELECT id, nome, email FROM usuarios WHERE id = ?", (usuario_id,)
    ).fetchone()
    return dict(linha) if linha else None


def adotar_itens_do_visitante(conexao, usuario_id: str, visitante_id: str | None) -> int:
    """Vincula ao usuário os itens registrados neste navegador antes do cadastro."""
    if not visitante_id:
        return 0
    with transacao(conexao):
        cursor = conexao.execute(
            """UPDATE itens SET dono_id = ?, visitante_id = NULL
               WHERE visitante_id = ? AND dono_id IS NULL""",
            (usuario_id, visitante_id),
        )
    return cursor.rowcount
