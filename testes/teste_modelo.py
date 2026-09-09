"""
Regras de `backend/modelo.py`.

Este módulo não tem I/O, não importa Flask e não abre banco: é o alvo mais barato
e mais rentável da suíte, e roda sem nenhum fixture. Vários casos daqui são itens
do roteiro manual da seção 11.1 do Relatório Técnico virando verificação
automática.
"""

import pytest

import modelo

# --------------------------------------------------------------------------- #
# Transição de etapa
# --------------------------------------------------------------------------- #

# Parametrizado sobre IDS_ETAPAS, e não sobre uma lista escrita à mão: se alguém
# acrescentar uma sétima etapa, estes testes passam a cobri-la sozinhos.
#
# Repare no que isso NÃO faz: eles acompanham a lista, então acrescentar uma
# etapa não os faz falhar. Quem detecta a etapa nova é `teste_paridade_front.py`,
# comparando com `js/model.js` — verificado por mutação.
#
# O que estes casos cobrem e os testes de API não conseguem cobrir é a
# EXAUSTIVIDADE. Lá, cada teste percorre um caminho concreto, porque custa conta,
# banco e requisição; aqui, todos os pares saem de graça. A diferença aparece no
# defeito localizado — "retroceder liberado só de EM_TRIAGEM para COLETADO", o
# caso especial bem-intencionado que alguém acrescenta um dia. Foi medido: esse
# defeito passa por toda a suíte de API e só este bloco o pega.
PARES_SEGUIDOS = list(zip(modelo.IDS_ETAPAS, modelo.IDS_ETAPAS[1:]))


@pytest.mark.parametrize("atual,destino", PARES_SEGUIDOS)
def teste_avanco_de_uma_etapa_e_aceito(atual, destino):
    modelo.validar_transicao(atual, destino)


@pytest.mark.parametrize("etapa", modelo.IDS_ETAPAS)
def teste_repetir_a_etapa_atual_e_recusado(etapa):
    with pytest.raises(modelo.RegraViolada, match="já está"):
        modelo.validar_transicao(etapa, etapa)


@pytest.mark.parametrize("atual,destino", [(a, d) for d, a in PARES_SEGUIDOS])
def teste_retroceder_e_recusado(atual, destino):
    """Retroceder permitiria mascarar um extravio — é o motivo da regra existir."""
    with pytest.raises(modelo.RegraViolada, match="retroceder"):
        modelo.validar_transicao(atual, destino)


@pytest.mark.parametrize(
    "atual,destino",
    [(modelo.IDS_ETAPAS[i], modelo.IDS_ETAPAS[i + 2])
     for i in range(len(modelo.IDS_ETAPAS) - 2)],
)
def teste_pular_uma_etapa_e_recusado(atual, destino):
    with pytest.raises(modelo.RegraViolada, match="pular"):
        modelo.validar_transicao(atual, destino)


def teste_pular_da_primeira_a_ultima_e_recusado():
    with pytest.raises(modelo.RegraViolada, match="pular"):
        modelo.validar_transicao(modelo.PRIMEIRA_ETAPA, modelo.ETAPA_FINAL)


def teste_etapa_destino_desconhecida():
    with pytest.raises(modelo.RegraViolada, match="desconhecida"):
        modelo.validar_transicao("REGISTRADO", "TELEPORTADO")


def teste_etapa_atual_invalida():
    with pytest.raises(modelo.RegraViolada, match="sem etapa atual"):
        modelo.validar_transicao("SEI_LA", "COLETADO")


def teste_etapa_final_nao_avanca_para_lugar_nenhum():
    for destino in modelo.IDS_ETAPAS:
        with pytest.raises(modelo.RegraViolada):
            modelo.validar_transicao(modelo.ETAPA_FINAL, destino)


# --------------------------------------------------------------------------- #
# Código de rastreio e dígito verificador
# --------------------------------------------------------------------------- #

def teste_codigo_gerado_sobrevive_a_normalizacao():
    for _ in range(200):
        codigo = modelo.gerar_codigo()
        assert modelo.normalizar_codigo(codigo) == codigo


