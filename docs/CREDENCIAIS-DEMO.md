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

As contas iniciais e a **conta de reserva**, o que cada uma abre e como
recuperar uma senha perdida estão em um lugar só, no
[README](../README.md#contas-iniciais) — repetir as tabelas aqui já tinha
produzido duas versões diferentes da mesma informação.

O essencial para a apresentação: a carga cria `admin@etrilha.ms`,
`operador@etrilha.ms` e `reserva@etrilha.ms`, sorteia uma senha para cada e as
imprime **uma única vez, no terminal**. Anote no momento em que aparecem. Se
perder, `python backend/app.py --nova-senha <e-mail>` sorteia outra sem tocar
nos dados.

---

## O que cada conta abre

A tabela dos quatro papéis está na seção *Modelo de acesso* do
[Relatório Técnico](RELATORIO-TECNICO.md). Em uma linha: ler a trilha de um
código que se tem em mãos é público; registrar exige conta; ler QR e avançar
etapa exige operador; gerenciar contas exige administrador. Nenhuma conta
enxerga os aparelhos de outra.

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

**2b. Primeiro acesso.** Entre como `admin@etrilha.ms` com a senha sorteada. Em
vez do painel, aparece **"Defina uma senha sua para continuar"** — a senha
atual foi escolhida pela carga do sistema, e portanto não é só sua. Antes de
definir a nova, mostre que a trava é do servidor e não da tela: peça
`/api/painel` pelo terminal, com a sessão aberta, e ele responde 403. É o mesmo
argumento do item anterior, aplicado a um estado da conta em vez de a um papel.

A regra vale igual para uma conta cuja senha foi redefinida por um
administrador — e é o que você vai mostrar no passo 5.

**3. Como visitante.** Crie uma conta pela tela. Ela nasce como *visitante*:
registra e acompanha os próprios aparelhos. Repare que **não existe aba "Ler
QR"** no menu dela — e que abrir `/scanner` pela URL devolve para a home: quem
recusa é o servidor, não o menu.

- em `/registrar`, cadastre um notebook. O servidor devolve um código como
  `MS-7K3F-2QX9` e a tela desenha o QR. **"Ampliar para leitura"** abre o QR em
  tela cheia — dá para ler com a câmera de outro aparelho, sem imprimir nada;
- em `/registrar?imprimir`, pré-visualize a folha de etiquetas;
- em `/pontos`, filtre os pontos de coleta por município e por tipo de aparelho;
- em `/painel`, os números do estado inteiro estão lá, mas a lista de pendências
  vem com os códigos substituídos por uma referência — os aparelhos são de
  outras pessoas.

**4. Como operador:**

- o scanner abre com a faixa *"Operando como…"*, o local **travado** no ponto da
  conta e **sem campo de responsável** — quem assina é a conta, não o formulário;
- digite `MS-8VNC-5RQ1` (um HD já coletado) e clique em registrar: aparece a
  **tela de confirmação** com tudo o que será gravado. Cancele uma vez para
  mostrar que nada é gravado, e confirme na segunda;
- no bloco *"Testar a validação da máquina de estados"*, tente pular ou
  retroceder uma etapa: quem recusa é o servidor;
- ao concluir a **triagem** de um notebook, HD ou celular, aparece o **atestado
  de apagamento**. Escolha "memória flash" e tente "sobrescrita de setores": o
  servidor recusa e explica o *wear leveling* — é o argumento de Arquitetura de
  Computadores aplicado, e costuma ser o momento que a banca mais pergunta;
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
  sem quem gerencie as contas;
- **redefina a senha da conta visitante** criada no passo 3 e entre com ela: o
  sistema exige que ela defina uma senha própria antes de qualquer coisa. Você,
  que redefiniu, conhece a senha atual — é exatamente por isso que ela não serve
  como identidade. Redefinir a *própria* senha não dispara a exigência: quem
  escolheu foi quem vai usar.

**6. A recuperação de acesso.** É o passo que fecha o argumento do controle de
contas. No terminal, rode `python backend/app.py --nova-senha` (sem e-mail) e
entre com o que ele imprimir: a sessão abre com uma **marca d'água em todas as
telas** dizendo que aquela é a conta de reserva e só deve ser usada quando o
acesso ao admin se perder. Procure a conta na lista de `/admin`: ela **não está
lá**, e tentar alterá-la pelo id responde como se não existisse. Dali, redefina
a senha de `admin@etrilha.ms` e volte a usá-la.

O ponto a fazer: a reserva não é um administrador escondido para uso comum. Ela
não aparece na lista para não ser o alvo fácil de quem apagasse todos os admins
visíveis, mas tudo o que ela faz entra na trilha de administração como o de
qualquer conta — e a marca d'água existe para que ninguém se acostume com ela.

### Códigos já cadastrados

| Código | Situação |
|---|---|
| `MS-3H7K-P2R6` | Notebook — ciclo completo, com certificado |
| `MS-9QW2-4TXK` | Celular — ciclo completo, com certificado |
| `MS-5F8N-JD3Z` | Servidor — em reciclagem |
| `MS-2KJ6-8YVF` | Monitor — em triagem e **atrasado** (sem mídia de dados) |
| `MS-8VNC-5RQ1` | HD — coletado; a próxima etapa exige o atestado de apagamento |
| `MS-4WGR-7K2N` | Impressora — parada na coleta e **atrasada** |

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
- as três contas iniciais — incluindo a de reserva — renascem com **senhas
  novas, sorteadas**, impressas no **terminal do servidor**, não na tela do
  navegador.

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
- a **conta de reserva** e o `--nova-senha` resolvem a recuperação de acesso
  para um protótipo de uma máquina só. Num sistema real, a reserva seria uma
  credencial guardada em cofre, com uso alarmado — aqui o que ela deixa é a
  linha na trilha de administração e a marca d'água na tela de quem a usa;
- faltaria ainda **HTTPS**: sem ele a senha trafega em texto claro na rede. Em
  `localhost` isso não é problema porque nada sai da máquina — mas o servidor
  hoje aceita conexões da rede local, e aí a ressalva vale de verdade.
