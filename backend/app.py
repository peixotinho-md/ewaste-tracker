"""
app.py — Servidor do e-Trilha MS: API REST + entrega das páginas.

Como executar (a partir da raiz do projeto):

    python backend/app.py

E abrir http://localhost:8000

Este único processo faz as duas coisas: responde às chamadas da API em `/api/*`
e entrega os arquivos do front-end. Um servidor só simplifica a demonstração e
elimina o problema de CORS, já que tudo fica na mesma origem.
"""

import os
import secrets
import sys
from functools import wraps
from pathlib import Path

# Permite `import banco` e `import modelo` mesmo executando de outra pasta.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from flask import Flask, jsonify, request, send_from_directory, session
from werkzeug.security import check_password_hash, generate_password_hash

import banco
import modelo

RAIZ = Path(__file__).resolve().parent.parent

# --------------------------------------------------------------------------- #
# Quais arquivos o servidor entrega
#
# A lista é explícita de propósito. Um servidor que entrega qualquer arquivo da
# pasta acabaria servindo também `backend/etrilha.db` (o banco inteiro, com os
# hashes de senha) e a pasta `backup/`. Aqui, o que não está na lista não sai.
# --------------------------------------------------------------------------- #

PAGINAS = {
    "index.html", "rastrear.html", "registrar.html", "etiqueta.html",
    "scanner.html", "pontos.html", "painel.html", "conta.html",
}
ARQUIVOS_RAIZ = {"sw.js", "manifest.webmanifest", "icon.svg"}
PASTAS_PUBLICAS = {"css", "js", "vendor"}

app = Flask(__name__, static_folder=None)


def _chave_de_sessao() -> bytes:
    """
    Chave que assina o cookie de sessão.

    Em produção viria de variável de ambiente. Aqui, é gerada uma vez e guardada
    em `backend/.chave-sessao` para que as sessões sobrevivam ao reinício do
    servidor durante a demonstração.
    """
    if variavel := os.environ.get("ETRILHA_SECRET"):
        return variavel.encode()

    caminho = Path(__file__).resolve().parent / ".chave-sessao"
    if not caminho.exists():
        caminho.write_bytes(secrets.token_bytes(32))
    return caminho.read_bytes()


app.secret_key = _chave_de_sessao()
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,   # o JavaScript da página não lê o cookie
    SESSION_COOKIE_SAMESITE="Lax",  # não acompanha requisições de outros sites
    JSON_SORT_KEYS=False,
)


# --------------------------------------------------------------------------- #
# Conexão por requisição
# --------------------------------------------------------------------------- #

def com_banco(rota):
    """Abre uma conexão para a requisição e fecha ao final, mesmo com erro."""
    @wraps(rota)
    def envelope(*args, **kwargs):
        conexao = banco.conectar()
        try:
            return rota(conexao, *args, **kwargs)
        finally:
            conexao.close()
    return envelope


@app.errorhandler(modelo.RegraViolada)
def erro_de_regra(erro):
    """Regra de negócio violada vira 400 com a mensagem pronta para a tela."""
    return jsonify({"erro": str(erro)}), 400


@app.errorhandler(404)
def nao_encontrado(_erro):
    if request.path.startswith("/api/"):
        return jsonify({"erro": "Recurso não encontrado."}), 404
    return "Página não encontrada.", 404


# --------------------------------------------------------------------------- #
# Identidade: usuário logado ou visitante
#
# A conta é opcional em todo o fluxo. Quem registra um aparelho sem conta recebe
# um identificador de visitante no cookie de sessão; ao criar conta ou entrar,
# esses itens são adotados pela conta.
# --------------------------------------------------------------------------- #

def usuario_da_sessao() -> str | None:
    return session.get("usuario_id")


def visitante_da_sessao(criar: bool = False) -> str | None:
    if "visitante_id" not in session and criar:
        session["visitante_id"] = banco.novo_id("v")
        session.permanent = True
    return session.get("visitante_id")


# --------------------------------------------------------------------------- #
# API — pontos de coleta
# --------------------------------------------------------------------------- #

@app.get("/api/pontos")
@com_banco
def pontos(conexao):
    return jsonify(banco.listar_pontos(conexao))


# --------------------------------------------------------------------------- #
# API — itens e cadeia de custódia
# --------------------------------------------------------------------------- #

