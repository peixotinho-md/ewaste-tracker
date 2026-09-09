"""
Administração de contas: papéis, exclusão e trilha de alterações.

As invariantes daqui são as que, se quebrarem, quebram em silêncio: um sistema
sem nenhum administrador continua respondendo normalmente até alguém precisar
administrar alguma coisa, e um cadastro que aceita o papel vindo do corpo só
aparece quando já é tarde.

A regra do "último admin" é verificada dentro da transação, com `BEGIN
IMMEDIATE` — ler e decidir na mesma transação é o que impede que dois pedidos
simultâneos rebaixem os dois últimos administradores, cada um enxergando o outro
ainda no lugar.
"""

import pytest

import banco
import modelo


def usuarios(cliente):
    return cliente.get("/api/admin/usuarios").get_json()


def por_email(cliente, email):
    return next(u for u in usuarios(cliente) if u["email"] == email)


# --------------------------------------------------------------------------- #
# O cadastro não escolhe o próprio papel
# --------------------------------------------------------------------------- #

def teste_cadastro_nasce_visitante_mesmo_pedindo_admin(cliente):
    """
    A defesa mais importante do arquivo: `criar_usuario` grava 'visitante'
    escrito no INSERT, e não o que veio no corpo. Sem isso, qualquer pessoa se
    tornaria administrador pelo formulário público de cadastro.
    """
    resposta = cliente.post("/api/usuarios", json={
        "nome": "Pessoa Comum",
        "email": "comum@teste.ms",
        "senha": "senha-boa",
        "papel": "admin",
    })
    assert resposta.status_code == 201
    assert resposta.get_json()["usuario"]["papel"] == "visitante"


def teste_cadastro_nao_escolhe_ponto_vinculado(cliente, primeiro_ponto):
    resposta = cliente.post("/api/usuarios", json={
        "nome": "Pessoa Comum",
        "email": "comum2@teste.ms",
        "senha": "senha-boa",
        "pontoId": primeiro_ponto["id"],
    })
    assert resposta.status_code == 201
    assert resposta.get_json()["usuario"]["pontoId"] is None


# --------------------------------------------------------------------------- #
# Promoção e rebaixamento
# --------------------------------------------------------------------------- #

def teste_admin_promove_visitante_a_operador(cliente, admin, fabricar_conta, primeiro_ponto):
    alvo = fabricar_conta("visitante")
    resposta = cliente.patch(f"/api/admin/usuarios/{alvo['id']}",
                             json={"papel": "operador", "pontoId": primeiro_ponto["id"]})
    assert resposta.status_code == 200
    assert resposta.get_json()["papel"] == "operador"
    assert resposta.get_json()["pontoId"] == primeiro_ponto["id"]


def teste_papel_invalido_e_recusado(cliente, admin, fabricar_conta):
    alvo = fabricar_conta("visitante")
    resposta = cliente.patch(f"/api/admin/usuarios/{alvo['id']}", json={"papel": "root"})
    assert resposta.status_code == 400
    assert "Papel inválido" in resposta.get_json()["erro"]


def teste_patch_sem_nada_a_alterar_e_recusado(cliente, admin, fabricar_conta):
    alvo = fabricar_conta("visitante")
    resposta = cliente.patch(f"/api/admin/usuarios/{alvo['id']}", json={})
    assert resposta.status_code == 400
    assert "Nada a alterar" in resposta.get_json()["erro"]


def teste_admin_nao_rebaixa_a_si_mesmo(cliente, admin):
    """Proteção contra o tiro no próprio pé, que é o caso mais comum."""
    resposta = cliente.patch(f"/api/admin/usuarios/{admin['id']}", json={"papel": "visitante"})
    assert resposta.status_code == 400
    assert "a si mesmo" in resposta.get_json()["erro"]


def teste_admin_rebaixa_outro_admin_enquanto_sobrar_um(cliente, fabricar_conta, entrar):
    """Rebaixar outro administrador é permitido — o que a regra impede é ficar sem nenhum."""
    outro = fabricar_conta("admin")
    entrar(fabricar_conta("admin"))
    resposta = cliente.patch(f"/api/admin/usuarios/{outro['id']}", json={"papel": "visitante"})
    assert resposta.status_code == 200
    assert resposta.get_json()["papel"] == "visitante"


