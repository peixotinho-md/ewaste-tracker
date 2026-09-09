"""
Quem pode chamar cada rota da API.

Este é o arquivo que verifica o RNF06 do Relatório Técnico — "regras impostas
pelo servidor, não pela tela". A tela esconde botões por gentileza; o que de
fato fecha a porta é o decorador `exige` em `backend/app.py`, e até agora nada
conferia se ele estava fechando.

A distinção entre 401 e 403 é decisão de projeto documentada em app.py, e é
verificada aqui uma a uma: **401** quer dizer "falta autenticar" e **403**, "você
está autenticado e mesmo assim não pode". Trocar um pelo outro não quebra
nenhuma tela — e é exatamente por isso que só um teste percebe.
"""

import pytest

# Cada linha é (método, caminho, papel mínimo). `None` em papel significa rota
# pública. A tabela é a especificação: se uma rota nova entrar em app.py sem
# entrar aqui, o teste de cobertura no fim do arquivo acusa.
ROTAS = [
    # públicas
    ("GET",    "/api/pontos",                        None),
    ("GET",    "/api/saude",                         None),
    ("GET",    "/api/sessao",                        None),
    ("GET",    "/api/itens/MS-3H7K-P2R6/rastreio",   None),
    ("POST",   "/api/usuarios",                      None),
    ("POST",   "/api/sessao",                        None),
    ("DELETE", "/api/sessao",                        None),
    # exigem conta, qualquer papel
    ("GET",    "/api/painel",                        "visitante"),
    ("POST",   "/api/itens",                         "visitante"),
    ("GET",    "/api/meus-itens",                    "visitante"),
    ("POST",   "/api/sessao/senha",                  "visitante"),
    # exigem operador
    ("POST",   "/api/itens/MS-3H7K-P2R6/eventos",    "operador"),
    # exigem admin
    ("GET",    "/api/admin/usuarios",                "admin"),
    ("PATCH",  "/api/admin/usuarios/u-qualquer",     "admin"),
    ("DELETE", "/api/admin/usuarios/u-qualquer",     "admin"),
    ("GET",    "/api/admin/itens",                   "admin"),
    ("GET",    "/api/admin/alteracoes",              "admin"),
    ("POST",   "/api/demo/reiniciar",                "admin"),
]

FECHADAS = [(m, c, p) for m, c, p in ROTAS if p is not None]
ABERTAS = [(m, c) for m, c, p in ROTAS if p is None]

# Ordem de menor para maior poder. Um papel cobre todos os anteriores.
ESCALA = ["visitante", "operador", "admin"]


def chamar(cliente, metodo, caminho):
    return cliente.open(caminho, method=metodo, json={})


def contas_abaixo(papel):
    """Os papéis que NÃO alcançam o papel exigido."""
    return ESCALA[: ESCALA.index(papel)]


# --------------------------------------------------------------------------- #
# Sem sessão
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("metodo,caminho,papel", FECHADAS)
def teste_sem_sessao_responde_401(cliente, metodo, caminho, papel):
    resposta = chamar(cliente, metodo, caminho)
    assert resposta.status_code == 401, (
        f"{metodo} {caminho} devolveu {resposta.status_code} para quem não entrou; "
        f"401 é 'falta autenticar' e é o que a tela usa para mandar ao login"
    )


@pytest.mark.parametrize("metodo,caminho,papel", FECHADAS)
def teste_sem_sessao_responde_em_json(cliente, metodo, caminho, papel):
    """
    A recusa precisa falar o dialeto que `js/store.js` entende.

    O wrapper `api()` lê `{"erro": ...}` do corpo e o transforma na mensagem da
    tela. Uma recusa em HTML cairia no `catch` e viraria "erro de rede" — a
    pessoa veria um problema de conexão onde na verdade só faltou entrar.
    """
    resposta = chamar(cliente, metodo, caminho)
    assert resposta.is_json, f"{metodo} {caminho} recusou fora de JSON"
    assert resposta.get_json().get("erro")


# O login é público, mas responde 401 quando a credencial não confere — e o corpo
# vazio que este arquivo manda nunca confere. Ali o 401 significa "essa senha não
# é a sua", e não "entre primeiro", que é o sentido verificado no resto do arquivo.
LOGIN = ("POST", "/api/sessao")


@pytest.mark.parametrize("metodo,caminho", ABERTAS)
def teste_rotas_publicas_dispensam_sessao(cliente, metodo, caminho):
    """Consultar a trilha de um código que se tem em mãos é de todos."""
    resposta = chamar(cliente, metodo, caminho)
    assert resposta.status_code != 403, (
        f"{metodo} {caminho} deveria ser pública e respondeu 403"
    )
    if (metodo, caminho) != LOGIN:
        assert resposta.status_code != 401, (
            f"{metodo} {caminho} deveria ser pública e exigiu autenticação"
        )


