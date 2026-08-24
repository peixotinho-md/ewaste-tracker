# Credenciais de demonstração — e-Trilha MS

> **Estas senhas são públicas e servem só para a demonstração.** Elas já estão
> escritas em `backend/banco.py` (`CONTAS_DEMO`) e são impressas no terminal
> toda vez que o servidor sobe. Não são segredo, e não devem ser reaproveitadas
> em nada que importe.
>
> **Nunca escreva neste arquivo uma senha de verdade.** Ele é versionado no Git:
> o que entra aqui vai junto para o repositório e fica no histórico, mesmo que
> seja apagado depois.

---

## Contas prontas ao subir o servidor

| Papel | E-mail | Senha | Ponto vinculado |
|---|---|---|---|
| **Administrador** | `admin@etrilha.ms` | `etrilha-admin` | — (sem ponto fixo) |
| **Operador** | `operador@etrilha.ms` | `etrilha-operador` | Ecoponto Campo Grande — Região Norte |

**O que cada uma abre:**

| | Consultar por código | Registrar o próprio aparelho | Ler QR e avançar etapa | Administrar contas |
|---|---|---|---|---|
| Sem conta | sim | sim | não | não |
| Visitante (conta criada pela tela) | sim | sim | não | não |
| **Operador** | sim | sim | **sim** | não |
| **Administrador** | sim | sim | **sim** | **sim** |

Entrar é sempre pela mesma tela: **`conta.html`** (link "Entrar" no canto
superior direito). Não há tela de login separada para operador ou admin — o que
muda é o que aparece depois de entrar.

---

## Roteiro da demonstração

**1. A barreira existe.** Ainda deslogado, clique em *"Sou operador: ler QR"* na
página inicial. A câmera não aparece: a tela explica que registrar uma etapa é
assinar uma declaração e leva ao login.

**2. Como operador** (`operador@etrilha.ms` / `etrilha-operador`):

- o scanner abre com a faixa *"Operando como…"*, o local **travado** no ponto da
  conta e **sem campo de responsável** — quem assina é a conta, não o formulário;
- digite `MS-8VNC-5RQ1` (um HD já coletado) e clique em registrar: aparece a
  **tela de confirmação** com tudo o que será gravado. Cancele uma vez para
  mostrar que nada é gravado, e confirme na segunda;
- no bloco *"Testar a validação da máquina de estados"*, tente pular ou
  retroceder uma etapa: quem recusa é o servidor.

**3. Como administrador** (`admin@etrilha.ms` / `etrilha-admin`):

- o menu ganha **"Administração"**;
- a tela abre com **todos os aparelhos cadastrados** — código, etapa, ponto de
  entrada, dono e se o atestado de apagamento já saiu. Marque *"Só os
  atrasados"* para mostrar, em um clique, onde a cadeia travou;
- clique em **Abrir** numa conta: o painel dela sobe por cima da tela, que
  escurece atrás — dados, aparelhos, histórico, permissões e exclusão;
- promova uma conta visitante a operador, vincule-a a um ponto e veja a mudança
  aparecer na **trilha de administração** logo abaixo;
- tente **excluir** uma conta: o sistema pede a *sua* senha de administrador
  antes. Os aparelhos dela continuam cadastrados, e a exclusão fica na trilha;
- tente rebaixar o próprio admin: é recusado, porque o sistema não pode ficar
  sem quem gerencie as contas.

**4. Consulta pública.** Abra `rastrear.html` numa janela anônima e consulte o
código: a trilha inteira e o certificado aparecem **sem login**. É o contraste
que fecha a demonstração — ler é de todos, escrever é de quem tem credencial.

---

## Contas criadas durante os testes

Qualquer conta criada pela tela `conta.html` nasce como **visitante** e **não
está listada aqui** — as senhas ficam guardadas apenas como hash PBKDF2, e não
há como lê-las de volta, nem pelo administrador.

Duas coisas úteis de saber:

- **Esqueceu a senha de uma conta de teste?** Entre como admin, abra
  `admin.html`, expanda *"Redefinir senha"* na linha da conta e defina uma nova.
- **Precisa de outro operador para a apresentação?** Crie a conta normalmente em
  `conta.html` e promova-a em `admin.html`. É justamente o fluxo que vale a pena
  mostrar para a banca.

---

## Reiniciar a demonstração

O botão **"Reiniciar demonstração"**, no painel, recria o banco do zero:

- os pontos de coleta e os 10 aparelhos de exemplo voltam ao estado inicial;
- as duas contas desta página são recriadas com as mesmas senhas;
- **todas as outras contas são apagadas**, junto com os aparelhos que elas
  registraram.

Ou seja: se o grupo criou contas para testar, elas somem no reinício. Faça o
reinício **antes** de montar o cenário da apresentação, não depois.

---

## Em uso real, nada disso valeria

Vale dizer isto na apresentação, se perguntarem:

- o primeiro administrador nasce na carga de demonstração porque **só um admin
  promove outro** — não pode haver auto-promoção pela tela, ou o controle não
  valeria nada. Num sistema real, esse primeiro cadastro seria um comando de
  instalação, executado por quem opera o servidor;
- as senhas seriam definidas por cada pessoa, com troca obrigatória no primeiro
  acesso;
- faltaria ainda **HTTPS**: sem ele a senha trafega em texto claro na rede. Em
  `localhost` isso não é problema porque nada sai da máquina.