def teste_rebaixar_operador_desfaz_o_vinculo_com_o_ponto(cliente, admin, fabricar_conta,
                                                         primeiro_ponto):
    """
    Papel sem escrita não guarda vínculo com ponto de coleta, e o desligamento
    entra na trilha: quem for auditar precisa ver que o vínculo caiu, e por quê.
    """
    alvo = fabricar_conta("operador", ponto_id=primeiro_ponto["id"])
    resposta = cliente.patch(f"/api/admin/usuarios/{alvo['id']}", json={"papel": "visitante"})
    assert resposta.status_code == 200
    assert resposta.get_json()["pontoId"] is None

    trilha = cliente.get(f"/api/admin/alteracoes?usuario={alvo['id']}").get_json()
    assert any(a["acao"] == "ponto" and a["de"] == primeiro_ponto["id"] for a in trilha)


def teste_ponto_inexistente_no_vinculo_e_recusado(cliente, admin, fabricar_conta):
    alvo = fabricar_conta("visitante")
    resposta = cliente.patch(f"/api/admin/usuarios/{alvo['id']}",
                             json={"papel": "operador", "pontoId": "pt-nao-existe"})
    assert resposta.status_code == 400
    assert "Ponto de coleta desconhecido" in resposta.get_json()["erro"]


def teste_desvincular_o_operador_do_ponto(cliente, admin, fabricar_conta, primeiro_ponto):
    """Ausente = não mexer; presente e vazio = desvincular."""
    alvo = fabricar_conta("operador", ponto_id=primeiro_ponto["id"])
    resposta = cliente.patch(f"/api/admin/usuarios/{alvo['id']}", json={"pontoId": ""})
    assert resposta.status_code == 200
    assert resposta.get_json()["pontoId"] is None


# --------------------------------------------------------------------------- #
# A regra do último admin, onde ela de fato é alcançável
#
# Pela API ela NÃO é: para a contagem de administradores restantes chegar a
# zero, o alvo tem de ser o próprio autor — e `app.py` recusa antes, com
# "você não pode rebaixar a si mesmo" e "não pode excluir a própria conta".
# A verificação em `banco.py` é defesa em profundidade: vale para qualquer
# chamada que não passe pelas rotas, como um comando de administração futuro.
# Por isso estes dois testes falam direto com a camada de dados, dentro da
# mesma transação `BEGIN IMMEDIATE` que serializa dois pedidos simultâneos.
# --------------------------------------------------------------------------- #

def _unico_admin(conexao):
    """Deixa exatamente um administrador no banco e o devolve."""
    admins = [u for u in banco.listar_usuarios(conexao) if u["papel"] == "admin"]
    assert admins, "a carga precisa criar ao menos um administrador"
    with banco.transacao(conexao):
        for extra in admins[1:]:
            conexao.execute("UPDATE usuarios SET papel = 'visitante' WHERE id = ?",
                            (extra["id"],))
    return banco.obter_usuario(conexao, admins[0]["id"])


def teste_o_ultimo_admin_nao_pode_ser_rebaixado(conexao):
    unico = _unico_admin(conexao)
    with pytest.raises(modelo.RegraViolada, match="única conta de administrador"):
        banco.atualizar_usuario(conexao, unico["id"], autor=unico, papel="operador")

    assert banco.obter_usuario(conexao, unico["id"])["papel"] == "admin"


def teste_o_ultimo_admin_nao_pode_ser_excluido(conexao):
    """
    Excluir o último administrador deixaria o sistema sem ninguém capaz de
    promover outro — e sem caminho de volta pela interface.
    """
    unico = _unico_admin(conexao)
    with pytest.raises(modelo.RegraViolada, match="única conta de administrador"):
        banco.excluir_usuario(conexao, unico["id"], autor=unico)

    assert banco.obter_usuario(conexao, unico["id"]) is not None


# --------------------------------------------------------------------------- #
# Senha redefinida por terceiro
# --------------------------------------------------------------------------- #

def teste_senha_redefinida_por_outro_nasce_provisoria(cliente, admin, fabricar_conta):
    """
    Enquanto quem definiu a senha não foi o dono, existe alguém além dele que
    conhece o segredo. A conta fica marcada até a troca.
    """
    alvo = fabricar_conta("visitante")
    assert alvo["senhaProvisoria"] is False

    resposta = cliente.patch(f"/api/admin/usuarios/{alvo['id']}", json={"senha": "senha-nova"})
    assert resposta.status_code == 200
    assert resposta.get_json()["senhaProvisoria"] is True


def teste_admin_que_troca_a_propria_senha_nao_fica_provisorio(cliente, admin):
    resposta = cliente.patch(f"/api/admin/usuarios/{admin['id']}", json={"senha": "senha-minha"})
    assert resposta.status_code == 200
    assert resposta.get_json()["senhaProvisoria"] is False


