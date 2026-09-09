"""
Cadastro, login e troca de senha.

Este é o único arquivo que exercita o login de verdade, com `check_password_hash`.
O resto da suíte abre sessão gravando o cookie direto, porque PBKDF2 é lento de
propósito e pagá-lo em cada teste custaria a suíte inteira.
"""

import pytest

import banco

CADASTRO = {"nome": "Maria Silva", "email": "maria@teste.ms", "senha": "senha-boa"}


# --------------------------------------------------------------------------- #
# Cadastro
# --------------------------------------------------------------------------- #

def teste_cadastro_abre_a_sessao(cliente):
    resposta = cliente.post("/api/usuarios", json=CADASTRO)
    assert resposta.status_code == 201
    assert cliente.get("/api/sessao").get_json()["usuario"]["email"] == CADASTRO["email"]


def teste_quem_se_cadastra_escolhe_a_senha_e_nao_fica_provisorio(cliente):
    """
    Quem digita a própria senha é o único que a conhece — não há por que exigir
    a troca. O estado provisório existe só quando outra pessoa definiu o segredo.
    """
    resposta = cliente.post("/api/usuarios", json=CADASTRO)
    assert resposta.get_json()["usuario"]["senhaProvisoria"] is False


@pytest.mark.parametrize("email", ["semarroba", "sem@dominio", "", "@teste.ms"])
def teste_email_invalido_e_recusado(cliente, email):
    resposta = cliente.post("/api/usuarios", json={**CADASTRO, "email": email})
    assert resposta.status_code == 400
    assert "E-mail" in resposta.get_json()["erro"]


def teste_nome_vazio_e_recusado(cliente):
    resposta = cliente.post("/api/usuarios", json={**CADASTRO, "nome": "   "})
    assert resposta.status_code == 400
    assert "nome" in resposta.get_json()["erro"].lower()


def teste_senha_curta_e_recusada(cliente):
    resposta = cliente.post("/api/usuarios", json={**CADASTRO, "senha": "12345"})
    assert resposta.status_code == 400
    assert "ao menos 6" in resposta.get_json()["erro"]


def teste_email_repetido_e_recusado(cliente):
    assert cliente.post("/api/usuarios", json=CADASTRO).status_code == 201
    resposta = cliente.post("/api/usuarios", json=CADASTRO)
    assert resposta.status_code == 400


def teste_email_repetido_ignora_maiusculas(cliente):
    """A coluna é UNIQUE COLLATE NOCASE: Maria@ e maria@ são a mesma conta."""
    assert cliente.post("/api/usuarios", json=CADASTRO).status_code == 201
    resposta = cliente.post("/api/usuarios", json={**CADASTRO, "email": "MARIA@TESTE.MS"})
    assert resposta.status_code == 400


# --------------------------------------------------------------------------- #
# Login
# --------------------------------------------------------------------------- #

def teste_login_com_a_senha_certa(cliente, fabricar_conta):
    conta = fabricar_conta("visitante")
    resposta = cliente.post("/api/sessao", json={"email": conta["email"], "senha": conta["senha"]})
    assert resposta.status_code == 200
    assert resposta.get_json()["usuario"]["id"] == conta["id"]
    assert cliente.get("/api/sessao").get_json()["usuario"]["id"] == conta["id"]


def teste_login_ignora_maiusculas_e_espacos_no_email(cliente, fabricar_conta):
    conta = fabricar_conta("visitante")
    resposta = cliente.post(
        "/api/sessao",
        json={"email": f"  {conta['email'].upper()}  ", "senha": conta["senha"]},
    )
    assert resposta.status_code == 200


def teste_senha_errada_e_email_inexistente_dao_a_mesma_resposta(cliente, fabricar_conta):
    """
    Anti-enumeração: se a mensagem distinguisse os dois casos, bastaria tentar
    um e-mail para descobrir se ele tem conta no sistema.
    """
    conta = fabricar_conta("visitante")

    errada = cliente.post("/api/sessao", json={"email": conta["email"], "senha": "chute"})
    inexistente = cliente.post("/api/sessao", json={"email": "ninguem@teste.ms", "senha": "chute"})

    assert errada.status_code == inexistente.status_code == 401
    assert errada.get_json()["erro"] == inexistente.get_json()["erro"]


def teste_login_descarta_a_sessao_anterior(cliente, fabricar_conta):
    """
    Fixação de sessão: um identificador obtido por terceiros antes do login
    deixa de valer depois dele.
    """
    primeira = fabricar_conta("visitante")
    segunda = fabricar_conta("visitante")

    cliente.post("/api/sessao", json={"email": primeira["email"], "senha": primeira["senha"]})
    with cliente.session_transaction() as sessao:
        sessao["lixo-de-antes"] = "não deveria sobreviver"

    cliente.post("/api/sessao", json={"email": segunda["email"], "senha": segunda["senha"]})
    with cliente.session_transaction() as sessao:
        assert sessao["usuario_id"] == segunda["id"]
        assert "lixo-de-antes" not in sessao


