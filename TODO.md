# TODO — e-Trilha MS

> **Os 14 itens estão implementados.** O arquivo fica como registro do que foi
> pedido e do porquê de cada decisão; pode ser removido quando o grupo achar
> melhor. Onde o código explicava a falta, o comentário saiu.
>
> Testes na seção 11 do [Relatório Técnico](docs/RELATORIO-TECNICO.md) —
> cenários 23 a 37 para os itens 1 a 3, e 45 a 59 para os itens 4 a 14.
>
> **Duas coisas ficaram em aberto**, as duas registradas nos itens
> correspondentes:
>
> - a pasta `backup/` (item 10): apagar libera 724 KB, mas perde a v1
>   só-front-end, que nunca foi commitada;
> - a interface móvel (item 13) foi ajustada por inspeção, sem teste em
>   aparelho real.

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

# 4. Limitar quantidade de caractére no registro de produto — FEITO

- EX: Não deixar ele digitar "11111111111", limitar em 3 dígitos, com o peso
  máximo sendo 500kg

**O defeito era maior do que o campo.** `maxlength` não vale em
`<input type="number">` — o atributo conta caracteres de texto, e o navegador não
trata o campo como texto —, então dava para digitar "11111111111". Pior: o
servidor **aceitava** e trocava em silêncio pelo peso médio da categoria
(`normalizar_peso`), dando por bom um número digitado errado.

- [x] Na tela, um `input` que corta a parte inteira em 3 dígitos enquanto a
      pessoa digita (`registrar.html`).
- [x] No servidor, `normalizar_peso` passou a **recusar** com HTTP 400: número
      inválido, zero, negativo e acima de 500 kg têm mensagens próprias. Peso
      *ausente* continua caindo no peso médio — é o caso de quem não tem balança.
- [x] `PESO_MAXIMO_KG` e `DIGITOS_PESO` ficam nomeados em `backend/modelo.py`,
      com o porquê do teto.

**Por que recusar em vez de corrigir:** o peso alimenta todo o cálculo de
material recuperado e de CO₂e evitado. Substituir o valor errado pela média
esconde o erro dentro de um indicador que a apresentação usa como resultado.

# 5. Primeira tela é a de log-in/registro do usuário, conta obrigatória — FEITO

**Como ficou:** `index.html` deixou de ser a home e virou a **porta de entrada**,
com três caminhos — *entrar*, *criar conta* e *consultar um código*. A home
antiga (números do estado, "como funciona", o problema) foi para `inicio.html`,
que só abre com sessão.

O terceiro caminho leva a `consultar.html`, tela nova e pública que faz uma
coisa só: escanear o QR ou receber o código digitado e abrir `rastrear.html`.
Ela não lista nada, não registra nada e não chama nenhuma rota que exija sessão
— e oferece entrar/criar conta para quem quiser mais do que consultar.

- [x] Páginas públicas reduzidas a três: `index.html`, `consultar.html` e
      `rastrear.html`. As demais o servidor **não entrega** sem sessão:
      `arquivo_raiz()` responde com um redirecionamento para
      `/?destino=<pagina>`, em vez de servir a página e deixar o JavaScript
      esconder o conteúdo depois.
- [x] `POST /api/itens` passou a exigir conta: registrar aparelho sem cadastro
      não existe mais.
- [x] Sumiu a figura do "visitante sem conta" que registrava e depois adotava os
      itens: a coluna `itens.visitante_id`, o índice dela,
      `adotar_itens_do_visitante()` e a sessão de visitante saíram
      (`PRAGMA user_version` foi para 5).
- [x] `conta.html` ficou só com a tela de quem entrou — os formulários de login
      e cadastro moram na porta de entrada agora.
- [x] O cabeçalho de `js/ui.js` some quando não há sessão: nas telas públicas,
      todo link do menu levaria a uma página fechada.