@app.get("/api/itens")
@com_banco
def itens(conexao):
    return jsonify(banco.listar_itens(conexao))


@app.get("/api/eventos")
@com_banco
def eventos(conexao):
    return jsonify(banco.listar_eventos(conexao))


@app.get("/api/itens/<codigo>")
@com_banco
def item(conexao, codigo):
    canonico = modelo.normalizar_codigo(codigo)
    if not canonico:
        return jsonify({"erro": "Código de rastreio inválido."}), 400
    encontrado = banco.obter_item(conexao, canonico)
    if encontrado is None:
        return jsonify({"erro": "Código de rastreio não encontrado."}), 404
    return jsonify(encontrado)


@app.get("/api/itens/<codigo>/rastreio")
@com_banco
def rastreio(conexao, codigo):
    canonico = modelo.normalizar_codigo(codigo)
    if not canonico:
        return jsonify({"erro": "Código de rastreio inválido."}), 400
    resultado = banco.obter_rastreio(conexao, canonico)
    if resultado is None:
        return jsonify({"erro": "Código de rastreio não encontrado."}), 404
    return jsonify(resultado)


@app.post("/api/itens")
@com_banco
def criar_item(conexao):
    corpo = request.get_json(silent=True) or {}

    categoria = modelo.validar_categoria(corpo.get("categoria"))
    peso = modelo.normalizar_peso(corpo.get("pesoKg"), categoria)
    ponto_origem = corpo.get("pontoOrigemId") or None

    if ponto_origem and not conexao.execute(
        "SELECT 1 FROM pontos WHERE id = ?", (ponto_origem,)
    ).fetchone():
        raise modelo.RegraViolada("Ponto de coleta desconhecido.")

    usuario_id = usuario_da_sessao()
    novo = banco.criar_item(
        conexao,
        categoria=categoria,
        marca=modelo.texto(corpo.get("marca"), "marca"),
        peso_kg=peso,
        ponto_origem_id=ponto_origem,
        responsavel=modelo.texto(corpo.get("responsavel"), "responsavel"),
        usuario_id=usuario_id,
        visitante_id=None if usuario_id else visitante_da_sessao(criar=True),
    )
    return jsonify(novo), 201


@app.post("/api/itens/<codigo>/eventos")
@com_banco
def criar_evento(conexao, codigo):
    canonico = modelo.normalizar_codigo(codigo)
    if not canonico:
        return jsonify({"erro": "Código de rastreio inválido."}), 400

    corpo = request.get_json(silent=True) or {}
    ponto_id = corpo.get("pontoId") or None

    if ponto_id and not conexao.execute(
        "SELECT 1 FROM pontos WHERE id = ?", (ponto_id,)
    ).fetchone():
        raise modelo.RegraViolada("Ponto de coleta desconhecido.")

    evento = banco.registrar_evento(
        conexao,
        canonico,
        etapa=corpo.get("etapa"),
        ponto_id=ponto_id,
        responsavel=modelo.texto(corpo.get("responsavel"), "responsavel"),
        observacao=modelo.texto(corpo.get("observacao"), "observacao"),
    )
    return jsonify(evento), 201


# --------------------------------------------------------------------------- #
# API — conta (opcional)
# --------------------------------------------------------------------------- #

@app.get("/api/sessao")
@com_banco
def sessao_atual(conexao):
    usuario_id = usuario_da_sessao()
    if not usuario_id:
        return jsonify({"usuario": None})
    return jsonify({"usuario": banco.obter_usuario(conexao, usuario_id)})


@app.post("/api/usuarios")
@com_banco
def cadastrar(conexao):
    corpo = request.get_json(silent=True) or {}
    nome = modelo.texto(corpo.get("nome"), "nome")
    email = modelo.texto(corpo.get("email"), "email")
    senha = str(corpo.get("senha") or "")

    if not nome:
        raise modelo.RegraViolada("Informe seu nome.")
    if "@" not in email or "." not in email.split("@")[-1]:
        raise modelo.RegraViolada("E-mail inválido.")
    if len(senha) < 6:
        raise modelo.RegraViolada("A senha precisa ter ao menos 6 caracteres.")

    # generate_password_hash usa PBKDF2 com sal aleatório e muitas iterações.
    # É o oposto do SHA-256 simples da versão anterior: propositalmente lento,
    # para que testar senhas em massa não seja viável.
    usuario = banco.criar_usuario(
        conexao, nome=nome, email=email, senha_hash=generate_password_hash(senha)
    )

    adotados = banco.adotar_itens_do_visitante(conexao, usuario["id"], visitante_da_sessao())
    _abrir_sessao(usuario["id"])
    return jsonify({"usuario": usuario, "adotados": adotados}), 201


