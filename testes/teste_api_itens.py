"""
Registro de aparelhos e a cadeia de custódia, pela API.

Cobre os itens 1, 3, 4 e 5 do roteiro manual da seção 11.1 do Relatório Técnico,
e mais as duas regras que o Relatório chama de "a assinatura não se falsifica":
o nome de quem assina e o ponto onde a leitura aconteceu vêm da SESSÃO, e o que
o cliente mandar nesses campos é descartado. São as regras mais fáceis de perder
numa refatoração, porque perdê-las não quebra nenhuma tela.
"""

import pytest

import modelo

APARELHO = {"categoria": "notebook", "marca": "Dell Latitude 3480", "pesoKg": 1.9}


def registrar(cliente, **campos):
    resposta = cliente.post("/api/itens", json={**APARELHO, **campos})
    assert resposta.status_code == 201, resposta.get_json()
    return resposta.get_json()


def avancar(cliente, codigo, etapa, **corpo):
    return cliente.post(f"/api/itens/{codigo}/eventos", json={"etapa": etapa, **corpo})


# Atestado que vale para um notebook (mídia flash apagada pelo controlador).
ATESTADO = {"apagamento": {"midia": "flash", "metodo": "SECURE_ERASE"}}


# --------------------------------------------------------------------------- #
# Registro
# --------------------------------------------------------------------------- #

def teste_registrar_gera_codigo_valido_e_primeira_etapa(cliente, visitante):
    """Item 1 do roteiro manual: registrar um notebook."""
    item = registrar(cliente)
    assert modelo.normalizar_codigo(item["codigo"]) == item["codigo"]
    assert item["etapaAtual"] == modelo.PRIMEIRA_ETAPA
    assert item["pesoKg"] == 1.9


def teste_registro_cria_o_evento_de_abertura(cliente, visitante):
    item = registrar(cliente)
    rastreio = cliente.get(f"/api/itens/{item['codigo']}/rastreio").get_json()
    assert [e["etapa"] for e in rastreio["eventos"]] == [modelo.PRIMEIRA_ETAPA]
    assert rastreio["eventos"][0]["responsavel"] == visitante["nome"]


def teste_peso_ausente_cai_na_media_da_categoria(cliente, visitante):
    item = registrar(cliente, pesoKg=None)
    assert item["pesoKg"] == modelo.CATEGORIAS["notebook"]


def teste_categoria_invalida_e_recusada(cliente, visitante):
    resposta = cliente.post("/api/itens", json={"categoria": "nave"})
    assert resposta.status_code == 400
    assert "Categoria" in resposta.get_json()["erro"]


def teste_ponto_de_origem_inexistente_e_recusado(cliente, visitante):
    resposta = cliente.post("/api/itens", json={**APARELHO, "pontoOrigemId": "pt-nao-existe"})
    assert resposta.status_code == 400
    assert "Ponto de coleta desconhecido" in resposta.get_json()["erro"]


def teste_o_dono_e_a_conta_da_sessao(cliente, visitante):
    """O id do dono nunca vem do cliente: sai do cookie, no servidor."""
    item = registrar(cliente)
    meus = cliente.get("/api/meus-itens").get_json()
    assert [i["codigo"] for i in meus] == [item["codigo"]]
    # E a resposta não devolve o dono para ninguém.
    assert "donoId" not in item


# --------------------------------------------------------------------------- #
# A cadeia de custódia inteira
# --------------------------------------------------------------------------- #

def teste_percorrer_as_seis_etapas_ate_o_certificado(cliente, fabricar_conta, entrar,
                                                     primeiro_ponto):
    """Item 3 do roteiro manual: ler o QR e avançar as seis etapas."""
    dono = entrar(fabricar_conta("visitante"))
    item = registrar(cliente)

    entrar(fabricar_conta("operador", ponto_id=primeiro_ponto["id"]))
    for etapa in modelo.IDS_ETAPAS[1:]:
        extra = ATESTADO if etapa == "EM_TRIAGEM" else {}
        resposta = avancar(cliente, item["codigo"], etapa, **extra)
        assert resposta.status_code == 201, (etapa, resposta.get_json())

    rastreio = cliente.get(f"/api/itens/{item['codigo']}/rastreio").get_json()
    assert rastreio["item"]["etapaAtual"] == modelo.ETAPA_FINAL
    assert [e["etapa"] for e in rastreio["eventos"]] == modelo.IDS_ETAPAS
    assert rastreio["apagamento"]["metodo"] == "SECURE_ERASE"
    assert dono["nome"]  # o registro continua assinado por quem registrou


