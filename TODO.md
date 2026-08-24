# TODO — e-Trilha MS

> **Os três itens abaixo estão implementados e verificados.** O arquivo fica
> como registro do que foi pedido e do porquê de cada decisão; pode ser
> removido quando o grupo achar melhor. Onde o código explicava a falta, o
> comentário saiu.
>
> Onde ficou:
>
> - login de operador — `backend/app.py` (decorador `exige`), `scanner.html`,
>   `conta.html`, coluna `papel` em `backend/schema.sql`;
> - confirmação da mudança de etapa — `confirmar()` em `js/ui.js` e
>   `confirmarRegistro()` em `scanner.html`;
> - administração de contas — `admin.html`, rotas `/api/admin/*`,
>   `atualizar_usuario()` em `backend/banco.py`, tabela `alteracoes_conta`.
>
> Testes na seção 11 do [Relatório Técnico](docs/RELATORIO-TECNICO.md),
> cenários 23 a 37.

## 1. Exigir login do operador antes de abrir o leitor de QR — FEITO

**Onde:** o botão "Sou operador: ler QR" em `index.html` (e o link "Abrir o leitor
de QR" em `registrar.html`) leva direto para `scanner.html`. Hoje `scanner.html`
abre para qualquer visitante, sem identificação.

**Problema:** quem lê a etiqueta é quem *escreve* na cadeia de custódia — cada
leitura grava um evento que declara "este aparelho passou por esta etapa, neste
ponto, com este responsável". Sem autenticação, qualquer pessoa pode:

- avançar a etapa de um aparelho que ela não recebeu;
- assinar o evento com o nome de outra pessoa (o campo "responsável" é digitado
  livremente);
- emitir o atestado de apagamento de dados sem ter destruído mídia nenhuma.

Isso derruba justamente a garantia que o projeto se propõe a dar. A consulta
pública por código continua sem conta — o que precisa de login é a **escrita**.

**O que fazer:**

- [x] Criar o perfil `operador` no cadastro de usuários (`usuarios` em
      `backend/schema.sql`), vinculado a um ponto de coleta (`pontos.id`).
- [x] Bloquear `scanner.html`: sem sessão de operador, redirecionar para
      `conta.html?destino=scanner.html` em vez de mostrar a câmera.
- [x] Exigir a sessão **no servidor**, não só na tela: `POST /api/itens/<codigo>/eventos`
      deve recusar com HTTP 401 quem não estiver autenticado como operador.
      A validação da tela é conveniência; a que vale é a do servidor, como já
      acontece com a máquina de estados.
- [x] Preencher `responsavel` a partir da sessão em vez de aceitar o texto
      digitado, para o nome no histórico ser o de quem de fato estava logado.
- [x] Restringir o `pontoId` do evento ao ponto do operador, evitando que ele
      registre passagem por um local onde não trabalha.
- [x] Ajustar o texto do botão na `index.html` para deixar claro que a área do
      operador pede login.

**Cuidado ao implementar:** o modo offline (Service Worker) hoje permite abrir
`scanner.html` sem rede. Com login obrigatório, definir o comportamento sem
conexão — o mais honesto é a tela avisar que o registro exige servidor, já que o
evento não pode ser gravado localmente sem quebrar a cadeia de custódia.

---

## 2. Tela de confirmação antes de gravar a mudança de etapa — FEITO

**Onde:** `scanner.html`, botão `#btn-avancar` (`ligarFormulario`). Hoje o clique
chama `store.registrarEvento` direto: um toque grava o evento.

**Problema:** o histórico é **append-only** — os gatilhos em `backend/schema.sql`
recusam `UPDATE` e `DELETE` na tabela `eventos`. Não existe desfazer. Um clique
errado, ou um QR lido por engano num galpão com dezenas de aparelhos, deixa marca
permanente na cadeia de custódia do item errado. E a etapa `EM_TRIAGEM` ainda
carrega junto o atestado de apagamento de dados, que é uma declaração séria.

**O que fazer:**

- [x] Interpor uma confirmação entre o clique e a gravação, mostrando **o que
      será gravado**, não um "tem certeza?" genérico:
      - código e categoria do aparelho, para pegar o QR trocado;
      - etapa atual → etapa nova;
      - local, responsável e observação como ficarão no histórico;
      - quando houver, mídia e método de apagamento declarados.
- [x] Deixar explícito na tela que o registro é definitivo e não pode ser
      desfeito, com o motivo (o histórico é somente de acréscimo).
- [x] Dois botões distintos — "Voltar e corrigir" e "Confirmar e registrar" —
      sem confirmação em botão perigoso por padrão de foco.
- [x] Evitar duplo envio: desabilitar o botão enquanto o `POST` está em curso.
- [x] Não usar `confirm()` do navegador: ele não cabe o resumo dos dados e é
      bloqueante. Reaproveitar o `.cartao` da própria página.

---

## 3. Login de administrador para gerenciar as contas — FEITO

**Onde:** não existe hoje. `conta.html` só trata da própria conta do usuário, e
`usuarios` em `backend/schema.sql` não tem coluna de papel.

**Problema:** operador é um privilégio de escrita na cadeia de custódia (item 1),
e não há como conceder nem revogar esse privilégio. Também não há quem redefina a
senha de um operador que a perdeu, nem quem confira quem são as contas existentes.

**O que fazer:**

- [x] Acrescentar a coluna `papel` em `usuarios` (`visitante` | `operador` |
      `admin`), com `visitante` como padrão, e subir `PRAGMA user_version` para
      que `preparar()` recrie o banco.
- [x] Criar a tela `admin.html`, acessível só com sessão de papel `admin`:
      - listar as contas com nome, e-mail, papel, data de criação e ponto
        vinculado;
      - alternar o papel da conta (promover a operador, rebaixar a visitante);
      - vincular o operador ao ponto de coleta onde ele atua;
      - redefinir a senha de uma conta.
- [x] Expor a API correspondente com verificação de papel **no servidor**
      (`GET /api/admin/usuarios`, `PATCH /api/admin/usuarios/<id>`), respondendo
      HTTP 403 a quem estiver logado sem ser admin. Como no item 1, a tela
      escondida não é proteção.
- [x] Nunca expor `senha_hash` na API, nem mesmo para o admin. A redefinição
      grava um hash novo (o `pbkdf2` já usado no cadastro); não existe leitura
      da senha.
- [x] Registrar quem alterou o quê e quando: promover alguém a operador é dar
      poder de escrever no histórico, e essa concessão também precisa de trilha.
- [x] Impedir que o último admin se rebaixe ou apague a si mesmo, para o sistema
      não ficar sem quem administre.
- [x] Criar o primeiro admin fora da tela — semente em `backend/banco.py` ou
      comando de linha —, já que não pode haver auto-promoção pela interface.

**Cuidado com o escopo:** e-mail e nome das contas são dados pessoais. O admin
precisa deles para operar, mas isso não vale para as demais telas — o painel
público e o rastreio devem continuar sem identificar pessoas.
