"""
Competência por etapa (RF21): registra a próxima etapa quem está com o aparelho.

Duas camadas, verificadas aqui pela API, que é onde valem:

1. O TIPO do ponto diz que tipo de organização registra cada etapa
   (`modelo.COMPETENCIA`): o ecoponto não registra a reciclagem.
2. A POSSE diz qual ponto: o do último evento, ou o destino para onde ele
   encaminhou o aparelho. Um ecoponto não registra a coleta de um aparelho
   entregue em outro; uma recicladora não registra a reciclagem de um lote
   despachado para outra.

Antes disso, o operador de um ecoponto registrava "Processado" de um aparelho
que nunca saiu de lá, e o certificado saía assinado por quem não reciclou nada.
"""

import json
from pathlib import Path

import pytest

import banco
import modelo

ECO_NORTE = "pt-cg-eco-norte"
ECO_SUL = "pt-cg-eco-sul"
COOP = "pt-cg-coop-reviver"
PEV = "pt-cg-shopping"
RECICLADORA = "pt-cg-recicladora"

#: Um ponto de cada tipo, da base de demonstração.
PONTO_DO_TIPO = {
    "ecoponto": ECO_NORTE,
    "cooperativa": COOP,
    "fabricante": "pt-cg-loja-tec",
    "pev": PEV,
    "recicladora": RECICLADORA,
}

#: O caminho mais curto pela cadeia: tudo no ecoponto até o despacho.
CAMINHO = {
    "COLETADO": (ECO_NORTE, None),
    "EM_TRIAGEM": (ECO_NORTE, None),
    "EM_TRANSPORTE": (ECO_NORTE, RECICLADORA),
    "EM_RECICLAGEM": (RECICLADORA, None),
    "PROCESSADO": (RECICLADORA, None),
}

APARELHO = {"categoria": "cabos", "marca": "Teste", "pesoKg": 0.3}


def registrar(cliente, ponto_entrega=ECO_NORTE):
    corpo = {**APARELHO, "pontoOrigemId": ponto_entrega} if ponto_entrega else APARELHO
    resposta = cliente.post("/api/itens", json=corpo)
    assert resposta.status_code == 201, resposta.get_json()
    return resposta.get_json()["codigo"]


def levar_ate(codigo, etapa_final):
    """Avança o item pelo banco seguindo `CAMINHO`, sem depender da API."""
    conexao = banco.conectar()
    try:
        for etapa in modelo.IDS_ETAPAS[1:modelo.IDS_ETAPAS.index(etapa_final) + 1]:
            ponto, destino = CAMINHO[etapa]
            banco.registrar_evento(
                conexao, codigo, etapa=etapa, ponto_id=ponto, destino_id=destino,
                responsavel="Preparo do teste", observacao="",
            )
    finally:
        conexao.close()


def avancar(cliente, codigo, etapa, **corpo):
    return cliente.post(f"/api/itens/{codigo}/eventos", json={"etapa": etapa, **corpo})


def etapa_atual(cliente, codigo):
    return cliente.get(f"/api/itens/{codigo}/rastreio").get_json()["item"]["etapaAtual"]


@pytest.fixture
def como(fabricar_conta, entrar):
    """Entra como operador do ponto pedido. Cada ponto, uma conta só."""
    contas = {}

    def _como(ponto_id):
        if ponto_id not in contas:
            contas[ponto_id] = fabricar_conta("operador", ponto_id=ponto_id)
        return entrar(contas[ponto_id])
    return _como


# --------------------------------------------------------------------------- #
# A tabela de tipos
# --------------------------------------------------------------------------- #

def teste_toda_etapa_depois_do_registro_tem_quem_registre():
    assert list(modelo.COMPETENCIA) == modelo.IDS_ETAPAS[1:]
    for etapa, tipos in modelo.COMPETENCIA.items():
        assert tipos, f"{etapa} ficaria sem ninguém que a registre"
        assert set(tipos) <= set(modelo.TIPOS_PONTO), etapa