def teste_codigo_aceito_como_a_pessoa_digita():
    codigo = modelo.gerar_codigo()
    assert modelo.normalizar_codigo(codigo.replace("-", "")) == codigo
    assert modelo.normalizar_codigo(codigo.lower()) == codigo
    assert modelo.normalizar_codigo(f"  {codigo}  ") == codigo


def _trocas_de_um_caractere(codigo):
    """Todas as trocas de um caractere do código, com a posição alterada."""
    corpo = codigo.replace("-", "")[len(modelo.PREFIXO):]
    for posicao in range(len(corpo)):
        for substituto in modelo.ALFABETO:
            if substituto == corpo[posicao]:
                continue
            # A tabela de correções desfaz a troca antes da conferência: trocar
            # 0 por O não é um erro de digitação, é a leitura que o sistema
            # aceita de propósito.
            if modelo.CORRECOES.get(substituto) == corpo[posicao]:
                continue
            yield posicao, corpo[:posicao] + substituto + corpo[posicao + 1:]


def teste_erro_de_um_caractere_e_rejeitado_nas_posicoes_de_peso_impar():
    """
    Item 7 do roteiro manual: digitar o código com erro de um caractere.

    A garantia é PARCIAL, e o teste diz exatamente onde ela vale. O dígito é uma
    soma ponderada módulo 32, e os pesos são `len(corpo) + 1 - i` — ou seja
    8, 7, 6, 5, 4, 3, 2 para os sete caracteres do corpo. Um peso PAR divide 32,
    então existe uma troca cujo efeito na soma é múltiplo de 32 e passa
    despercebida; um peso ÍMPAR é coprimo com 32 e pega toda troca simples.

    Nas posições de peso ímpar, e no próprio dígito, a detecção é total.
    A posição de peso par é coberta pelo teste seguinte, que mede a brecha.
    """
    corpo_len = 7
    posicoes_impares = {i for i in range(corpo_len) if (corpo_len + 1 - i) % 2 == 1}

    for _ in range(50):
        codigo = modelo.gerar_codigo()
        for posicao, trocado in _trocas_de_um_caractere(codigo):
            if posicao in posicoes_impares or posicao == 7:
                assert modelo.normalizar_codigo(modelo.PREFIXO + trocado) is None, (
                    f"{codigo}: troca na posição {posicao} passou pelo dígito verificador"
                )


def teste_a_brecha_do_digito_verificador_esta_medida():
    """
    Registra o tamanho exato da brecha descrita no teste acima.

    Não é um teste de comportamento desejado — é um marco. Se alguém trocar os
    pesos por valores ímpares, a brecha vai a zero e este teste falha, avisando
    que a limitação foi fechada e que a documentação precisa acompanhar.
    """
    total = passaram = 0
    for _ in range(50):
        codigo = modelo.gerar_codigo()
        for _posicao, trocado in _trocas_de_um_caractere(codigo):
            total += 1
            if modelo.normalizar_codigo(modelo.PREFIXO + trocado) is not None:
                passaram += 1

    fracao = passaram / total
    # 4 das 8 posições têm peso par; em cada uma, das 31 trocas possíveis
    # algumas caem em múltiplo de 32. Medido: perto de 5%.
    assert 0.04 < fracao < 0.06, (
        f"{fracao:.2%} das trocas de um caractere passaram — o esperado hoje é "
        f"~5%. Se caiu para zero, os pesos foram corrigidos: atualize a seção "
        f"9.10 do Relatório Técnico e remova este teste."
    )


def teste_correcoes_de_leitura():
    """O, I, L e U não existem no alfabeto: são lidos como 0, 1, 1 e V."""
    corpo = "0" * 7
    codigo = modelo.formatar_codigo(corpo + modelo.digito_verificador(corpo))
    assert modelo.normalizar_codigo(codigo.replace("0", "O")) == codigo


@pytest.mark.parametrize("entrada", [None, "", "  ", 0, "XX-1234-5678", "1234-5678"])
def teste_codigo_sem_prefixo_ou_vazio_e_rejeitado(entrada):
    assert modelo.normalizar_codigo(entrada) is None


@pytest.mark.parametrize("corpo", ["ABC", "ABCDEFGHI", "ABCDEF"])
def teste_codigo_com_comprimento_errado_e_rejeitado(corpo):
    assert modelo.normalizar_codigo(modelo.PREFIXO + corpo) is None


