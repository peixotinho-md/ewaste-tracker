"""
modelo.py — Regras de negócio que o SERVIDOR precisa impor.

Estas regras também existem em `js/model.js`, do lado do navegador, mas por
motivos diferentes:

  - no navegador, para dar resposta imediata ao usuário (boa experiência);
  - aqui, porque o servidor NÃO PODE CONFIAR NO CLIENTE. Qualquer pessoa
    consegue chamar a API direto, com curl ou pelo console do navegador,
    ignorando toda a validação da tela.

Por isso a duplicação é intencional: a tela valida para ajudar, o servidor
valida para valer. Só o que o servidor precisa impor está aqui — as tabelas de
composição material e os fatores de CO2e ficam apenas no front-end, porque são
usados para exibição e não para decidir se uma gravação é aceita.
"""

import re
import secrets

# --------------------------------------------------------------------------- #
# Etapas da cadeia de custódia
# --------------------------------------------------------------------------- #

ETAPAS = [
    {"id": "REGISTRADO",    "rotulo": "Registrado",    "sla_horas": 168},
    {"id": "COLETADO",      "rotulo": "Coletado",      "sla_horas": 72},
    {"id": "EM_TRIAGEM",    "rotulo": "Em triagem",    "sla_horas": 96},
    {"id": "EM_TRANSPORTE", "rotulo": "Em transporte", "sla_horas": 120},
    {"id": "EM_RECICLAGEM", "rotulo": "Em reciclagem", "sla_horas": 168},
    {"id": "PROCESSADO",    "rotulo": "Processado",    "sla_horas": None},
]

IDS_ETAPAS = [e["id"] for e in ETAPAS]
PRIMEIRA_ETAPA = IDS_ETAPAS[0]
ETAPA_FINAL = IDS_ETAPAS[-1]

ROTULOS = {e["id"]: e["rotulo"] for e in ETAPAS}


class RegraViolada(Exception):
    """Erro de regra de negócio. Vira HTTP 400 com a mensagem para o usuário."""


def validar_transicao(etapa_atual: str, etapa_destino: str) -> None:
    """
    Aceita apenas o passo imediatamente seguinte. Levanta RegraViolada caso
    contrário.

    Pular etapa apagaria a prova de que o aparelho passou pela triagem;
    retroceder permitiria mascarar um extravio. As duas coisas destruiriam o
    valor da cadeia de custódia, que é justamente ser confiável.
    """
    if etapa_destino not in IDS_ETAPAS:
        raise RegraViolada("Etapa desconhecida.")
    if etapa_atual not in IDS_ETAPAS:
        raise RegraViolada("Item sem etapa atual válida.")

    atual = IDS_ETAPAS.index(etapa_atual)
    destino = IDS_ETAPAS.index(etapa_destino)

    if destino == atual:
        raise RegraViolada(f'O item já está em "{ROTULOS[etapa_atual]}".')
    if destino < atual:
        raise RegraViolada(
            f'Não é possível retroceder de "{ROTULOS[etapa_atual]}" para '
            f'"{ROTULOS[etapa_destino]}". O histórico é somente de acréscimo.'
        )
    if destino > atual + 1:
        raise RegraViolada(
            f'Não é possível pular etapas: depois de "{ROTULOS[etapa_atual]}" '
            f'vem "{ROTULOS[IDS_ETAPAS[atual + 1]]}".'
        )


# --------------------------------------------------------------------------- #
# Categorias aceitas
# --------------------------------------------------------------------------- #

# Peso médio em kg, usado quando o cliente não informa um peso válido.
# A composição material completa fica no front-end (js/model.js).
CATEGORIAS = {
    "celular": 0.19,
    "notebook": 2.0,
    "desktop": 8.5,
    "monitor": 7.5,
    "impressora": 6.5,
    "servidor": 16.0,
    "hd": 0.55,
    "cabos": 0.3,
    "bateria": 0.12,
    "eletrodomestico": 12.0,
}

PESO_MAXIMO_KG = 500.0

