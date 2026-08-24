# e-Trilha MS — rastreamento de resíduos eletrônicos por QR Code

Protótipo do **DAC — Tecnologia em Análise e Desenvolvimento de Sistemas**
(Prof. Vitor Gabriel de Souza Farias, RF1440), Eixo 3 — Resíduos e Economia Circular.

**Equipe:** Rafael Dias (205220) · Vinicios Pereira (208618) · José Victor (204998)
· Eder Maciel (205969) · Renato Peixoto (205683)

---

## O que é

Quem entrega um celular velho num ecoponto **não tem como saber se ele foi mesmo
reciclado**. A Lei 12.305/2010 obriga a logística reversa de eletroeletrônicos,
mas o consumidor final não recebe nenhuma prova de destinação.

O e-Trilha MS fecha essa lacuna com uma ideia simples: **uma etiqueta QR colada
no aparelho**, lida a cada etapa da cadeia. O QR é o identificador físico que
acompanha o dispositivo mesmo onde não há internet; cada leitura acrescenta um
elo à cadeia de custódia:

```
REGISTRADO → COLETADO → EM_TRIAGEM → EM_TRANSPORTE → EM_RECICLAGEM → PROCESSADO
```

Ao final, é emitido um **certificado de destinação final**, consultável por
qualquer pessoa que tenha o código — sem login.

---

## Como executar

**1. Instalar a dependência** (uma vez só):

```powershell
cd C:\Users\rpalmeida\ewaste
python -m pip install -r requirements.txt
```

**2. Subir o servidor:**

```powershell
python backend/app.py
```

**3. Abrir <http://localhost:8000>**

O banco (`backend/etrilha.db`) é criado e populado automaticamente na primeira
execução, a partir de `dados/*.json`. As bibliotecas de QR já estão em
`vendor/` — não há build nem `npm install`.

### Contas de demonstração

A carga inicial cria duas contas, também impressas no terminal ao subir o
servidor:

| Papel | E-mail | Senha | O que pode |
|---|---|---|---|
| Administrador | `admin@etrilha.ms` | `etrilha-admin` | gerenciar contas e papéis, além de tudo do operador |
| Operador | `operador@etrilha.ms` | `etrilha-operador` | ler QR e registrar as etapas, pelo Ecoponto Região Norte |

Roteiro de apresentação com essas contas em
[docs/CREDENCIAIS-DEMO.md](docs/CREDENCIAIS-DEMO.md).

São credenciais **públicas, de demonstração**. O primeiro administrador nasce
aqui de propósito: como só um admin promove outro, não pode haver
auto-promoção pela tela — num sistema real esse primeiro cadastro seria um
comando de instalação.

Quem se cadastra pela tela nasce como **visitante**: registra e acompanha os
próprios aparelhos, mas não grava etapas na cadeia de custódia de terceiros.

> **Câmera:** só funciona em contexto seguro. Em `http://localhost` funciona.
> Pelo celular na rede local (`http://192.168.x.x`) o navegador bloqueia, porque
> HTTP puro não é contexto seguro — nesse caso use a digitação manual do código,
> disponível em todas as telas. Para a apresentação, use a webcam do notebook.

---

## Roteiro rápido de demonstração

1. **`registrar.html`** — cadastre um notebook. O servidor gera um código como
   `MS-7K3F-2QX9` e a tela desenha o QR Code correspondente.
   - **"Ampliar para leitura"** abre o QR em tela cheia: dá para ler com a
     câmera de outro aparelho, sem imprimir nada.
2. **`etiqueta.html`** — imprima (ou pré-visualize) a folha de etiquetas.
3. **`scanner.html`** — a tela pede login: entre como
   `operador@etrilha.ms` / `etrilha-operador`. Ligue a câmera, aponte para a
   etiqueta e avance o aparelho etapa por etapa até `PROCESSADO`.
   - Antes de gravar, aparece a **tela de confirmação** com o que será
     registrado — código, categoria, etapa de origem e destino, local,
     assinatura e o atestado de apagamento. O histórico é somente de
     acréscimo: não existe desfazer.
   - O campo "responsável" não existe: quem assina é a conta autenticada, e
     quem preenche esse campo é o servidor.
   - No bloco *"Testar a validação da máquina de estados"*, tente pular uma
     etapa ou voltar: **o servidor** recusa e explica o porquê.
   - Ao concluir a **triagem** de um notebook, HD ou celular, aparece o
     **atestado de apagamento**. Escolha "memória flash" e tente
     "sobrescrita de setores": o servidor recusa e explica o *wear leveling*.