def teste_so_a_recicladora_emite_o_certificado():
    """O certificado é a afirmação mais forte do sistema; tem um dono só."""
    assert modelo.COMPETENCIA["EM_RECICLAGEM"] == ("recicladora",)
    assert modelo.COMPETENCIA["PROCESSADO"] == ("recicladora",)


MATRIZ = [(tipo, etapa) for tipo in modelo.TIPOS_PONTO for etapa in modelo.COMPETENCIA]


@pytest.mark.parametrize("tipo,etapa", MATRIZ, ids=[f"{t}-{e}" for t, e in MATRIZ])
def teste_a_matriz_de_tipos(tipo, etapa):
    if tipo in modelo.COMPETENCIA[etapa]:
        modelo.validar_competencia(etapa, tipo, "Ponto")
    else:
        with pytest.raises(modelo.SemCompetencia):
            modelo.validar_competencia(etapa, tipo, "Ponto")


def teste_o_tipo_e_conferido_pela_api(cliente, visitante, como):
    """Item na recicladora, operador do ecoponto: recusa pelo tipo."""
    codigo = registrar(cliente)
    levar_ate(codigo, "EM_TRANSPORTE")
    como(ECO_NORTE)
    resposta = avancar(cliente, codigo, "EM_RECICLAGEM")
    assert resposta.status_code == 403
    assert resposta.get_json()["competencia"] is True
    assert "recicladora credenciada" in resposta.get_json()["erro"]


# --------------------------------------------------------------------------- #
# Posse: só o ponto que está com o aparelho registra
# --------------------------------------------------------------------------- #

def teste_a_coleta_e_do_ponto_de_entrega(cliente, visitante, como):
    codigo = registrar(cliente, ponto_entrega=ECO_NORTE)

    como(ECO_SUL)
    recusada = avancar(cliente, codigo, "COLETADO")
    assert recusada.status_code == 403
    assert "Região Norte" in recusada.get_json()["erro"]
    assert etapa_atual(cliente, codigo) == "REGISTRADO"

    como(ECO_NORTE)
    assert avancar(cliente, codigo, "COLETADO").status_code == 201


def teste_aparelho_sem_ponto_de_entrega_e_coletado_por_quem_receber(cliente, visitante, como):
    """Ainda não está com ninguém: o primeiro ponto competente o recebe."""
    codigo = registrar(cliente, ponto_entrega=None)
    como(ECO_SUL)
    assert avancar(cliente, codigo, "COLETADO").status_code == 201


def teste_a_triagem_e_de_quem_coletou(cliente, visitante, como):
    codigo = registrar(cliente)
    levar_ate(codigo, "COLETADO")

    como(ECO_SUL)
    assert avancar(cliente, codigo, "EM_TRIAGEM").status_code == 403
    como(ECO_NORTE)
    assert avancar(cliente, codigo, "EM_TRIAGEM").status_code == 201


def teste_a_reciclagem_e_da_recicladora_de_destino(cliente, visitante, como, conexao):
    """Uma recicladora não registra o lote despachado para outra."""
    with banco.transacao(conexao):
        conexao.execute(
            "INSERT INTO pontos (id, nome, tipo, municipio, lat, lng, aceita) "
            "VALUES ('pt-outra-rec', 'Outra Recicladora', 'recicladora', "
            "'Campo Grande', -20.4, -54.6, '[]')"
        )
    codigo = registrar(cliente)
    levar_ate(codigo, "EM_TRANSPORTE")   # despachado para RECICLADORA

    como("pt-outra-rec")
    recusada = avancar(cliente, codigo, "EM_RECICLAGEM")
    assert recusada.status_code == 403
    assert "Cerrado Verde" in recusada.get_json()["erro"]

    como(RECICLADORA)
    assert avancar(cliente, codigo, "EM_RECICLAGEM").status_code == 201
    assert avancar(cliente, codigo, "PROCESSADO").status_code == 201