def teste_pular_uma_etapa_e_recusado(cliente, operador):
    """Item 4 do roteiro manual."""
    item = registrar(cliente)
    resposta = avancar(cliente, item["codigo"], "EM_TRIAGEM")
    assert resposta.status_code == 400
    assert "pular" in resposta.get_json()["erro"]


def teste_retroceder_e_recusado(cliente, operador):
    """Item 5 do roteiro manual: retroceder permitiria mascarar um extravio."""
    item = registrar(cliente)
    assert avancar(cliente, item["codigo"], "COLETADO").status_code == 201
    resposta = avancar(cliente, item["codigo"], modelo.PRIMEIRA_ETAPA)
    assert resposta.status_code == 400
    assert "retroceder" in resposta.get_json()["erro"]


def teste_repetir_a_etapa_atual_e_recusado(cliente, operador):
    item = registrar(cliente)
    resposta = avancar(cliente, item["codigo"], modelo.PRIMEIRA_ETAPA)
    assert resposta.status_code == 400
    assert "já está" in resposta.get_json()["erro"]


def teste_evento_em_codigo_mal_formado_e_recusado(cliente, operador):
    """Dígito verificador errado: a etiqueta foi lida errado, não é código nosso."""
    resposta = avancar(cliente, "MS-0000-0001", "COLETADO")
    assert resposta.status_code == 400
    assert "inválido" in resposta.get_json()["erro"]


def teste_evento_em_codigo_valido_e_inexistente(cliente, operador):
    resposta = avancar(cliente, modelo.gerar_codigo(), "COLETADO")
    assert resposta.status_code == 400
    assert "não encontrado" in resposta.get_json()["erro"]


# --------------------------------------------------------------------------- #
# A assinatura não se falsifica
# --------------------------------------------------------------------------- #

def teste_responsavel_do_corpo_e_descartado(cliente, operador):
    """
    Se o nome viesse do formulário, qualquer operador assinaria o evento com o
    nome de outra pessoa — e a assinatura não provaria nada.
    """
    item = registrar(cliente)
    resposta = avancar(cliente, item["codigo"], "COLETADO", responsavel="Fulano Inventado")
    assert resposta.status_code == 201
    assert resposta.get_json()["responsavel"] == operador["nome"]
    assert resposta.get_json()["responsavel"] != "Fulano Inventado"


def teste_ponto_do_corpo_e_ignorado_quando_o_operador_tem_ponto(
    cliente, operador, primeiro_ponto, bd
):
    """O operador não registra passagem por um local onde não trabalha."""
    import banco

    conexao = banco.conectar()
    try:
        outro = [p for p in banco.listar_pontos(conexao) if p["id"] != primeiro_ponto["id"]][0]
    finally:
        conexao.close()

    item = registrar(cliente)
    resposta = avancar(cliente, item["codigo"], "COLETADO", pontoId=outro["id"])
    assert resposta.status_code == 201
    assert resposta.get_json()["pontoId"] == primeiro_ponto["id"]


def teste_admin_sem_ponto_fixo_informa_o_local(cliente, admin, primeiro_ponto):
    item = registrar(cliente)
    resposta = avancar(cliente, item["codigo"], "COLETADO", pontoId=primeiro_ponto["id"])
    assert resposta.status_code == 201
    assert resposta.get_json()["pontoId"] == primeiro_ponto["id"]


def teste_ponto_inexistente_no_evento_e_recusado(cliente, admin):
    item = registrar(cliente)
    resposta = avancar(cliente, item["codigo"], "COLETADO", pontoId="pt-nao-existe")
    assert resposta.status_code == 400
    assert "Ponto de coleta desconhecido" in resposta.get_json()["erro"]


# --------------------------------------------------------------------------- #
# Atestado de apagamento na triagem
# --------------------------------------------------------------------------- #

def levar_ate_a_triagem(cliente, codigo):
    assert avancar(cliente, codigo, "COLETADO").status_code == 201


def teste_triagem_sem_atestado_e_recusada(cliente, operador):
    item = registrar(cliente)
    levar_ate_a_triagem(cliente, item["codigo"])
    resposta = avancar(cliente, item["codigo"], "EM_TRIAGEM")
    assert resposta.status_code == 400
    assert "mídia" in resposta.get_json()["erro"]


