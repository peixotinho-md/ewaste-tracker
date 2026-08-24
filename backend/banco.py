"""
banco.py — Conexão com o SQLite, criação do esquema e carga inicial.

O banco é um arquivo único (`backend/etrilha.db`), sem servidor de banco
separado. É a escolha certa para o porte do projeto: o SQLite roda em processo,
não precisa de instalação nem de configuração, e ainda assim oferece
transações ACID, chaves estrangeiras e gatilhos de verdade — que é o que
garante que o histórico de eventos não seja reescrito.
"""

import json
import re
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

from werkzeug.security import generate_password_hash

import modelo

PASTA_BACKEND = Path(__file__).resolve().parent
RAIZ = PASTA_BACKEND.parent
CAMINHO_BANCO = PASTA_BACKEND / "etrilha.db"
CAMINHO_SCHEMA = PASTA_BACKEND / "schema.sql"
PASTA_DADOS = RAIZ / "dados"

# Contas criadas junto com os dados de exemplo, para que a demonstração tenha
# de saída um administrador e um operador. São CREDENCIAIS PÚBLICAS, impressas
# no terminal ao subir o servidor: servem para a banca e para o grupo testarem,
# e num uso real seriam substituídas por um cadastro inicial fora da tela.
CONTAS_DEMO = [
    {
        "nome": "Administração e-Trilha MS",
        "email": "admin@etrilha.ms",
        "senha": "etrilha-admin",
        "papel": "admin",
        "ponto_id": None,
    },
    {
        "nome": "Operador do Ecoponto Região Norte",
        "email": "operador@etrilha.ms",
        "senha": "etrilha-operador",
        "papel": "operador",
        # Preenchido na carga com o primeiro ponto de coleta cadastrado.
        "ponto_id": None,
    },
]


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


def _versao_do_arquivo(conexao) -> int:
    return conexao.execute("PRAGMA user_version").fetchone()[0]


def _versao_do_schema() -> int:
    achado = re.search(r"PRAGMA user_version\s*=\s*(\d+)", CAMINHO_SCHEMA.read_text(encoding="utf-8"))
    return int(achado.group(1)) if achado else 1


def preparar(recriar: bool = False) -> None:
    """
    Garante que o banco exista e esteja na versão atual do esquema.

    Quando a versão gravada no arquivo é diferente da de `schema.sql`, o banco é
    recriado. Num sistema em produção isso seria uma migração; aqui os dados são
    de demonstração e vêm de `dados/*.json`, então recriar é mais simples e não
    corre o risco de deixar o banco num estado meio migrado.

    A reinicialização derruba as tabelas em vez de apagar as linhas porque os
    gatilhos de somente-acréscimo proíbem DELETE em `eventos` — e DROP TABLE
    não dispara gatilhos.
    """
    conexao = conectar()
    try:
        desatualizado = _tabelas_existem(conexao) and _versao_do_arquivo(conexao) != _versao_do_schema()
        if desatualizado:
            print("  Esquema do banco desatualizado: recriando com os dados de demonstração.")

        if recriar or desatualizado:
            conexao.executescript(
                """
                PRAGMA foreign_keys = OFF;
                DROP TRIGGER IF EXISTS eventos_sem_update;
                DROP TRIGGER IF EXISTS eventos_sem_delete;
                DROP TRIGGER IF EXISTS apagamentos_sem_update;
                DROP TRIGGER IF EXISTS apagamentos_sem_delete;
                DROP TRIGGER IF EXISTS alteracoes_sem_update;
                DROP TRIGGER IF EXISTS alteracoes_sem_delete;
                DROP TABLE IF EXISTS alteracoes_conta;
                DROP TABLE IF EXISTS apagamentos;
                DROP TABLE IF EXISTS eventos;
                DROP TABLE IF EXISTS itens;
                DROP TABLE IF EXISTS usuarios;
                DROP TABLE IF EXISTS pontos;
                """
            )

        if recriar or desatualizado or not _tabelas_existem(conexao):
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

            # O atestado de apagamento nasce na triagem; itens de exemplo que
            # ainda não chegaram lá não têm um.
            apagamento = item.get("apagamento")
            triagem = next((e for e in trilha if e[0] == "EM_TRIAGEM"), None)
            if apagamento and triagem:
                conexao.execute(
                    """INSERT INTO apagamentos (item_codigo, midia, metodo, responsavel, em)
                       VALUES (?, ?, ?, ?, ?)""",
                    (item["codigo"], apagamento["midia"], apagamento["metodo"],
                     triagem[3], quando(triagem[1])),
                )

        _semear_contas(conexao, pontos[0]["id"] if pontos else None)


