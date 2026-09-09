"""
`backend/modelo.py` e `js/model.js` precisam contar a mesma história.

A duplicação entre os dois é intencional e está justificada na seção 9.2 do
Relatório Técnico: a tela valida para ajudar, o servidor valida para valer. Mas
uma duplicação intencional continua sendo duplicação — e o modo como ela falha é
silencioso. Mudar o prazo de uma etapa só no Python não quebra nada: o painel
passa a marcar como atrasado o que o servidor considera no prazo, e ninguém
descobre até alguém comparar as duas telas.

O que dá para verificar aqui são as TABELAS, lendo `js/model.js` como texto.
Executar o JavaScript exigiria Node, que o projeto não usa e não instala; então
a paridade dos ALGORITMOS (dígito verificador, CO2e evitado) continua sendo
conferida à mão. Está registrado como limitação em vez de fingido como coberto.

Se este arquivo falhar, a mensagem diz qual tabela divergiu — o conserto é
alinhar os dois lados, nunca afrouxar a comparação.
"""

import json
import re
from pathlib import Path

import pytest

import modelo

RAIZ = Path(modelo.__file__).resolve().parent.parent
MODEL_JS = (RAIZ / "js" / "model.js").read_text(encoding="utf-8")
STORE_JS = (RAIZ / "js" / "store.js").read_text(encoding="utf-8")


def bloco(fonte: str, declaracao: str, abre: str, fecha: str) -> str:
    """
    Recorta o corpo de uma constante exportada do JavaScript.

    Recorta pelo fechamento na COLUNA ZERO (`];` ou `};` no início da linha),
    que é como o arquivo está formatado. Assim o recorte não se perde nos objetos
    aninhados de `composicao`, que trazem chaves no meio do caminho.
    """
    inicio = fonte.index(f"{declaracao} = {abre}") + len(f"{declaracao} = {abre}")
    fim = fonte.index(f"\n{fecha};", inicio)
    return fonte[inicio:fim]


# --------------------------------------------------------------------------- #
# Etapas — a ordem É a máquina de estados
# --------------------------------------------------------------------------- #

ETAPAS_JS = bloco(MODEL_JS, "export const ETAPAS", "[", "]")


def teste_as_etapas_sao_as_mesmas_e_na_mesma_ordem():
    ids = re.findall(r"id: '([A-Z_]+)'", ETAPAS_JS)
    assert ids == modelo.IDS_ETAPAS, (
        "as etapas divergiram entre js/model.js e backend/modelo.py; a ORDEM é a "
        "própria máquina de estados, então trocá-la muda quais transições o "
        "servidor aceita"
    )


def teste_os_prazos_de_cada_etapa_sao_os_mesmos():
    slas_js = [None if v == "null" else int(v)
               for v in re.findall(r"slaHoras: (\d+|null)", ETAPAS_JS)]
    slas_py = [e["sla_horas"] for e in modelo.ETAPAS]
    assert slas_js == slas_py, (
        "os prazos (SLA) divergiram; o painel marcaria como pendência o que o "
        "servidor considera no prazo"
    )


def teste_os_rotulos_das_etapas_sao_os_mesmos():
    rotulos_js = re.findall(r"rotulo: '([^']+)'", ETAPAS_JS)
    assert rotulos_js == [e["rotulo"] for e in modelo.ETAPAS]


# --------------------------------------------------------------------------- #
# Categorias
# --------------------------------------------------------------------------- #

CATEGORIAS_JS = bloco(MODEL_JS, "export const CATEGORIAS", "[", "]")


def teste_as_categorias_sao_as_mesmas():
    ids = re.findall(r"id: '([a-z]+)'", CATEGORIAS_JS)
    assert sorted(ids) == sorted(modelo.CATEGORIAS), (
        "uma categoria existe de um lado só: a tela ofereceria uma opção que o "
        "servidor recusa, ou deixaria de oferecer uma que ele aceita"
    )


def teste_os_pesos_medios_sao_os_mesmos():
    """
    O peso médio é o que entra quando ninguém tem balança — e é ele que alimenta
    todo o cálculo de material recuperado e de CO2e evitado. Divergir aqui faz a
    tela mostrar um número e o banco guardar outro.
    """
    pares_js = dict(zip(
        re.findall(r"id: '([a-z]+)'", CATEGORIAS_JS),
        (float(v) for v in re.findall(r"pesoMedioKg: ([\d.]+)", CATEGORIAS_JS)),
    ))
    assert pares_js == modelo.CATEGORIAS


def teste_as_categorias_com_midia_sao_as_mesmas():
    """
    Divergir aqui é grave: uma categoria que o servidor considera com mídia e a
    tela não faz a triagem ser recusada sem que o formulário tenha pedido o
    atestado — a pessoa não entende o erro e não tem como corrigi-lo.
    """
    trecho = bloco(MODEL_JS, "export const CATEGORIAS_COM_MIDIA", "new Set([", "])")
    ids = set(re.findall(r"'([a-z]+)'", trecho))
    assert ids == modelo.CATEGORIAS_COM_MIDIA


# --------------------------------------------------------------------------- #
# Apagamento seguro
# --------------------------------------------------------------------------- #

def teste_as_midias_sao_as_mesmas():
    trecho = bloco(MODEL_JS, "export const MIDIAS", "{", "}")
    ids = set(re.findall(r"^\s{2}(\w+): \{", trecho, re.MULTILINE))
    assert ids == set(modelo.MIDIAS)