# Categorias que carregam memória não volátil e, portanto, podem sair da casa
# ou da empresa com dados dentro. Multifuncionais entram na lista porque as
# corporativas guardam cópias digitalizadas em disco ou em memória flash interna.
CATEGORIAS_COM_MIDIA = {"celular", "notebook", "desktop", "servidor", "hd", "impressora"}


def validar_categoria(categoria: str) -> str:
    if categoria not in CATEGORIAS:
        raise RegraViolada("Categoria de aparelho inválida.")
    return categoria


def normalizar_peso(peso, categoria: str) -> float:
    """Peso ausente ou inválido cai no peso médio da categoria."""
    try:
        valor = float(peso)
    except (TypeError, ValueError):
        return CATEGORIAS[categoria]
    if not (0 < valor <= PESO_MAXIMO_KG):
        return CATEGORIAS[categoria]
    return round(valor, 3)


# --------------------------------------------------------------------------- #
# Apagamento seguro de mídias de dados
#
# Um aparelho descartado não carrega só metal: carrega dados. Apagar um arquivo
# ou formatar não destrói o conteúdo — só marca o espaço como livre. E a forma
# correta de destruir depende de COMO a mídia guarda o bit, o que é uma questão
# de arquitetura do hardware, não de software:
#
#   DISCO MAGNÉTICO (HDD)
#     O bit é a orientação magnética de uma região do prato, e o endereço lógico
#     corresponde a uma posição física estável. Sobrescrever o setor destrói o
#     dado anterior, e um campo magnético forte (desmagnetização) apaga o disco
#     inteiro de uma vez.
#
#   MEMÓRIA FLASH (SSD, NVMe, eMMC, cartão)
#     O bit é carga presa numa célula, e o endereço lógico NÃO corresponde a uma
#     célula fixa: a flash translation layer do controlador remapeia blocos
#     constantemente para distribuir o desgaste (wear leveling), e ainda mantém
#     uma reserva invisível ao sistema (over-provisioning). Consequências:
#       - sobrescrever pelo endereço lógico deixa cópias intactas nos blocos
#         remapeados, que o sistema operacional sequer consegue endereçar;
#       - desmagnetizar não faz absolutamente nada, porque não há magnetismo
#         guardando o dado.
#     O que funciona é o próprio controlador apagar (ATA Secure Erase / NVMe
#     Format), ou destruir a chave quando a mídia é autocriptografada.
#
# É por isso que as combinações abaixo são validadas: não é burocracia de
# formulário, é a diferença entre o dado estar destruído e apenas parecer que está.
# --------------------------------------------------------------------------- #

MIDIAS = {
    "magnetica": "Disco magnético (HDD)",
    "flash": "Memória flash (SSD, NVMe, eMMC, cartão)",
    "sem_midia": "Sem mídia de dados, ou já removida e destinada à parte",
}

# Para cada método, em quais mídias ele destrói o dado de fato.
METODOS_APAGAMENTO = {
    "SOBRESCRITA": {
        "rotulo": "Sobrescrita de todos os setores",
        "midias": {"magnetica"},
        "porque_nao": (
            "Sobrescrever pelo endereço lógico não alcança os blocos que o wear "
            "leveling remapeou nem a área de over-provisioning: em memória flash, "
            "restam cópias legíveis do dado."
        ),
    },
    "DESMAGNETIZACAO": {
        "rotulo": "Desmagnetização (degausser)",
        "midias": {"magnetica"},
        "porque_nao": (
            "Em memória flash o bit é carga elétrica presa numa célula, não "
            "orientação magnética. O degausser não tem efeito nenhum."
        ),
    },
    "SECURE_ERASE": {
        "rotulo": "ATA Secure Erase / NVMe Format (comando do controlador)",
        "midias": {"magnetica", "flash"},
        "porque_nao": "Método aplicável apenas a mídias de dados.",
    },
    "CRIPTO_ERASE": {
        "rotulo": "Destruição da chave de criptografia (mídia autocriptografada)",
        "midias": {"magnetica", "flash"},
        "porque_nao": "Método aplicável apenas a mídias de dados.",
    },
    "DESTRUICAO_FISICA": {
        "rotulo": "Destruição física (trituração da mídia)",
        "midias": {"magnetica", "flash"},
        "porque_nao": "Método aplicável apenas a mídias de dados.",
    },
    "NAO_APLICAVEL": {
        "rotulo": "Não aplicável — aparelho sem mídia de dados",
        "midias": {"sem_midia"},
        "porque_nao": "O aparelho tem mídia de dados: informe como ela foi destruída.",
    },
}