@app.post("/api/sessao")
@com_banco
def entrar(conexao):
    corpo = request.get_json(silent=True) or {}
    linha = banco.buscar_usuario_por_email(conexao, corpo.get("email") or "")
    senha = str(corpo.get("senha") or "")

    if linha is None or not check_password_hash(linha["senha_hash"], senha):
        # Mensagem genérica de propósito: não revela se o e-mail está cadastrado.
        return jsonify({"erro": "E-mail ou senha incorretos."}), 401

    usuario = {"id": linha["id"], "nome": linha["nome"], "email": linha["email"]}
    adotados = banco.adotar_itens_do_visitante(conexao, usuario["id"], visitante_da_sessao())
    _abrir_sessao(usuario["id"])
    return jsonify({"usuario": usuario, "adotados": adotados})


@app.delete("/api/sessao")
def sair():
    session.clear()
    return jsonify({"usuario": None})


def _abrir_sessao(usuario_id: str) -> None:
    """
    Troca o identificador da sessão ao autenticar.

    Descartar a sessão anterior antes de gravar a nova evita fixação de sessão:
    um identificador obtido por terceiros antes do login deixa de valer depois dele.
    """
    session.clear()
    session["usuario_id"] = usuario_id
    session.permanent = True


@app.get("/api/meus-itens")
@com_banco
def meus_itens(conexao):
    return jsonify(
        banco.itens_do_dono(conexao, usuario_da_sessao(), visitante_da_sessao())
    )


# --------------------------------------------------------------------------- #
# API — demonstração
# --------------------------------------------------------------------------- #

@app.post("/api/demo/reiniciar")
def reiniciar_demo():
    """Recria o banco com os dados de exemplo. Existe só para a demonstração."""
    banco.preparar(recriar=True)
    session.clear()
    return jsonify({"ok": True})


@app.get("/api/saude")
@com_banco
def saude(conexao):
    """Diagnóstico rápido: o servidor responde e o banco está carregado?"""
    contar = lambda tabela: conexao.execute(f"SELECT COUNT(*) AS n FROM {tabela}").fetchone()["n"]
    return jsonify({
        "ok": True,
        "banco": str(banco.CAMINHO_BANCO),
        "pontos": contar("pontos"),
        "itens": contar("itens"),
        "eventos": contar("eventos"),
        "usuarios": contar("usuarios"),
    })


# --------------------------------------------------------------------------- #
# Entrega do front-end
# --------------------------------------------------------------------------- #

@app.get("/")
def home():
    return send_from_directory(RAIZ, "index.html")


@app.get("/<nome>")
def arquivo_raiz(nome):
    if nome in PAGINAS or nome in ARQUIVOS_RAIZ:
        resposta = send_from_directory(RAIZ, nome)
        if nome == "sw.js":
            # O service worker precisa poder controlar todo o site, e não apenas
            # a pasta de onde foi servido.
            resposta.headers["Service-Worker-Allowed"] = "/"
        return resposta
    return nao_encontrado(None)


@app.get("/<pasta>/<path:arquivo>")
def arquivo_publico(pasta, arquivo):
    if pasta not in PASTAS_PUBLICAS:
        return nao_encontrado(None)
    # send_from_directory já barra caminhos com ".." saindo da pasta.
    return send_from_directory(RAIZ / pasta, arquivo)


# --------------------------------------------------------------------------- #

def main() -> None:
    banco.preparar()
    porta = int(os.environ.get("PORTA", 8000))
    print(f"\n  e-Trilha MS em execução:  http://localhost:{porta}")
    print(f"  Banco de dados:           {banco.CAMINHO_BANCO}")
    print("  Encerre com Ctrl+C\n")
    app.run(host="127.0.0.1", port=porta, debug=False)


if __name__ == "__main__":
    main()