- [x] O Service Worker pré-carrega só as três páginas públicas — guardar a casca
      de uma página que não carrega dado nenhum offline não ajudaria ninguém.

**Por que a consulta continua sem login:** é a promessa do projeto. Quem entrega
um celular no ecoponto tem a etiqueta na mão, e exigir cadastro para ver onde o
aparelho está seria pedir conta justamente para entregar o que o sistema promete
de graça. Ler a trilha de um código que se tem em mãos é de todos; escrever nela
é de quem tem credencial.

# 6. Usuário comum só tem acesso aos seus produtos próprios, de ninguém mais — FEITO

**O que vazava:** `GET /api/itens` e `GET /api/eventos` eram públicas e
devolviam **tudo** — código, marca, o `donoId` de cada aparelho e o nome de quem
assinou cada etapa. `etiqueta.html` imprimia etiqueta de qualquer aparelho, não
só dos seus.

- [x] As duas rotas deixaram de existir. No lugar entrou `GET /api/painel`, que
      exige conta e devolve o recorte **anônimo** usado pelos indicadores: sem
      código, sem marca, sem dono, e sem `responsavel`/`observacao` nos eventos.
      Cada item recebe uma referência sequencial (`#0001`) que só vale dentro
      daquela resposta — serve para juntar evento e item e calcular tempos, não
      para abrir a trilha de ninguém.
- [x] Operador e admin recebem o painel identificado (`detalhado: true`): a
      lista de aparelhos parados além do prazo só vira ação se disser **qual**
      aparelho parou. Para conta comum, a tabela mostra a referência sem link e
      explica por quê.
- [x] `GET /api/meus-itens` filtra por `dono_id` vindo do cookie de sessão. O id
      do dono não é parâmetro de rota nem de consulta — não há chamada a montar
      para pedir "os itens do usuário X".
- [x] `item_json()` parou de expor `donoId`. A administração, que precisa do
      vínculo, continua usando `listar_itens_detalhados()`.
- [x] `etiqueta.html` imprime só os aparelhos da conta (o botão "Só os meus"
      perdeu o sentido e saiu).
- [x] `POST /api/demo/reiniciar` passou a exigir admin. Estava **aberta**:
      qualquer visitante podia apagar o banco inteiro no meio da apresentação.
- [x] O Service Worker não guarda mais `/api/painel`: a resposta muda conforme o
      papel, e uma cópia da versão identificada não pode sobrar no navegador
      para a próxima pessoa.

# 7. Na hora de buscar um produto pelo código, obrigar que os dois primeiros dígitos sejam MS — FEITO

- EX: MS-XXXX-XXXX

`normalizar_codigo` aceitava o código com ou sem o prefixo: `MS8VNC5RQ1` e
`8VNC5RQ1` levavam ao mesmo item. Agora o `MS` é obrigatório, nos dois lados
(`backend/modelo.py` e `js/model.js`), com a constante `PREFIXO` nomeando a regra.

- [x] Sem prefixo, o servidor responde HTTP 400 e a tela explica o formato.
- [x] As mensagens de erro passaram a dizer o que se espera —
      "começa com MS e tem 8 caracteres, como em MS-0000-0000" — em vez de só
      "código inválido".

**São duas verificações com papéis distintos:** o prefixo diz de qual sistema é
a etiqueta, e recusa de cara qualquer outra sequência de 8 caracteres que
apareça num QR; o dígito verificador diz se ela foi lida ou digitada direito.

# 8. Na URL tirar o .html ao abrir no navegador — FEITO

- EX: http://127.0.0.1:8000/registrar.html >> http://127.0.0.1:8000/registrar

- [x] `PAGINAS` em `backend/app.py` passou a nomear as páginas sem extensão, e
      `arquivo_raiz()` resolve `/registrar` para o arquivo `registrar.html`.