def teste_senha_curta_e_recusada_tambem_na_administracao(cliente, admin, fabricar_conta):
    alvo = fabricar_conta("visitante")
    resposta = cliente.patch(f"/api/admin/usuarios/{alvo['id']}", json={"senha": "123"})
    assert resposta.status_code == 400
    assert "ao menos 6" in resposta.get_json()["erro"]


# --------------------------------------------------------------------------- #
# Exclusão
# --------------------------------------------------------------------------- #

def teste_excluir_exige_a_senha_de_quem_exclui(cliente, admin, fabricar_conta):
    """
    A sessão pode estar aberta num computador que ficou sozinho no galpão, e
    esta é a única ação da tela que não tem volta. Senha errada é 403, e não o
    401 do login: a sessão continua válida, o que faltou foi a confirmação.
    """
    alvo = fabricar_conta("visitante")
    resposta = cliente.delete(f"/api/admin/usuarios/{alvo['id']}", json={"senha": "chute"})
    assert resposta.status_code == 403
    assert "não foi excluída" in resposta.get_json()["erro"]
    # E a conta continua lá.
    assert any(u["id"] == alvo["id"] for u in usuarios(cliente))


def teste_excluir_com_a_senha_certa(cliente, admin, fabricar_conta):
    alvo = fabricar_conta("visitante")
    resposta = cliente.delete(f"/api/admin/usuarios/{alvo['id']}", json={"senha": admin["senha"]})
    assert resposta.status_code == 200
    assert not any(u["id"] == alvo["id"] for u in usuarios(cliente))


def teste_admin_nao_exclui_a_propria_conta(cliente, admin):
    resposta = cliente.delete(f"/api/admin/usuarios/{admin['id']}", json={"senha": admin["senha"]})
    assert resposta.status_code == 400
    assert "própria conta" in resposta.get_json()["erro"]


def teste_excluir_conta_preserva_os_aparelhos_dela(cliente, fabricar_conta, entrar):
    """
    O que a conta declarou continua valendo: os aparelhos ficam cadastrados,
    com código e trilha intactos, e só perdem o dono. A cadeia de custódia não
    pode encolher porque alguém saiu do sistema.
    """
    dono = entrar(fabricar_conta("visitante"))
    item = cliente.post("/api/itens", json={"categoria": "celular"}).get_json()

    autor = entrar(fabricar_conta("admin"))
    resposta = cliente.delete(f"/api/admin/usuarios/{dono['id']}", json={"senha": autor["senha"]})
    assert resposta.status_code == 200
    assert resposta.get_json()["itensLiberados"] == 1

    rastreio = cliente.get(f"/api/itens/{item['codigo']}/rastreio").get_json()
    assert rastreio["item"]["codigo"] == item["codigo"]
    assert len(rastreio["eventos"]) == 1

    detalhados = cliente.get("/api/admin/itens").get_json()
    orfao = next(i for i in detalhados if i["codigo"] == item["codigo"])
    assert orfao["donoNome"] is None


# --------------------------------------------------------------------------- #
# Trilha de administração
# --------------------------------------------------------------------------- #

def teste_alteracoes_registram_autor_alvo_e_mudanca(cliente, admin, fabricar_conta):
    alvo = fabricar_conta("visitante")
    cliente.patch(f"/api/admin/usuarios/{alvo['id']}", json={"papel": "operador"})

    trilha = cliente.get("/api/admin/alteracoes").get_json()
    registro = next(a for a in trilha if a["alvoNome"] == alvo["nome"])
    assert registro["acao"] == "papel"
    assert registro["autorNome"] == admin["nome"]
    assert registro["de"] == "visitante"
    assert registro["para"] == "operador"


def teste_a_trilha_nao_devolve_os_ids_das_contas(cliente, admin, fabricar_conta):
    """
    A trilha identifica por NOME, e não por id.

    É o que permite que ela continue legível depois de a conta ser excluída — e
    é também o motivo de a resposta não trazer `alvoId`: o id de uma conta que
    não existe mais não diria nada a quem lê a tela.
    """
    alvo = fabricar_conta("visitante")
    cliente.patch(f"/api/admin/usuarios/{alvo['id']}", json={"papel": "operador"})

    trilha = cliente.get("/api/admin/alteracoes").get_json()
    assert trilha
    for registro in trilha:
        assert "alvoId" not in registro
        assert "autorId" not in registro


