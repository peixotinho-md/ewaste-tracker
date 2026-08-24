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
    "admin.html",
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
# Autorização
#
# Ler é público; ESCREVER na cadeia de custódia não. Quem lê a etiqueta é quem
# declara que o aparelho passou por uma etapa, e essa declaração é o produto do
# sistema — se qualquer um puder emiti-la, ela não vale nada.
#
# A verificação está AQUI, e não só na tela, porque é aqui que ela é efetiva:
# esconder o botão não impede um POST feito com curl. O papel é lido do banco a
# cada requisição, e não guardado no cookie — assim, revogar o papel de alguém
# tem efeito imediato, sem esperar a sessão dele expirar.
# --------------------------------------------------------------------------- #

def conta_da_sessao(conexao) -> dict | None:
    usuario_id = usuario_da_sessao()
    return banco.obter_usuario(conexao, usuario_id) if usuario_id else None


def exige(*papeis: str):
    """
    Fecha a rota para quem não tem um dos papéis exigidos.

    Responde 401 a quem não está autenticado (falta entrar) e 403 a quem está
    autenticado mas não tem o papel (entrar de novo não resolve). A distinção
    importa para a tela saber se manda a pessoa fazer login ou explica que a
    conta dela não tem permissão.
    """
    def decorador(rota):
        @wraps(rota)
        def envelope(conexao, *args, **kwargs):
            conta = conta_da_sessao(conexao)
            if conta is None:
                return jsonify({
                    "erro": "Esta ação exige uma conta de operador. Entre para continuar."
                }), 401
            if conta["papel"] not in papeis:
                return jsonify({
                    "erro": "Sua conta não tem permissão para esta ação. "
                            "Peça a um administrador para ajustar o papel dela."
                }), 403
            return rota(conexao, *args, conta=conta, **kwargs)
        return envelope
    return decorador


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
@exige("operador", "admin")
def criar_evento(conexao, codigo, conta):
    """
    Acrescenta um elo à cadeia de custódia. Só operador e admin chegam aqui.

    Duas informações do corpo da requisição são DESCARTADAS de propósito:

      responsavel  vem do nome da conta autenticada. Se viesse do formulário,
                   qualquer operador poderia assinar o evento com o nome de
                   outra pessoa, e a assinatura não provaria nada.
      pontoId      é o ponto ao qual o operador está vinculado, quando há um.
                   Assim ele não registra passagem por um local onde não
                   trabalha. Só o admin, que não tem ponto fixo, informa o local.
    """
    canonico = modelo.normalizar_codigo(codigo)
    if not canonico:
        return jsonify({"erro": "Código de rastreio inválido."}), 400

    corpo = request.get_json(silent=True) or {}
    ponto_id = conta["pontoId"] or (corpo.get("pontoId") or None)

    if ponto_id and not conexao.execute(
        "SELECT 1 FROM pontos WHERE id = ?", (ponto_id,)
    ).fetchone():
        raise modelo.RegraViolada("Ponto de coleta desconhecido.")

    evento = banco.registrar_evento(
        conexao,
        canonico,
        etapa=corpo.get("etapa"),
        ponto_id=ponto_id,
        responsavel=modelo.texto(conta["nome"], "responsavel"),
        observacao=modelo.texto(corpo.get("observacao"), "observacao"),
        apagamento=corpo.get("apagamento"),
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

    usuario = banco.usuario_json(linha)
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
# API — administração das contas
#
# Toda rota daqui exige papel `admin`, verificado no servidor. A tela
# `admin.html` some do menu para quem não é admin, mas é este decorador que
# realmente fecha a porta.
# --------------------------------------------------------------------------- #

@app.get("/api/admin/usuarios")
@com_banco
@exige("admin")
def admin_usuarios(conexao, conta):
    usuarios = banco.listar_usuarios(conexao)
    itens_por_dono = banco.contar_itens_por_dono(conexao)
    for usuario in usuarios:
        usuario["itens"] = itens_por_dono.get(usuario["id"], 0)
        # A tela usa isto para não oferecer ao admin ações sobre si mesmo que
        # o servidor recusaria depois.
        usuario["souEu"] = usuario["id"] == conta["id"]
    return jsonify(usuarios)


@app.patch("/api/admin/usuarios/<usuario_id>")
@com_banco
@exige("admin")
def admin_atualizar_usuario(conexao, usuario_id, conta):
    """
    Altera papel, ponto vinculado e senha de uma conta.

    Só estes três campos. Nome e e-mail são da pessoa, não do administrador —
    quem os altera é o dono da conta.
    """
    corpo = request.get_json(silent=True) or {}

    papel = modelo.validar_papel(corpo["papel"]) if "papel" in corpo else None
    senha_hash = (
        generate_password_hash(modelo.validar_senha(corpo["senha"]))
        if corpo.get("senha")
        else None
    )
    # Ausente = não mexer; presente e vazio = desvincular do ponto.
    ponto_id = (corpo.get("pontoId") or None) if "pontoId" in corpo else ...

    if papel is None and senha_hash is None and ponto_id is ...:
        raise modelo.RegraViolada("Nada a alterar nesta conta.")

    if usuario_id == conta["id"] and papel is not None and papel != "admin":
        # A regra do "último admin" já está no banco; esta é uma proteção a
        # mais contra o tiro no próprio pé, que é o caso mais comum.
        raise modelo.RegraViolada(
            "Você não pode rebaixar a si mesmo. Peça a outro administrador."
        )

    atualizado = banco.atualizar_usuario(
        conexao, usuario_id, autor=conta,
        papel=papel, ponto_id=ponto_id, senha_hash=senha_hash,
    )
    return jsonify(atualizado)


@app.delete("/api/admin/usuarios/<usuario_id>")
@com_banco
@exige("admin")
def admin_excluir_usuario(conexao, usuario_id, conta):
    """
    Exclui uma conta, exigindo a senha de quem está excluindo.

    Pedir a senha de novo aqui não é redundância com o login: a sessão pode
    estar aberta num computador que ficou sozinho no galpão, e esta é a única
    ação da tela que não tem volta. É o mesmo raciocínio do `sudo`, que
    pergunta a senha mesmo já sabendo quem você é.

    A resposta a uma senha errada é 403 com mensagem própria, e não o 401 do
    login: a sessão continua válida: o que faltou foi a confirmação.
    """
    corpo = request.get_json(silent=True) or {}
    linha = conexao.execute(
        "SELECT senha_hash FROM usuarios WHERE id = ?", (conta["id"],)
    ).fetchone()

    if linha is None or not check_password_hash(linha["senha_hash"], str(corpo.get("senha") or "")):
        return jsonify({"erro": "Senha incorreta. A conta não foi excluída."}), 403

    if usuario_id == conta["id"]:
        raise modelo.RegraViolada(
            "Você não pode excluir a própria conta. Peça a outro administrador."
        )

    return jsonify(banco.excluir_usuario(conexao, usuario_id, autor=conta))


@app.get("/api/admin/itens")
@com_banco
@exige("admin")
def admin_itens(conexao, conta):
    """
    Todos os aparelhos com etapa, origem, dono e nº de leituras.

    A lista pública `/api/itens` continua existindo e continua aberta — é dela
    que o painel tira os indicadores. Esta rota acrescenta o cruzamento com
    pontos, contas e eventos, útil para quem administra e desnecessário para
    quem só consulta um código.
    """
    return jsonify(banco.listar_itens_detalhados(conexao))


@app.get("/api/admin/alteracoes")
@com_banco
@exige("admin")
def admin_alteracoes(conexao, conta):
    """
    Trilha de quem alterou o quê nas contas — somente de acréscimo.

    Com `?usuario=<id>`, devolve só o histórico daquela conta, que é o que a
    tela de detalhe mostra.
    """
    return jsonify(
        banco.listar_alteracoes(conexao, usuario_id=request.args.get("usuario") or None)
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
    print("\n  Contas de demonstração (públicas, só para a apresentação):")
    for conta in banco.CONTAS_DEMO:
        print(f"    {conta['papel']:<9} {conta['email']:<20} senha: {conta['senha']}")
    print("\n  Encerre com Ctrl+C\n")
    app.run(host="127.0.0.1", port=porta, debug=False)


if __name__ == "__main__":
    main()
