# Credenciais de demonstração — e-Trilha MS

> **Não há senha escrita neste arquivo, e nunca deve haver.** Ele é versionado
> no Git: o que entra aqui vai junto para o repositório e fica no histórico,
> mesmo que seja apagado depois.
>
> As senhas das contas iniciais são **sorteadas na primeira execução** e
> aparecem **uma única vez, no terminal**. Não são gravadas em arquivo nenhum:
> o banco guarda apenas o hash PBKDF2, e o sorteio não se repete.

---

## Onde estão as senhas

Ao subir o servidor pela primeira vez (`python backend/app.py`), a carga cria
duas contas e sorteia uma senha para cada uma:

```
  Contas criadas agora, com senha sorteada:
    admin     admin@etrilha.ms       senha: ····················
    operador  operador@etrilha.ms    senha: ····················

  ANOTE AGORA. Elas não ficam salvas em lugar nenhum e não
  podem ser recuperadas — só trocadas em /admin, já autenticado.
```

**Anote no momento em que aparecem.** Fechar o terminal, ou deixar a saída rolar
para fora da janela, perde a senha para sempre.

| Papel | E-mail | Ponto vinculado |
|---|---|---|
| **Administrador** | `admin@etrilha.ms` | — (sem ponto fixo) |
| **Operador** | `operador@etrilha.ms` | Ecoponto Campo Grande — Região Norte |

Nas execuções seguintes nada é impresso: o banco guarda apenas o **hash
PBKDF2** e o sorteio não se repete. Já autenticado, dá para trocar a senha de
qualquer conta em `/admin`. Perdida a senha do admin, o único caminho é reiniciar
a demonstração — o que apaga junto tudo o que foi cadastrado nos testes.

**Por que sorteada, e não fixa no código:** senha escrita em `banco.py` vaza pelo
histórico do Git e continua valendo em toda instalação que copiar o projeto.

**Por que não gravada em arquivo:** um arquivo ao lado do banco vai junto quando
a pasta é copiada, compactada ou enviada — e ainda dá a falsa impressão de estar
guardado em segurança. Exibida e descartada, a senha existe enquanto alguém a
está lendo.

---

## O que cada conta abre

| | Consultar por código | Registrar aparelho | Ver os próprios aparelhos | Ler QR e avançar etapa | Administrar contas |
|---|---|---|---|---|---|
| Sem conta | sim | não | não | não | não |
| Visitante | sim | sim | só os dele | não | não |
| **Operador** | sim | sim | só os dele | **sim** | não |
| **Administrador** | sim | sim | só os dele | **sim** | **sim** |

A porta de entrada é a raiz do site (`/`): sem sessão ela oferece **entrar**,
**criar conta** ou **consultar um código**; com sessão, ela vira a home. A
consulta leva a `/rastrear`, a outra página pública, onde dá para escanear o QR
ou digitar o código. Toda outra página exige sessão, e o servidor nem entrega o
arquivo sem ela.

Nenhuma conta enxerga os aparelhos de outra pessoa: o painel de indicadores
mostra os números com os aparelhos **anonimizados** para conta comum, e vem
identificado só para operador e administrador, que precisam agir sobre um
aparelho específico.

---

## Roteiro da demonstração

**1. A porta de entrada.** Abra `http://localhost:8000`. A primeira tela
pergunta o que a pessoa quer fazer. Clique em *"Consultar um código de
rastreio"*, digite o código de um aparelho e mostre a trilha inteira e o
certificado **sem nenhum login**. Este é o contraste que fecha o argumento:
ler é de todos, escrever é de quem tem credencial.

**2. A barreira existe.** De volta ao início, tente abrir
`http://localhost:8000/registrar` direto pela URL. O servidor devolve a tela de
login — não é o JavaScript escondendo um botão.

**3. Como visitante.** Crie uma conta pela tela. Ela nasce como *visitante*:
registra e acompanha os próprios aparelhos. Registre um aparelho e mostre que
ele aparece em *Meus aparelhos*. Depois abra o painel: os números do estado
inteiro estão lá, mas a lista de pendências vem com os códigos substituídos por
uma referência — os aparelhos são de outras pessoas.