def teste_a_trilha_sobrevive_a_exclusao_da_conta(cliente, admin, fabricar_conta):
    """
    `alteracoes_conta` não tem chave estrangeira de propósito: uma trilha de
    auditoria que some junto com o auditado não serve para auditar nada.
    """
    alvo = fabricar_conta("visitante")
    cliente.patch(f"/api/admin/usuarios/{alvo['id']}", json={"papel": "operador"})
    cliente.delete(f"/api/admin/usuarios/{alvo['id']}", json={"senha": admin["senha"]})

    trilha = cliente.get("/api/admin/alteracoes").get_json()
    assert any(a["alvoNome"] == alvo["nome"] and a["acao"] == "papel" for a in trilha)
    assert any(a["alvoNome"] == alvo["nome"] and a["acao"] == "exclusao" for a in trilha)


def teste_alteracoes_filtram_por_usuario(cliente, admin, fabricar_conta):
    um = fabricar_conta("visitante")
    outro = fabricar_conta("visitante")
    cliente.patch(f"/api/admin/usuarios/{um['id']}", json={"papel": "operador"})
    cliente.patch(f"/api/admin/usuarios/{outro['id']}", json={"papel": "operador"})

    trilha = cliente.get(f"/api/admin/alteracoes?usuario={um['id']}").get_json()
    assert trilha
    assert {a["alvoNome"] for a in trilha} == {um["nome"]}


# --------------------------------------------------------------------------- #
# Lista de aparelhos da administração
# --------------------------------------------------------------------------- #

def teste_admin_ve_todos_os_aparelhos_identificados(cliente, fabricar_conta, entrar):
    dono = entrar(fabricar_conta("visitante"))
    item = cliente.post("/api/itens", json={"categoria": "notebook"}).get_json()

    entrar(fabricar_conta("admin"))
    detalhados = cliente.get("/api/admin/itens").get_json()
    achado = next(i for i in detalhados if i["codigo"] == item["codigo"])
    assert achado["donoNome"] == dono["nome"]
    assert achado["etapaAtual"] == modelo.PRIMEIRA_ETAPA
    assert achado["leituras"] == 1


def teste_reiniciar_demo_recria_o_banco(cliente, admin):
    cliente.post("/api/itens", json={"categoria": "celular"})
    resposta = cliente.post("/api/demo/reiniciar")
    assert resposta.status_code == 200
    # A sessão morre junto com o banco.
    assert cliente.get("/api/sessao").get_json()["usuario"] is None


# --------------------------------------------------------------------------- #
# A conta de reserva
#
# É a segunda chave do sistema: um administrador que não aparece na tela e que
# ninguém consegue alterar nem excluir por ela. Sem essa conta, perder a senha
# do único admin — ou um admin apagar todos os outros — deixaria o sistema sem
# volta, porque só um admin promove outro.
#
# O que se verifica aqui é o par que a torna útil: ela some da LISTA (senão
# seria o alvo mais óbvio) e as rotas de escrita a recusam (senão sumir da lista
# seria só cosmético, e um id descoberto por qualquer outro caminho bastaria).
# --------------------------------------------------------------------------- #

def _reserva(conexao):
    linha = conexao.execute(
        "SELECT * FROM usuarios WHERE reserva = 1"
    ).fetchone()
    assert linha is not None, "a carga precisa criar a conta de reserva"
    return linha


def teste_a_reserva_e_admin(conexao):
    assert _reserva(conexao)["papel"] == "admin"


def teste_a_sessao_da_reserva_se_identifica_como_tal(cliente, conexao):
    """
    A tela precisa deste campo para desenhar a marca d'água que acompanha a
    sessão da reserva. Sem ele, a conta de emergência seria indistinguível de
    um administrador comum — e a mais cômoda de usar, por não aparecer em lista
    nenhuma.
    """
    credencial = banco.redefinir_senha(conexao, banco.EMAIL_RESERVA)
    resposta = cliente.post("/api/sessao", json={
        "email": banco.EMAIL_RESERVA, "senha": credencial["senha"],
    })
    assert resposta.get_json()["usuario"]["reserva"] is True


def teste_conta_comum_nao_se_diz_reserva(cliente, fabricar_conta, entrar):
    conta = entrar(fabricar_conta("admin"))
    assert cliente.get("/api/sessao").get_json()["usuario"]["reserva"] is False
    assert conta["reserva"] is False


def teste_a_reserva_nao_aparece_na_lista_da_administracao(cliente, admin, conexao):
    listadas = {u["id"] for u in usuarios(cliente)}
    assert _reserva(conexao)["id"] not in listadas
    assert banco.EMAIL_RESERVA not in {u["email"] for u in usuarios(cliente)}