def teste_o_pev_coleta_e_encaminha(cliente, visitante, como):
    """PEV não faz triagem: precisa dizer para onde o aparelho segue."""
    codigo = registrar(cliente, ponto_entrega=PEV)
    como(PEV)

    sem_destino = avancar(cliente, codigo, "COLETADO")
    assert sem_destino.status_code == 400
    assert "Informe para onde o aparelho segue" in sem_destino.get_json()["erro"]

    aceita = avancar(cliente, codigo, "COLETADO", destinoId=COOP)
    assert aceita.status_code == 201
    assert aceita.get_json()["destinoId"] == COOP

    # Agora está com a cooperativa: o próprio PEV e o ecoponto não registram.
    assert avancar(cliente, codigo, "EM_TRIAGEM").status_code == 403
    como(ECO_NORTE)
    assert avancar(cliente, codigo, "EM_TRIAGEM").status_code == 403
    como(COOP)
    assert avancar(cliente, codigo, "EM_TRIAGEM").status_code == 201


def teste_o_ecoponto_pode_encaminhar_a_triagem(cliente, visitante, como):
    codigo = registrar(cliente)
    como(ECO_NORTE)
    assert avancar(cliente, codigo, "COLETADO", destinoId=COOP).status_code == 201
    assert avancar(cliente, codigo, "EM_TRIAGEM").status_code == 403
    como(COOP)
    assert avancar(cliente, codigo, "EM_TRIAGEM").status_code == 201


# --------------------------------------------------------------------------- #
# O destino do encaminhamento
# --------------------------------------------------------------------------- #

def teste_transporte_sem_destino_e_recusado(cliente, visitante, como):
    codigo = registrar(cliente)
    levar_ate(codigo, "EM_TRIAGEM")
    como(ECO_NORTE)
    resposta = avancar(cliente, codigo, "EM_TRANSPORTE")
    assert resposta.status_code == 400
    assert "recicladora credenciada" in resposta.get_json()["erro"]


def teste_transporte_so_vai_para_recicladora(cliente, visitante, como):
    codigo = registrar(cliente)
    levar_ate(codigo, "EM_TRIAGEM")
    como(ECO_NORTE)
    resposta = avancar(cliente, codigo, "EM_TRANSPORTE", destinoId=COOP)
    assert resposta.status_code == 400
    assert "O destino precisa ser recicladora credenciada" in resposta.get_json()["erro"]


@pytest.mark.parametrize("etapa", ["EM_TRIAGEM", "EM_RECICLAGEM", "PROCESSADO"])
def teste_so_coleta_e_transporte_encaminham(cliente, visitante, como, etapa):
    codigo = registrar(cliente)
    anterior = modelo.IDS_ETAPAS[modelo.IDS_ETAPAS.index(etapa) - 1]
    levar_ate(codigo, anterior)
    como(CAMINHO[etapa][0])
    resposta = avancar(cliente, codigo, etapa, destinoId=COOP)
    assert resposta.status_code == 400
    assert "Só a coleta e o transporte" in resposta.get_json()["erro"]


def teste_destino_nao_pode_ser_o_proprio_ponto(cliente, visitante, como):
    codigo = registrar(cliente)
    como(ECO_NORTE)
    resposta = avancar(cliente, codigo, "COLETADO", destinoId=ECO_NORTE)
    assert resposta.status_code == 400
    assert "outro ponto" in resposta.get_json()["erro"]


def teste_destino_desconhecido_e_recusado(cliente, visitante, como):
    codigo = registrar(cliente)
    como(ECO_NORTE)
    resposta = avancar(cliente, codigo, "COLETADO", destinoId="pt-nao-existe")
    assert resposta.status_code == 400


def teste_a_recicladora_nao_e_ponto_de_entrega(cliente, visitante):
    """O aparelho nasceria sem ninguém que pudesse registrar a coleta."""
    resposta = cliente.post("/api/itens", json={**APARELHO, "pontoOrigemId": RECICLADORA})
    assert resposta.status_code == 400
    assert "não recebe aparelhos do público" in resposta.get_json()["erro"]


# --------------------------------------------------------------------------- #
# Quem escolhe o ponto
# --------------------------------------------------------------------------- #

def teste_a_maquina_de_estados_responde_antes_da_competencia(cliente, visitante, como):
    """Pular etapa continua sendo 400 com o motivo da transição, não 403."""
    codigo = registrar(cliente)
    como(ECO_SUL)
    resposta = avancar(cliente, codigo, "PROCESSADO")
    assert resposta.status_code == 400
    assert "pular" in resposta.get_json()["erro"]