def teste_sair_encerra_a_sessao(cliente, fabricar_conta, entrar):
    entrar(fabricar_conta("visitante"))
    assert cliente.delete("/api/sessao").status_code == 200
    assert cliente.get("/api/sessao").get_json()["usuario"] is None


def teste_a_sessao_nao_carrega_o_papel(cliente, fabricar_conta, entrar):
    """
    Só o id vai no cookie; o papel é relido do banco a cada requisição.

    É o que faz uma revogação valer na hora: se o papel viajasse assinado no
    cookie, um operador rebaixado continuaria escrevendo na cadeia de custódia
    até o cookie expirar.
    """
    conta = entrar(fabricar_conta("operador"))
    with cliente.session_transaction() as sessao:
        assert set(sessao.keys()) <= {"usuario_id", "_permanent"}
        assert sessao["usuario_id"] == conta["id"]


# --------------------------------------------------------------------------- #
# Troca de senha
# --------------------------------------------------------------------------- #

def teste_trocar_a_senha_e_entrar_com_a_nova(cliente, fabricar_conta, entrar):
    conta = entrar(fabricar_conta("visitante"))

    resposta = cliente.post("/api/sessao/senha",
                            json={"senhaAtual": conta["senha"], "senhaNova": "outra-senha"})
    assert resposta.status_code == 200

    cliente.delete("/api/sessao")
    assert cliente.post("/api/sessao",
                        json={"email": conta["email"], "senha": "outra-senha"}).status_code == 200
    assert cliente.post("/api/sessao",
                        json={"email": conta["email"], "senha": conta["senha"]}).status_code == 401


def teste_trocar_senha_exige_a_atual(cliente, fabricar_conta, entrar):
    """
    O cookie prova que alguém entrou, não que quem está no teclado agora é o
    dono. Numa máquina compartilhada, sem isto bastaria a sessão aberta para
    tomar a conta.
    """
    entrar(fabricar_conta("visitante"))
    resposta = cliente.post("/api/sessao/senha",
                            json={"senhaAtual": "chute", "senhaNova": "outra-senha"})
    assert resposta.status_code == 403
    assert "Senha atual incorreta" in resposta.get_json()["erro"]


def teste_senha_nova_igual_a_atual_e_recusada(cliente, fabricar_conta, entrar):
    """É justamente a atual que outra pessoa conhece."""
    conta = entrar(fabricar_conta("visitante", provisoria=True))
    resposta = cliente.post("/api/sessao/senha",
                            json={"senhaAtual": conta["senha"], "senhaNova": conta["senha"]})
    assert resposta.status_code == 400
    assert "diferente da atual" in resposta.get_json()["erro"]


def teste_senha_nova_curta_e_recusada(cliente, fabricar_conta, entrar):
    conta = entrar(fabricar_conta("visitante"))
    resposta = cliente.post("/api/sessao/senha",
                            json={"senhaAtual": conta["senha"], "senhaNova": "123"})
    assert resposta.status_code == 400
    assert "ao menos 6" in resposta.get_json()["erro"]


def teste_a_troca_encerra_o_estado_provisorio(cliente, fabricar_conta, entrar):
    conta = entrar(fabricar_conta("operador", provisoria=True))
    assert cliente.get("/api/painel").status_code == 403

    resposta = cliente.post("/api/sessao/senha",
                            json={"senhaAtual": conta["senha"], "senhaNova": "minha-senha"})
    assert resposta.status_code == 200
    assert cliente.get("/api/painel").status_code == 200


# --------------------------------------------------------------------------- #
# As contas criadas pela carga
# --------------------------------------------------------------------------- #

def teste_as_contas_iniciais_nascem_com_senha_provisoria(cliente, bd):
    """
    A senha sorteada na carga aparece uma vez no terminal — ou seja, quem subiu
    o servidor a conhece. Até a troca, a conta não prova quem a está usando.
    """
    assert bd.credenciais, "a carga precisa devolver as credenciais iniciais"

    for credencial in bd.credenciais:
        resposta = cliente.post("/api/sessao",
                                json={"email": credencial["email"], "senha": credencial["senha"]})
        assert resposta.status_code == 200, credencial["email"]
        assert resposta.get_json()["usuario"]["senhaProvisoria"] is True
        cliente.delete("/api/sessao")


def teste_a_carga_cria_um_admin_um_operador_e_a_reserva(bd):
    papeis = sorted(c["papel"] for c in bd.credenciais)
    assert papeis == ["admin", "admin", "operador"]

    reservas = [c for c in bd.credenciais if c["reserva"]]
    assert len(reservas) == 1, "a carga precisa criar exatamente uma reserva"
    assert reservas[0]["papel"] == "admin"
    assert reservas[0]["email"] == banco.EMAIL_RESERVA
