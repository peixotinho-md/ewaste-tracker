"""
A superfície que o servidor expõe: quais arquivos saem e quais páginas abrem.

Estes testes cobrem a seção 9.9 do Relatório Técnico. São os que ninguém escreve
e os que mais doem quando faltam: a lista de arquivos entregues é uma allowlist
explícita justamente para o servidor não acabar servindo `backend/etrilha.db`,
com todos os hashes de senha dentro — e nada verificava se a allowlist estava
fazendo o seu trabalho.

O portão de autenticação aqui é do nível do HTML, e não da API: uma página que
exige conta não é ENTREGUE a quem não entrou. Entregar o arquivo e deixar o
JavaScript decidir mostraria por um instante uma tela inutilizável, e ainda
dependeria de o script rodar.
"""

from pathlib import Path

import pytest

import app as aplicacao

RAIZ = Path(aplicacao.__file__).resolve().parent.parent

PAGINAS_FECHADAS = sorted(aplicacao.PAGINAS - aplicacao.PAGINAS_PUBLICAS)
PAGINAS_ABERTAS = sorted(aplicacao.PAGINAS_PUBLICAS - {"index"})
#: Fechadas para quem não entrou E para quem entrou sem poder de escrita.
PAGINAS_DE_QUALQUER_CONTA = sorted(
    aplicacao.PAGINAS - aplicacao.PAGINAS_PUBLICAS - aplicacao.PAGINAS_OPERADOR
)


# --------------------------------------------------------------------------- #
# Portão de autenticação no nível do HTML
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("pagina", PAGINAS_FECHADAS)
def teste_pagina_fechada_nao_e_entregue_sem_sessao(cliente, pagina):
    resposta = cliente.get(f"/{pagina}")
    assert resposta.status_code == 302
    assert resposta.headers["Location"] == f"/?destino={pagina}"


@pytest.mark.parametrize("pagina", PAGINAS_DE_QUALQUER_CONTA)
def teste_pagina_fechada_e_entregue_com_sessao(cliente, fabricar_conta, entrar, pagina):
    """
    Qualquer conta recebe o ARQUIVO; o que cada papel pode fazer é decidido pela
    API. Separar as duas coisas é o que permite que a tela de administração
    explique a falta de permissão em vez de sumir.

    A exceção é `PAGINAS_OPERADOR`, logo abaixo: lá não sobra nada que a tela
    possa explicar, porque a página inteira é a ação recusada.
    """
    entrar(fabricar_conta("visitante"))
    resposta = cliente.get(f"/{pagina}")
    assert resposta.status_code == 200
    assert b"<!doctype html" in resposta.data[:200].lower()


# --------------------------------------------------------------------------- #
# O leitor de QR não é entregue a quem não pode gravar etapas
#
# A aba some do menu para a conta comum (js/ui.js), mas esconder um link não é
# controle de acesso: quem digitar `/scanner` na barra de endereço tem de
# esbarrar no servidor. Sem isto, a pessoa veria a câmera abrir e cada leitura
# terminar em 403.
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("pagina", sorted(aplicacao.PAGINAS_OPERADOR))
def teste_pagina_de_operador_nao_e_entregue_a_visitante(
    cliente, fabricar_conta, entrar, pagina
):
    entrar(fabricar_conta("visitante"))
    resposta = cliente.get(f"/{pagina}")
    assert resposta.status_code == 302
    assert resposta.headers["Location"] == "/"


@pytest.mark.parametrize("papel", ["operador", "admin"])
@pytest.mark.parametrize("pagina", sorted(aplicacao.PAGINAS_OPERADOR))
def teste_pagina_de_operador_e_entregue_a_quem_grava(
    cliente, fabricar_conta, entrar, pagina, papel
):
    entrar(fabricar_conta(papel))
    resposta = cliente.get(f"/{pagina}")
    assert resposta.status_code == 200
    assert b"<!doctype html" in resposta.data[:200].lower()


@pytest.mark.parametrize("pagina", PAGINAS_ABERTAS)
def teste_pagina_publica_abre_sem_sessao(cliente, pagina):
    assert cliente.get(f"/{pagina}").status_code == 200


def teste_a_raiz_e_publica(cliente):
    """A porta de entrada precisa abrir para quem ainda não tem conta."""
    resposta = cliente.get("/")
    assert resposta.status_code == 200


@pytest.mark.parametrize("pagina", PAGINAS_FECHADAS)
def teste_senha_provisoria_fica_presa_na_raiz(cliente, fabricar_conta, entrar, pagina):
    """Sem isto, a pessoa navegaria por telas que a API vai recusar."""
    entrar(fabricar_conta("admin", provisoria=True))
    resposta = cliente.get(f"/{pagina}")
    assert resposta.status_code == 302
    assert resposta.headers["Location"] == "/"