def teste_digito_verificador_recusa_caractere_fora_do_alfabeto():
    assert modelo.digito_verificador("ABCDEF@") is None


def teste_corpo_que_comeca_com_MS_continua_valido():
    """
    Regressão: `formatar_codigo` cortava um "MS" no início do corpo.

    Como o corpo é sorteado no alfabeto de 32 caracteres, ele começa com M e S
    uma vez a cada 1024 — e o código resultante ficava com 6 caracteres em vez
    de 8, sem passar por nenhuma validação depois. Isso era gravado como chave
    primária do item e impresso na etiqueta: o aparelho nascia sem rastreio, e
    de forma irreversível.
    """
    corpo = "MSABCDE"
    codigo = modelo.formatar_codigo(corpo + modelo.digito_verificador(corpo))
    assert codigo == "MS-MSAB-CDEN"
    assert modelo.normalizar_codigo(codigo) == codigo


def teste_todo_codigo_gerado_e_reconhecido():
    """A geração e a validação precisam concordar sempre, não quase sempre."""
    for _ in range(3000):
        codigo = modelo.gerar_codigo()
        assert modelo.normalizar_codigo(codigo) == codigo, codigo


# --------------------------------------------------------------------------- #
# Peso
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("categoria,media", sorted(modelo.CATEGORIAS.items()))
def teste_peso_ausente_cai_na_media_da_categoria(categoria, media):
    assert modelo.normalizar_peso(None, categoria) == media
    assert modelo.normalizar_peso("", categoria) == media
    assert modelo.normalizar_peso("   ", categoria) == media


def teste_peso_valido_e_arredondado():
    assert modelo.normalizar_peso("1.23456", "notebook") == 1.235
    assert modelo.normalizar_peso(2, "notebook") == 2.0


@pytest.mark.parametrize("peso", ["abc", "11kg", [], {}])
def teste_peso_presente_e_invalido_e_recusado(peso):
    """Substituir em silêncio pela média daria por bom um erro de digitação."""
    with pytest.raises(modelo.RegraViolada, match="Peso inválido"):
        modelo.normalizar_peso(peso, "notebook")


@pytest.mark.parametrize("peso", [0, -1, "0", "-2.5"])
def teste_peso_nao_positivo_e_recusado(peso):
    with pytest.raises(modelo.RegraViolada, match="maior que zero"):
        modelo.normalizar_peso(peso, "notebook")


def teste_peso_acima_do_teto_e_recusado():
    with pytest.raises(modelo.RegraViolada, match="acima do limite"):
        modelo.normalizar_peso(modelo.PESO_MAXIMO_KG + 0.1, "notebook")
    # A fronteira exata passa.
    assert modelo.normalizar_peso(modelo.PESO_MAXIMO_KG, "notebook") == modelo.PESO_MAXIMO_KG


@pytest.mark.parametrize("peso", [float("nan"), float("inf"), float("-inf")])
def teste_peso_nao_finito_e_recusado(peso):
    with pytest.raises(modelo.RegraViolada, match="Peso inválido"):
        modelo.normalizar_peso(peso, "notebook")


def teste_categoria_invalida():
    with pytest.raises(modelo.RegraViolada, match="Categoria"):
        modelo.validar_categoria("nave")
    assert modelo.validar_categoria("notebook") == "notebook"


# --------------------------------------------------------------------------- #
# Atestado de apagamento
#
# Aqui a arquitetura do hardware vira regra de negócio: o que destrói o dado
# depende de como a mídia guarda o bit.
# --------------------------------------------------------------------------- #

def teste_sobrescrita_em_flash_e_recusada():
    """Wear leveling deixa cópias em blocos que o endereço lógico não alcança."""
    with pytest.raises(modelo.RegraViolada, match="wear leveling"):
        modelo.validar_apagamento("notebook", "flash", "SOBRESCRITA")


def teste_desmagnetizacao_em_flash_e_recusada():
    """Em flash o bit é carga elétrica presa numa célula, não orientação magnética."""
    with pytest.raises(modelo.RegraViolada, match="degausser"):
        modelo.validar_apagamento("notebook", "flash", "DESMAGNETIZACAO")