- [x] `/registrar.html` continua funcionando, mas **redireciona** para
      `/registrar`: link antigo e favorito não quebram, e a tela passa a ter um
      endereço só. O redirecionamento é 302, e não 301, porque um permanente
      ficaria gravado no navegador de quem abriu uma vez — e isto ainda é
      protótipo.
- [x] Todos os links internos, o `?destino=`, o menu (`js/ui.js`), o QR
      (`urlDeRastreio`), o `manifest.webmanifest` e a lista do Service Worker
      foram reescritos sem `.html`.

**Por quê, além da estética:** a extensão descreve como o arquivo está guardado
no disco, e isso não é assunto de quem digita o endereço. Trocar `.html` por
outra coisa amanhã não deveria quebrar link nenhum.

# 9. Painel Co2 — FEITO

- Deixar mais explícito de onde vem os dados usados para cálculo, e que vem da
  produção do metal

O painel mostrava o total de CO₂e sem responder à pergunta mais óbvia da banca:
**evitado em relação a quê?**

- [x] Bloco "De onde vem o número de CO₂e", em `painel.html`, dizendo que o
      total é a emissão da **produção primária do metal** — mineração e refino
      que deixam de ser necessários — e não economia de transporte ou de aterro.
- [x] A sequência do cálculo em três passos: peso registrado → composição média
      da categoria → fator de CO₂e por material → soma.
- [x] Tabela dos fatores **lida de `MATERIAIS`** (`js/model.js`), não repetida no
      texto: número na explicação divergindo do usado no cálculo seria pior que
      não explicar.
- [x] As constantes das equivalências (0,12 kg/km de carro; 22 kg/árvore/ano)
      saíram de dentro da função e viraram `EQUIVALENCIAS`, exportadas de
      `js/indicadores.js`, para a tela poder exibi-las.
- [x] Faixa dizendo que é **estimativa, não medição**, e o que seria preciso em
      uso real: base de inventário auditada e a balança da recicladora.
- [x] A mesma explicação, resumida, no certificado em `rastrear`.

# 10. Otimização, diminuir arquivos — FEITO (com uma decisão pendente)

Código morto removido, e não minificação: um protótipo acadêmico que a banca vai
ler não ganha nada sendo comprimido.

- [x] `GET /api/itens` e `GET /api/eventos` (rotas), `listar_itens()` e
      `listar_eventos()` (banco) — substituídos por `/api/painel`, item 6.
- [x] `GET /api/itens/<codigo>`: nenhuma tela chamava; quem precisa do aparelho
      usa `/rastreio`. Saiu a rota, o `store.obterItem()` e o padrão de cache
      correspondente no Service Worker. Uma rota pública a menos.
- [x] `adotar_itens_do_visitante()`, a coluna `itens.visitante_id` e o índice
      dela — sem sentido depois do item 5.
- [x] `gerarCodigo()`, `validarTransicao()` e `PRIMEIRA_ETAPA` em `js/model.js`:
      quem emite código e valida transição é o servidor. `digitoVerificador` e
      `formatarCodigo` deixaram de ser exportados — só `normalizarCodigo` os usa.
- [x] CSS: `.mono`, `.acoes` e `.aviso-info` não eram usados por tela nenhuma.
- [x] `GET /api/itens/<codigo>` e o `store.obterItem()` que ninguém chamava.
- [x] O botão "Só os meus" de `etiqueta` e o `style="width:auto"` que existia só
      para driblar o bug do item 14.

**Menos arquivos, e não só menos linhas:**

- [x] `js/geo-ms.js` (19 linhas, uma constante, um consumidor) foi para
      `js/model.js`, ao lado de `distanciaKm` — as duas coisas geográficas do
      sistema agora moram juntas.
- [x] `js/auth.js` foi para `js/store.js`. Era uma camada de passagem: metade
      comentário, o resto delegando para o `store`. A validação de formulário
      entrou em `cadastrarUsuario()` e os papéis viraram a seção "Papéis" no fim
      do arquivo.