**4. Como operador:**

- o scanner abre com a faixa *"Operando como…"*, o local **travado** no ponto da
  conta e **sem campo de responsável** — quem assina é a conta, não o formulário;
- digite `MS-8VNC-5RQ1` (um HD já coletado) e clique em registrar: aparece a
  **tela de confirmação** com tudo o que será gravado. Cancele uma vez para
  mostrar que nada é gravado, e confirme na segunda;
- no bloco *"Testar a validação da máquina de estados"*, tente pular ou
  retroceder uma etapa: quem recusa é o servidor;
- abra o painel de novo: agora as pendências vêm com o código e o link.

**5. Como administrador:**

- o menu ganha **"Administração"**;
- a tela abre com **todos os aparelhos cadastrados** — código, etapa, ponto de
  entrada, dono e se o atestado de apagamento já saiu. Marque *"Só os
  atrasados"* para mostrar, em um clique, onde a cadeia travou;
- clique em **Abrir** numa conta: o painel dela sobe por cima da tela, que
  escurece atrás — dados, aparelhos, histórico, permissões e exclusão;
- promova a conta visitante criada no passo 3 a operador, vincule-a a um ponto e
  veja a mudança aparecer na **trilha de administração** logo abaixo;
- tente **excluir** uma conta: o sistema pede a *sua* senha de administrador
  antes. Os aparelhos dela continuam cadastrados, e a exclusão fica na trilha;
- tente rebaixar o próprio admin: é recusado, porque o sistema não pode ficar
  sem quem gerencie as contas.

---

## Contas criadas durante os testes

Toda conta criada pela tela nasce como **visitante**, e a senha fica guardada
apenas como hash PBKDF2 — não há como lê-la de volta, nem pelo administrador.

- **Esqueceu a senha de uma conta de teste?** Entre como admin, abra
  `/admin`, expanda *"Redefinir senha"* na linha da conta e defina uma nova.
- **Precisa de outro operador para a apresentação?** Crie a conta normalmente na
  tela inicial e promova-a em `/admin`. É justamente o fluxo que vale a pena
  mostrar para a banca.

---

## Reiniciar a demonstração

O botão **"Reiniciar demonstração"**, no painel, aparece só para administrador e
recria o banco do zero:

- os pontos de coleta e os 10 aparelhos de exemplo voltam ao estado inicial;
- **todas as contas são apagadas**, junto com os aparelhos que registraram;
- as contas iniciais renascem com **senhas novas, sorteadas**, impressas no
  **terminal do servidor** — não na tela do navegador.

Você é desconectado no processo, e a senha anterior deixou de existir. Tenha a
janela do terminal à vista **antes** de confirmar o reinício: é lá, e só lá, que
as credenciais novas aparecem. Elas não são enviadas para o navegador de
propósito — mandar senha pela rede contradiria o motivo de não gravá-la em
arquivo, e aqui ainda não há HTTPS.

Faça o reinício **antes** de montar o cenário da apresentação, não depois.

---

## Em uso real, o que ainda faltaria

Vale dizer isto na apresentação, se perguntarem:

- o primeiro administrador nasce na carga porque **só um admin promove outro** —
  não pode haver auto-promoção pela tela, ou o controle não valeria nada. Num
  sistema real, esse primeiro cadastro seria um comando de instalação, executado
  por quem opera o servidor;
- a senha sorteada deveria exigir **troca no primeiro acesso**;
- faltaria um comando de administração para **sortear uma senha nova sem
  recriar o banco** — hoje, quem perde a senha do admin perde junto os dados de
  teste;
- faltaria ainda **HTTPS**: sem ele a senha trafega em texto claro na rede. Em
  `localhost` isso não é problema porque nada sai da máquina — mas o servidor
  hoje aceita conexões da rede local, e aí a ressalva vale de verdade.