def teste_operador_sem_ponto_nao_registra_nada(cliente, fabricar_conta, entrar, visitante):
    codigo = registrar(cliente)
    entrar(fabricar_conta("operador", ponto_id=None))
    resposta = avancar(cliente, codigo, "COLETADO", pontoId=ECO_NORTE)
    assert resposta.status_code == 403
    assert resposta.get_json()["competencia"] is True
    assert "vinculada a um ponto" in resposta.get_json()["erro"]


def teste_ponto_do_corpo_nao_muda_o_ponto_do_operador(cliente, visitante, como):
    """Se o corpo valesse, bastaria mandar o id do ponto que está com o aparelho."""
    codigo = registrar(cliente, ponto_entrega=ECO_NORTE)
    como(ECO_SUL)
    assert avancar(cliente, codigo, "COLETADO", pontoId=ECO_NORTE).status_code == 403


def teste_admin_registra_so_no_ponto_que_esta_com_o_aparelho(cliente, admin):
    codigo = registrar(cliente, ponto_entrega=ECO_NORTE)
    assert avancar(cliente, codigo, "COLETADO", pontoId=ECO_SUL).status_code == 403
    aceita = avancar(cliente, codigo, "COLETADO", pontoId=ECO_NORTE)
    assert aceita.status_code == 201
    assert aceita.get_json()["pontoId"] == ECO_NORTE


def teste_admin_sem_local_e_recusado(cliente, admin):
    """Um elo sem local não diz onde o aparelho estava nem quem o tinha."""
    codigo = registrar(cliente)
    resposta = avancar(cliente, codigo, "COLETADO")
    assert resposta.status_code == 400
    assert "Informe o ponto" in resposta.get_json()["erro"]


def teste_a_recusa_nao_deixa_rastro(cliente, visitante, como):
    codigo = registrar(cliente)
    levar_ate(codigo, "EM_TRANSPORTE")
    antes = cliente.get(f"/api/itens/{codigo}/rastreio").get_json()["eventos"]
    como(ECO_NORTE)
    avancar(cliente, codigo, "EM_RECICLAGEM")
    como("pt-cg-eco-sul")
    avancar(cliente, codigo, "EM_RECICLAGEM")
    depois = cliente.get(f"/api/itens/{codigo}/rastreio").get_json()["eventos"]
    assert depois == antes


# --------------------------------------------------------------------------- #
# Dados de demonstração e carga
# --------------------------------------------------------------------------- #

def teste_a_trilha_de_demonstracao_respeita_tipo_posse_e_destino():
    raiz = Path(modelo.__file__).resolve().parent.parent
    pontos = {p["id"]: p["tipo"] for p in
              json.loads((raiz / "dados" / "pontos.json").read_text(encoding="utf-8"))}
    itens = json.loads((raiz / "dados" / "itens-demo.json").read_text(encoding="utf-8"))
    for item in itens:
        local = item["pontoOrigemId"]
        for evento in item["trilha"][1:]:
            etapa, ponto = evento[0], evento[2]
            destino = evento[4] if len(evento) > 4 else None
            onde = f"{item['codigo']} {etapa}"
            assert modelo.pode_registrar(etapa, pontos[ponto]), f"{onde}: tipo {pontos[ponto]}"
            assert local in (None, ponto), f"{onde}: registrado em {ponto}, mas estava em {local}"
            modelo.validar_destino(etapa, pontos[ponto], pontos.get(destino), destino == ponto)
            local = destino or ponto


def teste_a_carga_cria_um_operador_em_cada_ponta_da_cadeia(bd):
    """Sem a conta da recicladora, a demonstração do ciclo dependeria do admin."""
    conexao = banco.conectar()
    try:
        linhas = conexao.execute(
            "SELECT p.tipo FROM usuarios u JOIN pontos p ON p.id = u.ponto_id "
            "WHERE u.papel = 'operador'"
        ).fetchall()
    finally:
        conexao.close()
    assert sorted(l["tipo"] for l in linhas) == ["ecoponto", "recicladora"]