def _semear_contas(conexao, ponto_do_operador: str | None) -> None:
    """
    Cria o administrador inicial e um operador de exemplo.

    O primeiro admin precisa nascer FORA da tela: como só um admin promove
    outro, não pode haver auto-promoção pela interface, ou o controle não valeria
    nada. Aqui esse papel é do carregamento de demonstração; num sistema real
    seria um comando de instalação executado por quem opera o servidor.

    Já está dentro da transação de `_semear`.
    """
    for conta in CONTAS_DEMO:
        conexao.execute(
            """INSERT INTO usuarios (id, nome, email, senha_hash, criado_em, papel, ponto_id)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                novo_id("u"),
                conta["nome"],
                conta["email"],
                generate_password_hash(conta["senha"]),
                agora_iso(),
                conta["papel"],
                ponto_do_operador if conta["papel"] == "operador" else conta["ponto_id"],
            ),
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


def usuario_json(linha) -> dict:
    """
    Usuário como a API o devolve.

    `senha_hash` NUNCA entra aqui. Nem para o admin: o hash não tem utilidade
    legítima na tela, e vazá-lo transformaria um XSS ou um log em material para
    ataque de dicionário offline.
    """
    return {
        "id": linha["id"],
        "nome": linha["nome"],
        "email": linha["email"],
        "papel": linha["papel"],
        "pontoId": linha["ponto_id"],
        "criadoEm": linha["criado_em"],
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

    return {"item": item, "eventos": eventos, "apagamento": obter_apagamento(conexao, codigo)}


def obter_apagamento(conexao, codigo: str) -> dict | None:
    linha = conexao.execute(
        "SELECT * FROM apagamentos WHERE item_codigo = ?", (codigo,)
    ).fetchone()
    if linha is None:
        return None
    return {
        "midia": linha["midia"],
        "metodo": linha["metodo"],
        "responsavel": linha["responsavel"],
        "em": linha["em"],
    }


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


def registrar_evento(conexao, codigo, *, etapa, ponto_id, responsavel, observacao,
                     apagamento=None) -> dict:
    """
    Acrescenta um elo à cadeia de custódia. A validação da transição roda
    dentro da transação, sobre a etapa lida do banco — nunca sobre o que o
    cliente afirmou ser a etapa atual.

    Ao concluir a triagem de um aparelho com mídia de dados, o atestado de
    apagamento é obrigatório e é gravado na mesma transação: ou o item avança
    com a declaração, ou não avança.
    """
    agora = agora_iso()

    with transacao(conexao):
        linha = conexao.execute(
            "SELECT etapa_atual, categoria FROM itens WHERE codigo = ?", (codigo,)
        ).fetchone()
        if linha is None:
            raise modelo.RegraViolada("Código de rastreio não encontrado.")

        # A validação acontece aqui, dentro da transação e do lado do servidor.
        modelo.validar_transicao(linha["etapa_atual"], etapa)

        if etapa == "EM_TRIAGEM":
            dados = apagamento or {}
            midia, metodo = modelo.validar_apagamento(
                linha["categoria"], dados.get("midia"), dados.get("metodo")
            )
            ja_existe = conexao.execute(
                "SELECT 1 FROM apagamentos WHERE item_codigo = ?", (codigo,)
            ).fetchone()
            if not ja_existe:
                conexao.execute(
                    """INSERT INTO apagamentos (item_codigo, midia, metodo, responsavel, em)
                       VALUES (?, ?, ?, ?, ?)""",
                    (codigo, midia, metodo, responsavel or "Não informado", agora),
                )

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
    """
    Cadastro feito pela própria pessoa. Nasce sempre como `visitante`: o papel
    é decisão de um admin, nunca do formulário — senão bastaria mandar
    `"papel": "admin"` no JSON para tomar o sistema.
    """
    usuario_id = novo_id("u")
    try:
        with transacao(conexao):
            conexao.execute(
                """INSERT INTO usuarios (id, nome, email, senha_hash, criado_em, papel)
                   VALUES (?, ?, ?, ?, ?, 'visitante')""",
                (usuario_id, nome, email.lower(), senha_hash, agora_iso()),
            )
    except sqlite3.IntegrityError:
        # A restrição UNIQUE do e-mail é quem garante isso — verificar antes com
        # um SELECT deixaria uma janela para duas contas iguais serem criadas
        # ao mesmo tempo.
        raise modelo.RegraViolada("Já existe uma conta com esse e-mail.")
    return obter_usuario(conexao, usuario_id)


def buscar_usuario_por_email(conexao, email: str):
    return conexao.execute(
        "SELECT * FROM usuarios WHERE email = ?", (str(email).strip().lower(),)
    ).fetchone()


def obter_usuario(conexao, usuario_id: str) -> dict | None:
    linha = conexao.execute(
        "SELECT * FROM usuarios WHERE id = ?", (usuario_id,)
    ).fetchone()
    return usuario_json(linha) if linha else None


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


# --------------------------------------------------------------------------- #
# Administração das contas
#
# Só um admin chega até aqui — quem verifica isso é `app.py`, antes de chamar
# estas funções. O que este módulo garante são as regras que não podem depender
# da tela: o sistema nunca fica sem administrador, e toda alteração deixa
# rastro.
# --------------------------------------------------------------------------- #

def listar_usuarios(conexao) -> list[dict]:
    linhas = conexao.execute(
        """SELECT * FROM usuarios
           ORDER BY CASE papel WHEN 'admin' THEN 0 WHEN 'operador' THEN 1 ELSE 2 END,
                    nome COLLATE NOCASE"""
    ).fetchall()
    return [usuario_json(l) for l in linhas]


def contar_itens_por_dono(conexao) -> dict[str, int]:
    """Quantos aparelhos cada conta já registrou — contexto útil na tela do admin."""
    linhas = conexao.execute(
        "SELECT dono_id, COUNT(*) AS n FROM itens WHERE dono_id IS NOT NULL GROUP BY dono_id"
    ).fetchall()
    return {l["dono_id"]: l["n"] for l in linhas}


def _registrar_alteracao(conexao, *, alvo_id, autor_id, acao, de="", para="") -> None:
    """Grava um elo na trilha de administração. Sempre dentro da transação da mudança."""
    conexao.execute(
        """INSERT INTO alteracoes_conta (alvo_id, autor_id, acao, de, para, em)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (alvo_id, autor_id, acao, de or "", para or "", agora_iso()),
    )