4. **`rastrear.html`** — abra em **outro navegador** e consulte o código: a
   trilha completa e o certificado aparecem, sem login. É a prova de que os
   dados são compartilhados, e não locais de cada máquina.
5. **`pontos.html`** — filtre os pontos de coleta por município e por aparelho.
6. **`painel.html`** — massa desviada do aterro, materiais recuperados, CO₂e
   evitado, gargalo da cadeia e lista de pendências.
7. **`admin.html`** — entre como `admin@etrilha.ms` / `etrilha-admin`. A tela
   abre com **todos os aparelhos cadastrados**: código, categoria, etapa, ponto
   de entrada, dono, nº de leituras e se o atestado de apagamento já saiu — com
   busca por texto, filtro por etapa e um atalho para ver só os atrasados.
   Clique em **Abrir** numa conta para o painel dela — dados, aparelhos,
   histórico, permissões e exclusão (que pede a senha do próprio admin). Promova
   uma conta a operador, vincule-a a um ponto de coleta e veja a alteração
   aparecer na **trilha de administração**. Tente rebaixar o único
   administrador: o servidor recusa, para o sistema não ficar sem quem
   gerencie as contas.

**Códigos já cadastrados:**

| Código | Situação |
|---|---|
| `MS-3H7K-P2R6` | Notebook — ciclo completo, com certificado |
| `MS-9QW2-4TXK` | Celular — ciclo completo, com certificado |
| `MS-5F8N-JD3Z` | Servidor — em reciclagem |
| `MS-2KJ6-8YVF` | Monitor — em triagem e **atrasado** (sem mídia de dados) |
| `MS-8VNC-5RQ1` | HD — coletado; a próxima etapa exige o atestado de apagamento |
| `MS-4WGR-7K2N` | Impressora — parada na coleta e **atrasada** |

O botão **"Reiniciar demonstração"**, no painel, recria o banco com os dados de
exemplo.

---

## Arquitetura

```
   NAVEGADOR                                    SERVIDOR (Flask)
   ─────────                                    ────────────────
   8 páginas HTML
        │
   ui.js  ......... cabeçalho, formatação, trilha
        │
   store.js  ...... ÚNICA porta de dados  ──HTTP/JSON──▶  app.py  ..... rotas da API
        │                                                    │
   model.js  ...... regras (validação de tela)          modelo.py  ... regras (validação real)
   indicadores.js . cálculo dos indicadores             banco.py  .... SQL e transações
                                                            │
                                                     SQLite (etrilha.db)
```

**A validação existe dos dois lados, de propósito.** No navegador, para
responder rápido ao usuário. No servidor, porque **qualquer pessoa consegue
chamar a API por fora da tela** — com `curl` ou pelo console do navegador. Quem
decide o que é gravado é o servidor.

### API

| Método | Rota | O que faz |
|---|---|---|
| `GET` | `/api/pontos` | Pontos de coleta |
| `GET` | `/api/itens` | Todos os itens (painel) |
| `GET` | `/api/eventos` | Todos os eventos (painel) |
| `GET` | `/api/itens/<codigo>` | Um item |
| `GET` | `/api/itens/<codigo>/rastreio` | Item + trilha + pontos resolvidos |
| `POST` | `/api/itens` | Registra aparelho, gera código e o evento `REGISTRADO` |
| `POST` | `/api/itens/<codigo>/eventos` | Avança a etapa — **exige operador** (valida a transição) |
| `GET` | `/api/sessao` | Usuário logado, se houver |
| `POST` | `/api/sessao` | Entrar |
| `DELETE` | `/api/sessao` | Sair |
| `POST` | `/api/usuarios` | Criar conta |
| `GET` | `/api/meus-itens` | Itens do usuário logado ou do visitante |
| `GET` | `/api/admin/itens` | Todos os aparelhos com etapa, origem, dono e nº de leituras — **exige admin** |
| `GET` | `/api/admin/usuarios` | Lista as contas — **exige admin** |
| `PATCH` | `/api/admin/usuarios/<id>` | Papel, ponto vinculado e senha — **exige admin** |
| `DELETE` | `/api/admin/usuarios/<id>` | Exclui a conta — **exige admin e a senha dele** |
| `GET` | `/api/admin/alteracoes` | Trilha de administração — **exige admin** |
| `POST` | `/api/demo/reiniciar` | Recria o banco com os dados de exemplo |
| `GET` | `/api/saude` | Diagnóstico: servidor e contagens do banco |

Dá para explorar a API sem abrir o navegador:

