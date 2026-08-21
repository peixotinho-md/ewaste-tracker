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