@pytest.mark.parametrize("metodo", ["SECURE_ERASE", "CRIPTO_ERASE", "DESTRUICAO_FISICA"])
@pytest.mark.parametrize("midia", ["magnetica", "flash"])
def teste_metodos_que_valem_nas_duas_midias(midia, metodo):
    assert modelo.validar_apagamento("notebook", midia, metodo) == (midia, metodo)


@pytest.mark.parametrize("metodo", ["SOBRESCRITA", "DESMAGNETIZACAO"])
def teste_metodos_magneticos_valem_em_disco(metodo):
    assert modelo.validar_apagamento("hd", "magnetica", metodo) == ("magnetica", metodo)


def teste_categoria_sem_midia_dispensa_o_atestado():
    assert modelo.validar_apagamento("cabos", None, None) == ("sem_midia", "NAO_APLICAVEL")
    assert not modelo.exige_apagamento("cabos")
    assert modelo.exige_apagamento("celular")


def teste_nao_aplicavel_em_aparelho_com_midia_e_recusado():
    with pytest.raises(modelo.RegraViolada, match="informe como ela foi destruída"):
        modelo.validar_apagamento("celular", "sem_midia", "NAO_APLICAVEL")


@pytest.mark.parametrize("midia", [None, "fita", ""])
def teste_midia_invalida(midia):
    with pytest.raises(modelo.RegraViolada, match="tipo de mídia"):
        modelo.validar_apagamento("notebook", midia, "SECURE_ERASE")


def teste_metodo_invalido():
    with pytest.raises(modelo.RegraViolada, match="como os dados"):
        modelo.validar_apagamento("notebook", "flash", "MARTELADA")


# --------------------------------------------------------------------------- #
# Papéis, senha e campos livres
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("papel", sorted(modelo.PAPEIS))
def teste_papeis_conhecidos_sao_aceitos(papel):
    assert modelo.validar_papel(papel) == papel


@pytest.mark.parametrize("papel", ["root", "", None, "Admin"])
def teste_papel_invalido(papel):
    with pytest.raises(modelo.RegraViolada, match="Papel inválido"):
        modelo.validar_papel(papel)


def teste_quem_escreve_na_cadeia():
    assert modelo.pode_escrever("operador")
    assert modelo.pode_escrever("admin")
    assert not modelo.pode_escrever("visitante")
    assert not modelo.pode_escrever(None)


@pytest.mark.parametrize("email", [
    "maria@teste.ms", "a@b.co", "nome.sobrenome@sub.dominio.com.br",
])
def teste_email_valido_e_aceito(email):
    assert modelo.validar_email(email) == email


@pytest.mark.parametrize("email", [
    "semarroba", "sem@dominio", "@teste.ms", "", None, "a b@teste.ms",
    "dois@@teste.ms", "maria@teste .ms",
])
def teste_email_invalido_e_recusado(email):
    """
    Mesmo padrão de `js/store.js`. Uma expressão regular não decide se a caixa
    existe — o que ela evita é o erro de digitação óbvio, e é preciso que a tela
    e o servidor recusem o mesmo conjunto, senão um aceita o que o outro nega.
    """
    with pytest.raises(modelo.RegraViolada, match="E-mail inválido"):
        modelo.validar_email(email)


def teste_email_e_limpo_nas_pontas():
    assert modelo.validar_email("  maria@teste.ms  ") == "maria@teste.ms"


@pytest.mark.parametrize("senha", ["", "12345", None])
def teste_senha_curta_e_recusada(senha):
    with pytest.raises(modelo.RegraViolada, match="ao menos 6"):
        modelo.validar_senha(senha)


def teste_senha_na_fronteira_dos_seis_caracteres():
    assert modelo.validar_senha("123456") == "123456"


@pytest.mark.parametrize("campo,limite", sorted(modelo.LIMITES.items()))
def teste_texto_respeita_o_limite_do_campo(campo, limite):
    assert len(modelo.texto("x" * (limite + 50), campo)) == limite


def teste_texto_limpa_as_pontas_e_aceita_ausencia():
    assert modelo.texto("  Dell Latitude  ", "marca") == "Dell Latitude"
    assert modelo.texto(None, "marca") == ""
    assert modelo.texto(0, "marca") == ""