def listar_alteracoes(conexao, limite: int = 50) -> list[dict]:
    linhas = conexao.execute(
        """SELECT a.*, alvo.nome AS alvo_nome, autor.nome AS autor_nome
           FROM alteracoes_conta a
           JOIN usuarios alvo  ON alvo.id  = a.alvo_id
           JOIN usuarios autor ON autor.id = a.autor_id
           ORDER BY a.em DESC, a.id DESC
           LIMIT ?""",
        (limite,),
    ).fetchall()
    return [
        {
            "id": l["id"],
            "alvoNome": l["alvo_nome"],
            "autorNome": l["autor_nome"],
            "acao": l["acao"],
            "de": l["de"],
            "para": l["para"],
            "em": l["em"],
        }
        for l in linhas
    ]


def atualizar_usuario(conexao, alvo_id: str, *, autor_id: str, papel=None,
                      ponto_id=..., senha_hash=None) -> dict:
    """
    Aplica as mudanças que um admin pode fazer numa conta, todas na mesma
    transação e cada uma com seu registro na trilha.

    `ponto_id` usa `...` como "não mexer" porque `None` aqui é um valor legítimo:
    significa desvincular o operador do ponto.
    """
    with transacao(conexao):
        atual = conexao.execute(
            "SELECT * FROM usuarios WHERE id = ?", (alvo_id,)
        ).fetchone()
        if atual is None:
            raise modelo.RegraViolada("Conta não encontrada.")

        if papel is not None and papel != atual["papel"]:
            # Ler a contagem de admins DENTRO da transação é o que impede a
            # corrida clássica: dois admins se rebaixando ao mesmo tempo, cada
            # um vendo que "ainda existe outro", e o sistema terminando sem
            # nenhum. O BEGIN IMMEDIATE de `transacao` serializa as duas.
            if atual["papel"] == "admin":
                restantes = conexao.execute(
                    "SELECT COUNT(*) AS n FROM usuarios WHERE papel = 'admin' AND id <> ?",
                    (alvo_id,),
                ).fetchone()["n"]
                if restantes == 0:
                    raise modelo.RegraViolada(
                        "Esta é a única conta de administrador. Promova outra pessoa "
                        "a administrador antes de rebaixar esta, ou o sistema ficaria "
                        "sem quem gerencie as contas."
                    )

            conexao.execute(
                "UPDATE usuarios SET papel = ? WHERE id = ?", (papel, alvo_id)
            )
            _registrar_alteracao(
                conexao, alvo_id=alvo_id, autor_id=autor_id, acao="papel",
                de=atual["papel"], para=papel,
            )

            # Papel sem escrita não guarda vínculo com ponto de coleta. O
            # desligamento entra na trilha como qualquer outra alteração: quem
            # for auditar precisa ver que o vínculo caiu, e por quê.
            if papel == "visitante" and atual["ponto_id"]:
                conexao.execute(
                    "UPDATE usuarios SET ponto_id = NULL WHERE id = ?", (alvo_id,)
                )
                _registrar_alteracao(
                    conexao, alvo_id=alvo_id, autor_id=autor_id, acao="ponto",
                    de=atual["ponto_id"], para="",
                )
                ponto_id = ...

        if ponto_id is not ... and ponto_id != atual["ponto_id"]:
            if ponto_id and not conexao.execute(
                "SELECT 1 FROM pontos WHERE id = ?", (ponto_id,)
            ).fetchone():
                raise modelo.RegraViolada("Ponto de coleta desconhecido.")
            conexao.execute(
                "UPDATE usuarios SET ponto_id = ? WHERE id = ?", (ponto_id, alvo_id)
            )
            _registrar_alteracao(
                conexao, alvo_id=alvo_id, autor_id=autor_id, acao="ponto",
                de=atual["ponto_id"] or "", para=ponto_id or "",
            )

        if senha_hash:
            conexao.execute(
                "UPDATE usuarios SET senha_hash = ? WHERE id = ?", (senha_hash, alvo_id)
            )
            # A trilha registra QUE houve redefinição, jamais o segredo.
            _registrar_alteracao(
                conexao, alvo_id=alvo_id, autor_id=autor_id, acao="senha",
            )

    return obter_usuario(conexao, alvo_id)