def teste_sobrescrita_em_flash_e_recusada_pela_api(cliente, operador):
    """
    O wear leveling deixa cópias que o endereço lógico não alcança. É a
    contribuição de Arquitetura de Computadores virando recusa do servidor.
    """
    item = registrar(cliente)
    levar_ate_a_triagem(cliente, item["codigo"])
    resposta = avancar(
        cliente, item["codigo"], "EM_TRIAGEM",
        apagamento={"midia": "flash", "metodo": "SOBRESCRITA"},
    )
    assert resposta.status_code == 400
    assert "wear leveling" in resposta.get_json()["erro"]


def teste_aparelho_com_midia_nao_passa_como_sem_midia(cliente, operador):
    """
    Regressão: declarar "sem mídia / não aplicável" para um notebook passava, e
    era exatamente o atestado vazio que esta validação existe para impedir. Como
    a tabela `apagamentos` é somente de acréscimo, ficava gravado para sempre.
    """
    item = registrar(cliente)
    levar_ate_a_triagem(cliente, item["codigo"])
    resposta = avancar(
        cliente, item["codigo"], "EM_TRIAGEM",
        apagamento={"midia": "sem_midia", "metodo": "NAO_APLICAVEL"},
    )
    assert resposta.status_code == 400
    assert "tem mídia de dados" in resposta.get_json()["erro"]


def teste_aparelho_sem_midia_dispensa_o_atestado(cliente, operador):
    item = registrar(cliente, categoria="cabos", pesoKg=0.3)
    levar_ate_a_triagem(cliente, item["codigo"])
    resposta = avancar(cliente, item["codigo"], "EM_TRIAGEM")
    assert resposta.status_code == 201


def teste_a_triagem_recusada_nao_deixa_rastro(cliente, operador):
    """Ou o item avança com a declaração, ou não avança: é a mesma transação."""
    item = registrar(cliente)
    levar_ate_a_triagem(cliente, item["codigo"])
    avancar(cliente, item["codigo"], "EM_TRIAGEM",
            apagamento={"midia": "flash", "metodo": "SOBRESCRITA"})

    rastreio = cliente.get(f"/api/itens/{item['codigo']}/rastreio").get_json()
    assert rastreio["item"]["etapaAtual"] == "COLETADO"
    assert [e["etapa"] for e in rastreio["eventos"]] == [modelo.PRIMEIRA_ETAPA, "COLETADO"]
    assert rastreio["apagamento"] is None


# --------------------------------------------------------------------------- #
# Consulta pública
# --------------------------------------------------------------------------- #

def teste_rastreio_e_publico(cliente, visitante):
    """Item 6 do roteiro manual: consultar o código em janela anônima."""
    item = registrar(cliente)
    cliente.delete("/api/sessao")

    resposta = cliente.get(f"/api/itens/{item['codigo']}/rastreio")
    assert resposta.status_code == 200
    assert resposta.get_json()["item"]["codigo"] == item["codigo"]


def teste_rastreio_aceita_o_codigo_como_a_pessoa_digita(cliente, visitante):
    item = registrar(cliente)
    for forma in (item["codigo"].lower(), item["codigo"].replace("-", "")):
        assert cliente.get(f"/api/itens/{forma}/rastreio").status_code == 200


# Cuidado ao escolher um código "obviamente inválido": MS-0000-0000 NÃO serve,
# porque a soma ponderada de sete zeros é zero e o dígito verificador dela é o
# próprio "0" — o código é válido, só não existe no banco. Aqui é preciso um
# dígito de fato errado.
@pytest.mark.parametrize("codigo", ["MS-0000-0001", "MS-3H7K-P2R5", "nada", "ABC"])
def teste_rastreio_de_codigo_invalido(cliente, codigo):
    resposta = cliente.get(f"/api/itens/{codigo}/rastreio")
    assert resposta.status_code == 400
    assert "inválido" in resposta.get_json()["erro"]


def teste_rastreio_de_codigo_valido_e_inexistente(cliente):
    resposta = cliente.get(f"/api/itens/{modelo.gerar_codigo()}/rastreio")
    assert resposta.status_code == 404


# --------------------------------------------------------------------------- #
# Isolamento por dono
# --------------------------------------------------------------------------- #

def teste_uma_conta_nao_ve_os_aparelhos_de_outra(cliente, fabricar_conta, entrar):
    entrar(fabricar_conta("visitante"))
    meu = registrar(cliente)

    entrar(fabricar_conta("visitante"))
    outro = registrar(cliente)

    codigos = [i["codigo"] for i in cliente.get("/api/meus-itens").get_json()]
    assert codigos == [outro["codigo"]]
    assert meu["codigo"] not in codigos