def metodos_do_js():
    trecho = bloco(MODEL_JS, "export const METODOS_APAGAMENTO", "{", "}")
    metodos = {}
    for nome, corpo in re.findall(r"^  ([A-Z_]+): \{(.*?)^  \},", trecho,
                                  re.MULTILINE | re.DOTALL):
        lista = re.search(r"midias: \[([^\]]*)\]", corpo)
        metodos[nome] = set(re.findall(r"'(\w+)'", lista.group(1))) if lista else set()
    return metodos


def teste_os_metodos_de_apagamento_sao_os_mesmos():
    assert set(metodos_do_js()) == set(modelo.METODOS_APAGAMENTO)


@pytest.mark.parametrize("metodo", sorted(modelo.METODOS_APAGAMENTO))
def teste_cada_metodo_vale_nas_mesmas_midias(metodo):
    """
    É a tabela que decide se um atestado destrói o dado de fato. Se a tela
    oferecesse "sobrescrita" para memória flash e o servidor recusasse, o
    operador tentaria concluir a triagem e não conseguiria — sem entender que a
    própria tela ofereceu uma opção impossível.
    """
    do_js = metodos_do_js()[metodo]
    do_py = modelo.METODOS_APAGAMENTO[metodo]["midias"]
    assert do_js == do_py, f"{metodo}: js={sorted(do_js)} python={sorted(do_py)}"


# --------------------------------------------------------------------------- #
# Código de rastreio
# --------------------------------------------------------------------------- #

def teste_o_alfabeto_do_codigo_e_o_mesmo():
    achado = re.search(r"const ALFABETO = '([^']+)'", MODEL_JS)
    assert achado.group(1) == modelo.ALFABETO


def teste_as_correcoes_de_leitura_sao_as_mesmas():
    achado = re.search(r"const CORRECOES = \{([^}]*)\}", MODEL_JS)
    pares = dict(re.findall(r"(\w+): '(\w+)'", achado.group(1)))
    assert pares == modelo.CORRECOES


def teste_o_prefixo_do_codigo_e_o_mesmo():
    achado = re.search(r"export const PREFIXO_CODIGO = '([^']+)'", MODEL_JS)
    assert achado.group(1) == modelo.PREFIXO


def teste_o_digito_verificador_usa_os_mesmos_pesos():
    """
    Compara a fórmula do peso, que é o coração do dígito. Não é execução do
    JavaScript — é a garantia mínima de que os dois lados não divergiram na
    conta enquanto não há Node para rodar o outro lado de verdade.
    """
    assert "corpo.length + 1 - i" in MODEL_JS
    assert "(len(corpo) + 1 - i)" in (RAIZ / "backend" / "modelo.py").read_text(encoding="utf-8")


# --------------------------------------------------------------------------- #
# Papéis (em js/store.js, não em js/model.js)
# --------------------------------------------------------------------------- #

def teste_os_papeis_sao_os_mesmos():
    trecho = bloco(STORE_JS, "export const PAPEIS", "{", "}")
    ids = set(re.findall(r"^\s{2}(\w+): \{", trecho, re.MULTILINE))
    assert ids == set(modelo.PAPEIS)


def teste_quem_escreve_na_cadeia_e_o_mesmo_dos_dois_lados():
    """
    `podeOperator` na tela e `PAPEIS_QUE_ESCREVEM` no servidor. Divergir aqui
    não abre brecha — o servidor continua sendo quem decide — mas faz a tela
    oferecer um botão que sempre devolve 403.
    """
    achado = re.search(r"podeOperar = \(usuario\) =>\s*(.+?);", STORE_JS, re.DOTALL)
    papeis_js = set(re.findall(r"=== '(\w+)'", achado.group(1)))
    assert papeis_js == modelo.PAPEIS_QUE_ESCREVEM


# --------------------------------------------------------------------------- #
# Pontos de coleta: o JSON semeado e o que a tela espera
# --------------------------------------------------------------------------- #

def teste_os_pontos_so_aceitam_categorias_conhecidas():
    """
    `dados/pontos.json` lista o que cada ponto aceita. Uma categoria escrita
    errada ali viraria um filtro que nunca casa, sem erro nenhum.
    """
    pontos = json.loads((RAIZ / "dados" / "pontos.json").read_text(encoding="utf-8"))
    aceitas = {c for p in pontos for c in p["aceita"]}
    desconhecidas = sorted(aceitas - set(modelo.CATEGORIAS))
    assert not desconhecidas, f"categorias em dados/pontos.json fora do modelo: {desconhecidas}"


def teste_os_itens_de_demonstracao_usam_etapas_e_categorias_conhecidas():
    itens = json.loads((RAIZ / "dados" / "itens-demo.json").read_text(encoding="utf-8"))
    for item in itens:
        assert item["categoria"] in modelo.CATEGORIAS, item["codigo"]
        assert modelo.normalizar_codigo(item["codigo"]) == item["codigo"], item["codigo"]
        for etapa, *_ in item["trilha"]:
            assert etapa in modelo.IDS_ETAPAS, (item["codigo"], etapa)


def teste_a_trilha_de_demonstracao_respeita_a_maquina_de_estados():
    """A carga não pode semear uma trilha que a própria API recusaria."""
    itens = json.loads((RAIZ / "dados" / "itens-demo.json").read_text(encoding="utf-8"))
    for item in itens:
        etapas = [e for e, *_ in item["trilha"]]
        assert etapas[0] == modelo.PRIMEIRA_ETAPA, item["codigo"]
        for atual, seguinte in zip(etapas, etapas[1:]):
            modelo.validar_transicao(atual, seguinte)