# --------------------------------------------------------------------------- #
# Com sessão, papel insuficiente
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize(
    "metodo,caminho,papel,papel_de_quem_tenta",
    [(m, c, p, menor) for m, c, p in FECHADAS for menor in contas_abaixo(p)],
)
def teste_papel_insuficiente_responde_403(
    cliente, fabricar_conta, entrar, metodo, caminho, papel, papel_de_quem_tenta
):
    entrar(fabricar_conta(papel_de_quem_tenta))
    resposta = chamar(cliente, metodo, caminho)
    assert resposta.status_code == 403, (
        f"{metodo} {caminho} exige {papel} e devolveu {resposta.status_code} para "
        f"{papel_de_quem_tenta}; 403 é 'autenticado, mas sem permissão' e é o que "
        f"distingue este caso de uma sessão ausente"
    )


# Duas rotas pedem a senha de novo, mesmo com sessão válida — é re-autenticação
# no estilo do `sudo`, porque o cookie prova que alguém entrou, não que quem está
# no teclado agora é o dono da conta. Elas também respondem 403, com outro
# sentido, então o corpo enviado precisa trazer a senha correta para que o 403
# restante signifique de fato "papel insuficiente".
def corpo_para(caminho, conta):
    if caminho == "/api/sessao/senha":
        return {"senhaAtual": conta["senha"], "senhaNova": "senha-nova-valida"}
    if caminho.startswith("/api/admin/usuarios/") and caminho != "/api/admin/usuarios":
        return {"senha": conta["senha"], "papel": "operador"}
    return {}


@pytest.mark.parametrize("metodo,caminho,papel", FECHADAS)
def teste_papel_suficiente_passa_da_autorizacao(
    cliente, fabricar_conta, entrar, primeiro_ponto, metodo, caminho, papel
):
    """
    Com o papel certo, a resposta pode ser qualquer coisa menos 401 ou 403.

    Não se afirma 200 aqui de propósito: várias destas rotas recusam por falta de
    dados no corpo (400) ou por id inexistente (404), e isso é assunto dos
    arquivos específicos. O que este teste garante é que o portão abriu.
    """
    ponto = primeiro_ponto["id"] if papel == "operador" else None
    conta = entrar(fabricar_conta(papel, ponto_id=ponto))
    resposta = cliente.open(caminho, method=metodo, json=corpo_para(caminho, conta))
    assert resposta.status_code not in (401, 403), (
        f"{metodo} {caminho} recusou {papel}, que deveria passar"
    )


# --------------------------------------------------------------------------- #
# Senha provisória: a conta existe, mas ainda não prova quem a usa
# --------------------------------------------------------------------------- #

TROCA_DE_SENHA = ("POST", "/api/sessao/senha")


@pytest.mark.parametrize(
    "metodo,caminho,papel",
    [linha for linha in FECHADAS if (linha[0], linha[1]) != TROCA_DE_SENHA],
)
def teste_senha_provisoria_so_pode_trocar_a_propria_senha(
    cliente, fabricar_conta, entrar, metodo, caminho, papel
):
    """
    Enquanto a senha em vigor foi escolhida por outra pessoa, existe alguém além
    do dono que conhece o segredo — e a conta não prova quem a está usando. Até
    a troca, o servidor aceita dessa conta apenas a própria troca de senha.
    """
    entrar(fabricar_conta(papel, provisoria=True))
    resposta = chamar(cliente, metodo, caminho)
    assert resposta.status_code == 403, (
        f"{metodo} {caminho} respondeu {resposta.status_code} para conta com senha "
        f"provisória; só a troca de senha deveria passar"
    )


def teste_senha_provisoria_alcanca_a_troca_de_senha(cliente, fabricar_conta, entrar):
    conta = fabricar_conta("visitante", provisoria=True)
    entrar(conta)
    resposta = cliente.post(
        "/api/sessao/senha",
        json={"senhaAtual": conta["senha"], "senhaNova": "outra-senha-boa"},
    )
    assert resposta.status_code == 200
    assert resposta.get_json()["usuario"]["senhaProvisoria"] is False


# --------------------------------------------------------------------------- #
# A tabela acima descreve mesmo a API?
# --------------------------------------------------------------------------- #

def teste_toda_rota_de_api_esta_na_tabela():
    """
    Impede que uma rota nova entre em `app.py` sem passar por este arquivo.

    Sem isto, acrescentar um endpoint de administração e esquecer o `@exige`
    passaria despercebido: nenhum teste existente falharia, porque nenhum teste
    conheceria a rota.
    """
    import app as aplicacao

    declaradas = {(m, c) for m, c, _ in ROTAS}

    reais = set()
    for regra in aplicacao.app.url_map.iter_rules():
        if not str(regra).startswith("/api/"):
            continue
        for metodo in regra.methods - {"HEAD", "OPTIONS"}:
            reais.add((metodo, str(regra)))

    def molde(caminho):
        """Troca os valores concretos da tabela pelos curingas do Flask."""
        return (
            caminho.replace("MS-3H7K-P2R6", "<codigo>")
            .replace("u-qualquer", "<usuario_id>")
        )

    faltando = reais - {(m, molde(c)) for m, c in declaradas}
    assert not faltando, (
        f"rotas de API fora da tabela de autorização deste arquivo: {sorted(faltando)}"
    )