- [x] `backend/_servidor.log` e `backend/__pycache__`, resíduos locais.

De **7 arquivos em `js/` para 5**, cada um com um trabalho claro: dados
(`store`), regras (`model`), indicadores, QR e interface (`ui`).

**Páginas: de 11 para 8.** Cada fusão junta dois estados da mesma tarefa, em
vez de duas tarefas diferentes:

- [x] `consultar` → `rastrear`. `consultar` só existia para receber um código e
      redirecionar — e `rastrear` já é pública e já tem o campo de código no
      topo. A câmera foi para um `<details>` fechado ali, e a leitura agora
      renderiza a trilha na própria página, sem o salto que existia antes.
- [x] `inicio` → `index`. A raiz decide pela sessão: sem conta mostra a porta de
      entrada, com conta mostra a home. É o mesmo momento da visita, e quem já
      entrou não tem o que fazer numa tela que só oferece entrar. O conteúdo da
      home não é protegido — os números vêm de `/api/painel`, que exige sessão —,
      então a rota pode ser pública sem abrir nada.
- [x] `etiqueta` → `registrar?imprimir`. O cadastro é o que produz a etiqueta, e
      a folha é onde ela vira papel; em páginas separadas era preciso atravessar
      o menu no meio de um fluxo só. Quem chega com `?imprimir&c=CÓDIGO` já
      encontra aquele aparelho marcado.
- [x] `/index` redireciona para `/`, pelo mesmo motivo de `/registrar.html`
      redirecionar para `/registrar`: um endereço por tela.

**Onde eu pararia:** juntar `indicadores.js` a `model.js` daria −1, mas criaria
um arquivo de ~590 linhas misturando regra de negócio com agregação. E juntar
`conta` com `admin`, ou `pontos` com `painel`, seria empilhar tarefas diferentes
num arquivo só — aí o que se ganha na contagem se perde na leitura, e a guarda
de sessão do servidor, que é por página, ficaria mais frouxa.

**Pendente, e é decisão do grupo:** a pasta `backup/` tem **724 KB** — a maior
massa do repositório depois de `vendor/` (308 KB, necessária). O `.gitignore`
diz que "o histórico do git já cumpre esse papel", **mas isso não é verdade**:
`git ls-files backup` não devolve nada, ou seja, a versão v1 só-front-end nunca
foi commitada e existe apenas nessa pasta. Apagar perde a v1 para sempre. As
saídas são commitar a v1 numa tag antes de apagar, ou deixar como está.

# 11. Arrumar a documentação — FEITO

- [x] `docs/CREDENCIAIS-DEMO.md` reescrito: parou de publicar senha e passou a
      explicar onde encontrá-la (item 12).
- [x] README — contas iniciais, seção nova sobre os endereços sem `.html`, seção
      sobre conta obrigatória × consulta pública, tabela da API corrigida,
      estrutura com `consultar` e `inicio`, tabela do modo offline refeita e
      limitações novas (peso declarado, CO₂e, interface móvel).
- [x] Relatório Técnico — RF12 reescrito e RF22 a RF25 acrescentados; seção 9.3
      (API, incluindo por que **não existe** `GET /api/itens`); 9.4 (modelo de
      dados sem `visitante_id`); 9.7 (autorização, com as duas decisões novas);
      9.9 (endereços e onde a sessão é conferida); 9.10 (prefixo `MS` e
      validação do peso); limitações 7 e 11; cenários de teste 45 a 59.

# 12. Admin user — FEITO

- Quando rodar pela primeira vez o site, se cria um admin genérico com senha
  aleatória mas com o e-mail do admin@etrilha.ms, evita a deixar senha e login
  em plain-text