# --------------------------------------------------------------------------- #
# Um endereço por página
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("pagina", sorted(aplicacao.PAGINAS - {"index"}))
def teste_a_forma_com_html_redireciona_para_a_limpa(cliente, pagina):
    resposta = cliente.get(f"/{pagina}.html")
    assert resposta.status_code == 302
    assert resposta.headers["Location"] == f"/{pagina}"


@pytest.mark.parametrize("caminho", ["/index", "/index.html"])
def teste_a_home_tem_um_endereco_so(cliente, caminho):
    resposta = cliente.get(caminho)
    assert resposta.status_code == 302
    assert resposta.headers["Location"] == "/"


def teste_o_redirecionamento_e_temporario(cliente):
    """
    302, e não 301: um permanente ficaria gravado no navegador de quem abriu uma
    vez, e este ainda é um protótipo em mudança.
    """
    assert cliente.get("/painel.html").status_code == 302


# --------------------------------------------------------------------------- #
# O que NÃO sai do servidor
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("caminho", [
    "/backend/etrilha.db",
    "/backend/app.py",
    "/backend/schema.sql",
    "/backend/.chave-sessao",
    "/dados/pontos.json",
    "/dados/itens-demo.json",
    "/backup/index.html",
    "/docs/RELATORIO-TECNICO.md",
    "/requirements.txt",
    "/README.md",
    "/.gitignore",
])
def teste_arquivo_fora_da_allowlist_nao_e_entregue(cliente, caminho):
    """
    O banco tem os hashes de senha de todo mundo; `dados/` e `backup/` não são
    parte da aplicação servida. A allowlist é o que impede que um dia alguém
    consiga baixá-los digitando o caminho.
    """
    resposta = cliente.get(caminho)
    assert resposta.status_code in (403, 404), (
        f"{caminho} respondeu {resposta.status_code}; nada fora de "
        f"{sorted(aplicacao.PASTAS_PUBLICAS)} deveria sair"
    )


@pytest.mark.parametrize("caminho", [
    "/css/../backend/etrilha.db",
    "/js/../backend/app.py",
    "/vendor/../../etc/passwd",
    "/css/%2e%2e/backend/etrilha.db",
])
def teste_travessia_de_diretorio_nao_escapa_das_pastas_publicas(cliente, caminho):
    resposta = cliente.get(caminho)
    assert resposta.status_code in (301, 302, 403, 404)
    assert b"sqlite" not in resposta.data.lower()[:64]


@pytest.mark.parametrize("caminho", [
    "/css/app.css", "/js/store.js", "/js/model.js", "/vendor/jsqr.js", "/vendor/qrcode.js",
])
def teste_as_pastas_publicas_sao_entregues(cliente, caminho):
    assert cliente.get(caminho).status_code == 200


@pytest.mark.parametrize("arquivo", sorted(aplicacao.ARQUIVOS_RAIZ))
def teste_arquivos_de_raiz_permitidos(cliente, arquivo):
    assert cliente.get(f"/{arquivo}").status_code == 200


def teste_o_service_worker_pode_controlar_o_site_inteiro(cliente):
    """Sem este cabeçalho, o SW só controlaria a pasta de onde foi servido."""
    resposta = cliente.get("/sw.js")
    assert resposta.status_code == 200
    assert resposta.headers.get("Service-Worker-Allowed") == "/"


def teste_pagina_inexistente_da_404(cliente):
    assert cliente.get("/nao-existe").status_code == 404


def teste_404_de_api_responde_em_json(cliente):
    """A tela precisa receber `{"erro": ...}` também quando erra o endereço."""
    resposta = cliente.get("/api/nao-existe")
    assert resposta.status_code == 404
    assert resposta.is_json
    assert resposta.get_json().get("erro")


# --------------------------------------------------------------------------- #
# A allowlist descreve mesmo o que está no disco?
# --------------------------------------------------------------------------- #

def teste_toda_pagina_da_allowlist_existe_no_disco():
    faltando = [p for p in sorted(aplicacao.PAGINAS) if not (RAIZ / f"{p}.html").exists()]
    assert not faltando, f"páginas na allowlist sem arquivo correspondente: {faltando}"


def teste_todo_html_da_raiz_esta_na_allowlist():
    """
    Impede os dois erros simétricos: uma página nova ficar inacessível porque
    ninguém a acrescentou à lista, e — pior — uma página entrar no repositório
    sem passar pela decisão de ser pública ou fechada.
    """
    no_disco = {caminho.stem for caminho in RAIZ.glob("*.html")}
    fora = sorted(no_disco - aplicacao.PAGINAS)
    assert not fora, f"arquivos .html na raiz fora da allowlist: {fora}"


def teste_toda_pasta_publica_existe():
    faltando = [p for p in sorted(aplicacao.PASTAS_PUBLICAS) if not (RAIZ / p).is_dir()]
    assert not faltando, faltando