def teste_a_reserva_nao_pode_ser_alterada_por_id(cliente, admin, conexao):
    """
    Esconder da lista não basta: o id pode vir de um `PATCH` chutado, de um
    backup antigo ou de um log. A rota precisa recusar por conta própria.
    """
    resposta = cliente.patch(f"/api/admin/usuarios/{_reserva(conexao)['id']}",
                             json={"papel": "visitante"})
    assert resposta.status_code == 400
    assert "não encontrada" in resposta.get_json()["erro"]
    # E de fato não mudou nada.
    assert _reserva(conexao)["papel"] == "admin"


def teste_a_reserva_nao_pode_ser_excluida(cliente, admin, conexao):
    resposta = cliente.delete(f"/api/admin/usuarios/{_reserva(conexao)['id']}",
                              json={"senha": admin["senha"]})
    assert resposta.status_code == 400
    assert _reserva(conexao) is not None


def teste_o_erro_da_reserva_e_o_mesmo_de_uma_conta_inexistente(cliente, admin, conexao):
    """
    Uma mensagem própria ("essa conta não pode ser alterada") já contaria que a
    conta existe, que é justamente o que a reserva não pode revelar.
    """
    da_reserva = cliente.patch(f"/api/admin/usuarios/{_reserva(conexao)['id']}",
                               json={"papel": "visitante"})
    inexistente = cliente.patch("/api/admin/usuarios/u-nao-existe",
                                json={"papel": "visitante"})
    assert da_reserva.status_code == inexistente.status_code
    assert da_reserva.get_json() == inexistente.get_json()


def teste_a_reserva_nao_conta_como_o_ultimo_admin(conexao):
    """
    Se a reserva contasse, esta regra deixaria rebaixar o último administrador
    VISÍVEL — e a administração passaria a depender de uma conta que não aparece
    em tela nenhuma. A reserva é a saída de emergência, não o admin de serviço.
    """
    unico = _unico_admin(conexao)
    assert _reserva(conexao)["id"] != unico["id"]
    with pytest.raises(modelo.RegraViolada, match="única conta de administrador"):
        banco.atualizar_usuario(conexao, unico["id"], autor=unico, papel="operador")


def teste_a_reserva_continua_de_pe_sem_nenhum_admin_visivel(conexao):
    """O dia para o qual ela existe: a administração visível inteira se foi."""
    with banco.transacao(conexao):
        conexao.execute("UPDATE usuarios SET papel = 'visitante' WHERE reserva = 0")
    assert not [u for u in banco.listar_usuarios(conexao) if u["papel"] == "admin"]
    assert _reserva(conexao)["papel"] == "admin"


# --------------------------------------------------------------------------- #
# Recuperação de acesso pelo terminal
# --------------------------------------------------------------------------- #

def teste_nova_senha_devolve_o_acesso_perdido(cliente, conexao):
    """
    O caminho completo de quem perdeu a senha do admin: roda o comando, entra
    com o que ele imprimiu e é levado à troca de senha.
    """
    credencial = banco.redefinir_senha(conexao, "admin@etrilha.ms")
    resposta = cliente.post("/api/sessao",
                            json={"email": "admin@etrilha.ms", "senha": credencial["senha"]})
    assert resposta.status_code == 200
    # Lida no terminal por quem rodou o comando: ainda não identifica o dono.
    assert resposta.get_json()["usuario"]["senhaProvisoria"] is True


def teste_nova_senha_alcanca_a_reserva(cliente, conexao):
    credencial = banco.redefinir_senha(conexao, banco.EMAIL_RESERVA)
    resposta = cliente.post("/api/sessao",
                            json={"email": banco.EMAIL_RESERVA, "senha": credencial["senha"]})
    assert resposta.status_code == 200
    assert resposta.get_json()["usuario"]["papel"] == "admin"


def teste_nova_senha_de_conta_inexistente_e_recusada(conexao):
    with pytest.raises(modelo.RegraViolada, match="Não existe conta"):
        banco.redefinir_senha(conexao, "ninguem@etrilha.ms")


def teste_nova_senha_deixa_rastro_menos_para_a_reserva(conexao):
    """
    A redefinição pelo terminal entra na trilha como qualquer outra — exceto a
    da reserva, cujo NOME apareceria na tela de administração e denunciaria a
    conta que precisa não aparecer lá. O rastro dela é a linha impressa no
    terminal de quem rodou o comando.
    """
    banco.redefinir_senha(conexao, "admin@etrilha.ms")
    trilha = banco.listar_alteracoes(conexao)
    assert [a for a in trilha
            if a["acao"] == "senha" and a["autorNome"] == "terminal do servidor"]

    antes = len(trilha)
    banco.redefinir_senha(conexao, banco.EMAIL_RESERVA)
    assert len(banco.listar_alteracoes(conexao)) == antes