**Como ficou:** `CONTAS_DEMO`, que trazia `etrilha-admin` e `etrilha-operador`
escritas em `backend/banco.py`, virou `CONTAS_INICIAIS` — só nome, e-mail e
papel. A senha é sorteada na carga com `secrets.token_urlsafe(12)` e mostrada
**uma única vez, no terminal**. Não é gravada em arquivo nenhum: o banco guarda
só o hash PBKDF2 e o sorteio não se repete.

- [x] `preparar()` devolve as credenciais quando a carga acontece, e `None`
      quando o banco já existia — nas execuções seguintes o terminal só aponta o
      arquivo, porque o banco guarda apenas o hash PBKDF2.
- [x] O reinício da demonstração sorteia senhas novas e as imprime **no terminal
      do servidor**, não na tela: mandar senha pela resposta HTTP contradiria o
      motivo de não gravá-la em arquivo, e aqui ainda não há HTTPS. A tela avisa
      onde procurar, e o diálogo de confirmação pede que a janela do terminal
      esteja à vista antes.
- [x] Nada de `credenciais-iniciais.txt`. Arquivo ao lado do banco vai junto
      quando a pasta é copiada ou compactada, e dá a falsa impressão de estar
      guardado em segurança.
- [x] `docs/CREDENCIAIS-DEMO.md` e o README pararam de publicar senha: agora
      explicam onde encontrá-la.

**Por que sorteada:** senha fixa no código vaza pelo histórico do Git — apagar
depois não adianta — e continua valendo em toda instalação que copiar o projeto.
Sorteada, ela existe só na máquina que rodou a carga.

**Ainda falta**, e vale dizer na apresentação: forçar a troca no primeiro acesso,
e um comando de administração que sorteie uma senha nova **sem recriar o banco**
(hoje, quem perde a senha do admin perde junto os dados de teste).

# 13. Arrumar UI para dispositivos móveis — FEITO (falta testar em aparelho real)

O `css/app.css` não tinha **nenhum** ponto de quebra: só havia `@media` para tema
escuro e para impressão. O que existia de responsivo vinha de `minmax()` nas
grades e de `flex-wrap`, o que resolve a largura mas não o resto.

- [x] Ponto de quebra em 640 px, com três problemas resolvidos e comentados:
      - **cabeçalho** — o menu de 6 itens quebrava em três linhas dentro de um
        cabeçalho fixo e comia metade da tela. Agora ocorre numa linha só, com
        rolagem horizontal, e marca e conta ficam na linha de cima;
      - **área de toque** — botões e campos com no mínimo 44 px de altura (um
        botão de 40 px é confortável no mouse e escorregadio no polegar), e
        botão ocupando a linha inteira;
      - **respiro** — margens e paddings menores, onde a largura é escassa.
- [x] Em paisagem no celular, o cabeçalho deixa de ser fixo: a tela já é baixa.
- [x] A caixa de seleção ficou **de fora** da regra de altura mínima — 44 px a
      esticariam de novo, que é exatamente o defeito do item 14.

**Falta:** abrir num telefone de verdade. A verificação foi por inspeção do
código; é justamente no celular que o sistema é usado de pé, num galpão.

# 14. Arrumar checkbox no painel de administração — FEITO

**Causa:** `css/app.css` tinha `input, select, textarea { width: 100% }`, que
alcançava também `input[type="checkbox"]`. A caixa "Só os atrasados" esticava
pela linha inteira e virava um retângulo enorme ao lado do rótulo. A tela de
etiquetas já convivia com o problema há tempos, com um `style="width:auto"`
inline para driblá-lo.

- [x] Regra própria para `input[type="checkbox"]` e `input[type="radio"]`:
      1,15 rem de lado (maior que o padrão, por causa do toque no celular),
      `flex: none` para não ser esticada por um container flex, e
      `accent-color` na cor do projeto.
- [x] O contorno inline de `etiqueta` saiu — a causa foi corrigida.
- [x] O rótulo virou a classe `.chip-caixa`, com altura mínima, em vez de
      `style="display:flex;..."` repetido no HTML.