```bash
curl http://localhost:8000/api/saude
curl http://localhost:8000/api/itens/MS-3H7K-P2R6/rastreio

# Escrever na cadeia de custódia sem ser operador: 401
curl -X POST -H "Content-Type: application/json" -d "{\"etapa\":\"COLETADO\"}"      http://localhost:8000/api/itens/MS-8VNC-5RQ1/eventos
```

### Quem pode escrever na cadeia de custódia

Ler é público: qualquer pessoa consulta um código, sem conta. **Escrever não.**
Quem lê a etiqueta é quem declara que o aparelho passou por uma etapa, e essa
declaração assinada é o produto do sistema — aberta a qualquer um, não valeria
nada.

| Papel | Registrar o próprio aparelho | Ler QR e avançar etapa | Gerenciar contas |
|---|---|---|---|
| Visitante (com ou sem conta) | sim | não | não |
| Operador | sim | sim | não |
| Administrador | sim | sim | sim |

Três decisões que sustentam isso:

- **A verificação é do servidor.** As telas do operador e do administrador
  somem do menu para quem não tem o papel, mas é o `POST`/`PATCH` que responde
  401 (falta entrar) ou 403 (entrou, sem permissão) — inclusive para chamadas
  feitas por fora da tela.
- **O papel é lido do banco a cada requisição**, nunca guardado no cookie:
  revogar o papel de alguém passa a valer na hora, sem esperar a sessão dela
  expirar.
- **O servidor carimba a assinatura e o local.** O nome do responsável vem da
  conta autenticada e o ponto vem do vínculo dela, então o formulário não
  consegue assinar com o nome de outra pessoa nem registrar passagem por um
  local onde não trabalha.

Promover alguém a operador é conceder poder de escrita no histórico, então a
concessão também deixa rastro: a tabela `alteracoes_conta` guarda quem alterou
o quê e quando, com os mesmos gatilhos de somente-acréscimo dos eventos.

### Apagamento seguro: arquitetura do hardware como regra de negócio

Um aparelho descartado carrega dados, não só metal — e é exatamente o caso das
PMEs de TI que o projeto atende. Apagar arquivo ou formatar **não destrói o
conteúdo**, e o método correto depende de **como a mídia guarda o bit**:

| | Disco magnético (HDD) | Memória flash (SSD, NVMe, eMMC) |
|---|---|---|
| Como o bit é guardado | Orientação magnética no prato | Carga elétrica presa numa célula |
| Endereço lógico → físico | Estável | **Não há**: a *flash translation layer* remapeia blocos |
| Sobrescrever setores | Funciona | **Não funciona** — *wear leveling* e *over-provisioning* deixam cópias inalcançáveis |
| Desmagnetizar | Funciona | **Não faz nada** — não há magnetismo guardando o dado |

Na triagem, aparelhos com memória não volátil só avançam com um **atestado de
apagamento** (mídia + método), e o servidor recusa a combinação ineficaz:

```
POST /api/itens/MS-YFFG-ZXBC/eventos
  {"etapa":"EM_TRIAGEM","apagamento":{"midia":"flash","metodo":"SOBRESCRITA"}}

HTTP 400  "Sobrescrita de todos os setores" não destrói os dados em memória
          flash. Sobrescrever pelo endereço lógico não alcança os blocos que o
          wear leveling remapeou nem a área de over-provisioning.
```

O atestado aparece no rastreio público junto ao certificado.

### O banco garante a cadeia de custódia

Não basta a aplicação prometer que não reescreve o histórico. `schema.sql` cria
**gatilhos que recusam qualquer `UPDATE` ou `DELETE`** na tabela `eventos`, no
nível do próprio SQLite:

```sql
CREATE TRIGGER eventos_sem_update BEFORE UPDATE ON eventos
BEGIN
  SELECT RAISE(ABORT, 'O histórico de eventos é somente de acréscimo: alterar é proibido.');
END;
```

E as escritas usam `BEGIN IMMEDIATE`, porque são do tipo "ler a etapa atual,
decidir, gravar": sem o bloqueio antecipado, dois operadores lendo o mesmo QR ao
mesmo tempo poderiam gravar a mesma etapa duas vezes.

---

## Estrutura