def exige_apagamento(categoria: str) -> bool:
    return categoria in CATEGORIAS_COM_MIDIA


def validar_apagamento(categoria: str, midia, metodo) -> tuple[str, str]:
    """
    Confere o atestado de apagamento e devolve (midia, metodo) validados.

    Levanta RegraViolada quando o método não destrói o dado naquela mídia — a
    validação existe justamente para impedir um atestado que parece correto e
    não é.
    """
    if not exige_apagamento(categoria):
        return ("sem_midia", "NAO_APLICAVEL")

    if midia not in MIDIAS:
        raise RegraViolada(
            "Informe o tipo de mídia de dados do aparelho antes de concluir a triagem."
        )
    definicao = METODOS_APAGAMENTO.get(metodo)
    if definicao is None:
        raise RegraViolada("Informe como os dados do aparelho foram destruídos.")

    if midia not in definicao["midias"]:
        raise RegraViolada(
            f'"{definicao["rotulo"]}" não destrói os dados em '
            f'{MIDIAS[midia].lower()}. {definicao["porque_nao"]}'
        )
    return (midia, metodo)


# --------------------------------------------------------------------------- #
# Código de rastreio com dígito verificador
# --------------------------------------------------------------------------- #

# Base32 sem I, L, O e U: são os caracteres que as pessoas confundem ao ler uma
# etiqueta suja ou riscada. Mesmo alfabeto usado em js/model.js.
ALFABETO = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
CORRECOES = {"O": "0", "I": "1", "L": "1", "U": "V"}


def digito_verificador(corpo: str) -> str | None:
    """Soma ponderada módulo 32, mesma ideia do CPF e do ISBN."""
    soma = 0
    for i, caractere in enumerate(corpo):
        if caractere not in ALFABETO:
            return None
        soma += ALFABETO.index(caractere) * (len(corpo) + 1 - i)
    return ALFABETO[soma % len(ALFABETO)]


def formatar_codigo(corpo: str) -> str:
    limpo = corpo[2:] if corpo.startswith("MS") else corpo
    return f"MS-{limpo[:4]}-{limpo[4:8]}"


def gerar_codigo() -> str:
    """7 caracteres sorteados criptograficamente + 1 dígito verificador."""
    corpo = "".join(secrets.choice(ALFABETO) for _ in range(7))
    return formatar_codigo(corpo + digito_verificador(corpo))


def normalizar_codigo(entrada) -> str | None:
    """
    Aceita o código como o usuário digitar (minúsculas, sem hífen, com O no
    lugar de 0) e devolve a forma canônica, ou None se for inválido.
    """
    if not entrada:
        return None
    bruto = re.sub(r"[^0-9A-Z]", "", str(entrada).upper())
    if bruto.startswith("MS"):
        bruto = bruto[2:]
    bruto = "".join(CORRECOES.get(c, c) for c in bruto)
    if len(bruto) != 8:
        return None
    if digito_verificador(bruto[:7]) != bruto[7]:
        return None
    return formatar_codigo(bruto)


# --------------------------------------------------------------------------- #
# Limites de tamanho dos campos livres
# --------------------------------------------------------------------------- #

LIMITES = {
    "marca": 80,
    "responsavel": 60,
    "observacao": 240,
    "nome": 60,
    "email": 120,
}


def texto(valor, campo: str) -> str:
    """Corta e limpa texto vindo do cliente, respeitando o limite do campo."""
    return str(valor or "").strip()[: LIMITES[campo]]
