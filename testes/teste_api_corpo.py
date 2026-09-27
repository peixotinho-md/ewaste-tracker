"""
Corpo da requisição que é JSON válido mas não é objeto.

`"x"`, `[1, 2]` e `42` são JSON legítimo, e `get_json() or {}` os deixava
passar até o primeiro `.get()` — que estourava em 500. Toda rota que lê corpo
passa por `corpo_json()` e responde 400, como a qualquer entrada malformada.
"""

import pytest

NAO_OBJETOS = ["x", [1, 2], 42, True]
ERRO = "O corpo da requisição precisa ser um objeto JSON."


@pytest.mark.parametrize("corpo", NAO_OBJETOS)
def teste_login_recusa_corpo_que_nao_e_objeto(cliente, corpo):
    resposta = cliente.post("/api/sessao", json=corpo)
    assert resposta.status_code == 400
    assert resposta.get_json()["erro"] == ERRO


@pytest.mark.parametrize("corpo", NAO_OBJETOS)
def teste_cadastro_recusa_corpo_que_nao_e_objeto(cliente, corpo):
    resposta = cliente.post("/api/usuarios", json=corpo)
    assert resposta.status_code == 400
    assert resposta.get_json()["erro"] == ERRO


@pytest.mark.parametrize("corpo", NAO_OBJETOS)
def teste_rotas_autenticadas_recusam_corpo_que_nao_e_objeto(
        cliente, fabricar_conta, entrar, corpo):
    admin = entrar(fabricar_conta("admin"))
    alvo = fabricar_conta("visitante")
    chamadas = [
        ("post", "/api/itens"),
        ("post", "/api/itens/MS-3H7K-P2R6/eventos"),
        ("post", "/api/sessao/senha"),
        ("patch", f"/api/admin/usuarios/{alvo['id']}"),
        ("delete", f"/api/admin/usuarios/{alvo['id']}"),
    ]
    for metodo, rota in chamadas:
        resposta = getattr(cliente, metodo)(rota, json=corpo)
        assert resposta.status_code == 400, (metodo, rota)
        assert resposta.get_json()["erro"] == ERRO, (metodo, rota)

    # Nada foi alterado: a conta do admin e a do alvo continuam de pé.
    assert cliente.get("/api/admin/usuarios").status_code == 200
    assert admin["id"] != alvo["id"]


def teste_corpo_ausente_continua_valendo_como_objeto_vazio(cliente):
    """Sem corpo, a rota reclama do campo que falta — e não do formato."""
    resposta = cliente.post("/api/sessao")
    assert resposta.status_code == 401
    assert resposta.get_json()["erro"] == "E-mail ou senha incorretos."