```
index.html        Home: consulta pública por código + números do estado
rastrear.html     Trilha do aparelho, materiais recuperados e certificado
registrar.html    Cadastro do dispositivo, código + QR, QR ampliado
etiqueta.html     Folha de etiquetas QR para impressão
scanner.html      Leitura da etiqueta e registro da etapa (exige operador)
pontos.html       Mapa SVG de MS + lista filtrável de pontos de coleta
painel.html       Indicadores para gestores, cooperativas e empresas
conta.html        Conta opcional e histórico do usuário
admin.html        Aparelhos, contas, papéis e trilha de administração (exige admin)

backend/app.py      Flask: rotas da API + entrega das páginas
backend/banco.py    Conexão SQLite, esquema, carga inicial, transações
backend/modelo.py   Regras impostas pelo servidor (etapas, código, categorias)
backend/schema.sql  DDL, índices e gatilhos de somente-acréscimo
dados/*.json        Pontos de coleta e itens de demonstração (fonte única)

js/model.js       Etapas, categorias, composição material, código, Haversine
js/store.js       Camada de dados — ÚNICA porta de acesso à API
js/indicadores.js Cálculo dos indicadores do painel (funções puras)
js/auth.js        Conta opcional
js/qr.js          Geração e leitura de QR Code
js/ui.js          Cabeçalho, avisos, formatação e linha do tempo
js/geo-ms.js      Contorno do mapa esquemático de MS

vendor/qrcode.js  qrcode-generator (MIT) — geração
vendor/jsqr.js    jsQR (Apache-2.0) — leitura, quando não há BarcodeDetector
sw.js             Service worker: consulta offline
backup/           Versão anterior, só front-end, preservada
```

---

## Funcionamento sem internet

Depois da primeira visita (quando o service worker se instala):

| | Sem conexão |
|---|---|
| Abrir as páginas | Funciona (cache do service worker) |
| Consultar trilha, pontos e painel | Funciona, com os últimos dados que passaram pelo navegador |
| Registrar aparelho, avançar etapa, entrar | **Não funciona** — precisa do servidor, que é quem valida e grava |

Uma faixa no topo avisa quando o servidor não responde. Fila de gravações
offline está listada como melhoria futura no Relatório Técnico.

---

## Articulação com as disciplinas do semestre

| Disciplina | Onde aparece |
|---|---|
| **Algoritmos e Programação** | Máquina de estados das etapas (`validar_transicao`), dígito verificador do código, Haversine, agregações do painel |
| **Arquitetura de Computadores** | **Atestado de apagamento**: a diferença entre disco magnético e memória flash (orientação magnética contra carga em célula; endereçamento estável contra *flash translation layer*) define quais métodos destroem o dado — e virou regra que o servidor impõe. Mais a tabela de composição material: ouro nos contatos e no encapsulamento dos CIs, cobre nas trilhas da placa, alumínio nos dissipadores, terras raras nos ímãs de HD |
| **Redes de Computadores** | Arquitetura cliente-servidor sobre HTTP, API REST com verbos e códigos de status, cookie de sessão, mesma origem para evitar CORS, QR transportando o identificador **sem rede** no ponto de coleta |
| **Sistemas Operacionais** | Navegador como ambiente de execução com sandbox e **permissões** (câmera, geolocalização); processo servidor escutando numa porta; service worker em segundo plano; concorrência e bloqueio de arquivo no SQLite |

---

## Limitações desta versão

- **O credenciamento do operador é por confiança no administrador.** Existe
  papel, vínculo com ponto de coleta e trilha de quem concedeu o quê, mas nada
  amarra a conta a uma pessoa física verificada — não há documento, contrato
  com a cooperativa nem segundo fator. Num sistema real, o credenciamento
  passaria pelo cadastro do órgão ambiental.
- **Qualquer operador pode avançar qualquer aparelho.** O papel não distingue
  as etapas: quem opera a coleta consegue registrar também a reciclagem. Separar
  as competências por etapa é melhoria mapeada.
- **Senha redefinida pelo admin é entregue fora do sistema.** Não há envio por
  e-mail nem obrigação de troca no primeiro acesso.
- **Sem HTTPS.** A senha trafega em texto claro. Em `localhost` isso não é
  problema; em rede, é.
- **Gravação exige conexão.** Não há fila de sincronização offline.
- **Servidor de desenvolvimento.** O `app.run` do Flask atende um pedido por
  vez e não é feito para produção — em uso real, entraria atrás de Gunicorn/Nginx.
- **Pontos de coleta fictícios**, posicionados sobre coordenadas reais dos
  municípios. Precisam ser levantados e validados em campo.
- **Composição material e fatores de CO₂e são médias de referência**, não medições.
- **Mapa esquemático**, não uma base cartográfica.

Detalhamento e melhorias futuras no [Relatório Técnico](docs/RELATORIO-TECNICO.md).

---

## Licença das bibliotecas de terceiros

- [qrcode-generator](https://github.com/kazuhikoarase/qrcode-generator) — Kazuhiko Arase, MIT
- [jsQR](https://github.com/cozmo/jsQR) — Cosmo Wolfe, Apache-2.0
- [Flask](https://flask.palletsprojects.com/) — Pallets, BSD-3-Clause
