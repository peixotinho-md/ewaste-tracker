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

O detalhamento técnico, com as decisões de projeto e os testes, está no
**[Relatório Técnico](docs/RELATORIO-TECNICO.md)**. O roteiro de apresentação e
as credenciais estão em **[docs/CREDENCIAIS-DEMO.md](docs/CREDENCIAIS-DEMO.md)**.

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

### Contas iniciais

A carga cria `admin@etrilha.ms` e `operador@etrilha.ms` e **sorteia uma senha
para cada uma**, impressa no terminal na primeira execução:

```
  Contas criadas agora, com senha sorteada:
    admin     admin@etrilha.ms       senha: ····················
    operador  operador@etrilha.ms    senha: ····················
```

**Anote no momento em que aparecem.** Elas não são gravadas em arquivo nenhum: o
banco guarda apenas o hash PBKDF2, e o sorteio não se repete. Fechar o terminal
perde a senha — resta trocá-la em `/admin`, já autenticado, ou reiniciar a
demonstração, que apaga os dados junto.

**No primeiro acesso, o sistema exige que você defina uma senha sua.** A regra é
a mesma para as duas situações em que a senha em vigor foi escolhida por outra
pessoa: a sorteada na carga e a redefinida por um administrador. Nos dois casos
existe alguém, além do dono, que conhece o segredo — e enquanto isso for verdade
a conta não prova quem a está usando. Até a troca, o servidor aceita dessa conta
apenas a própria troca de senha; todo o resto responde 403.

Quem se cadastra pela tela escolhe a senha na hora, então não passa por isso — e
nasce como **visitante**: registra e acompanha os próprios aparelhos, mas não vê
os de mais ninguém nem grava etapas na cadeia de custódia de terceiros.

### Acesso pela rede local

O servidor escuta em `0.0.0.0`, ou seja, **aceita conexões de qualquer aparelho
da mesma rede**. Ao subir, ele imprime os dois endereços:

```
  e-Trilha MS em execução:  http://localhost:8000
  Na rede local:            http://192.168.0.15:8000
```

Serve para abrir o sistema no celular, que é onde ler um QR faz sentido. Três
coisas a saber:

- **A câmera não funciona pelo IP.** `getUserMedia` só é liberado em contexto
  seguro: `localhost` ou HTTPS. Por `http://192.168.x.x` o navegador bloqueia, e
  sobra a digitação do código, disponível em todas as telas. Para a
  apresentação, use a webcam do notebook.
- **O Firewall do Windows** pede liberação na primeira execução; marque "redes
  privadas".
- **Em Wi-Fi público, feche.** Qualquer pessoa na mesma rede alcança o sistema, e
  sem HTTPS a senha trafega em texto claro:

```powershell
$env:HOST = "127.0.0.1"; python backend/app.py
```

A porta também é configurável, pela variável `PORTA`.

---

## Conta obrigatória, consulta pública

A primeira tela pergunta o que a pessoa quer: **entrar**, **criar conta** ou
**consultar um código**. Só o terceiro caminho dispensa cadastro, e leva a
`/rastrear`, que abre a trilha a partir do QR lido pela câmera ou do código
digitado. Todas as outras páginas exigem sessão, verificada **no servidor**:
pedir `/registrar` pela URL sem estar logado devolve a tela de entrada, e não a
página com um aviso.

É a divisão que o projeto defende desde o começo: **ler a trilha de um aparelho
cujo código você tem em mãos é de todos; escrever nela é de quem tem
credencial.**

Nenhuma conta lista os aparelhos de outra. O painel de indicadores mostra os
números do estado com os aparelhos **anonimizados** para conta comum, e vem
identificado só para operador e administrador, que precisam agir sobre um
aparelho específico.

### Endereços

As páginas são servidas **sem a extensão** — `/registrar`, `/painel`,
`/rastrear` —, porque a extensão diz como o arquivo está guardado no disco e
isso não é assunto de quem digita o endereço. A forma antiga redireciona para a
nova, de modo que cada tela tenha um endereço só.

Três páginas fazem duas coisas cada, escolhidas pelo contexto em vez de por um
arquivo separado: `/` mostra a porta de entrada ou a home conforme a sessão,
`/rastrear` aceita código digitado ou lido pela câmera, e `/registrar?imprimir`
troca o cadastro pela folha de etiquetas.

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
   qr.js  ......... geração e leitura do QR
                                                            │
                                                     SQLite (etrilha.db)
```

**A validação existe dos dois lados, de propósito.** No navegador, para
responder rápido ao usuário. No servidor, porque **qualquer pessoa consegue
chamar a API por fora da tela** — com `curl` ou pelo console do navegador. Quem
decide o que é gravado é o servidor.

Três garantias sustentam a cadeia de custódia, detalhadas nas seções 9.5 a 9.7
do [Relatório Técnico](docs/RELATORIO-TECNICO.md):

- **o histórico não se reescreve** — gatilhos no próprio SQLite recusam `UPDATE`
  e `DELETE` na tabela `eventos`;
- **a assinatura não se falsifica** — o nome e o ponto gravados no evento vêm da
  sessão, não do formulário;
- **o atestado de apagamento não passa se for ineficaz** — declarar sobrescrita
  de setores em memória flash é recusado, porque o *wear leveling* deixa cópias
  inalcançáveis pelo endereço lógico.

### API

| Método | Rota | O que faz |
|---|---|---|
| `GET` | `/api/pontos` | Pontos de coleta |
| `GET` | `/api/itens/<codigo>/rastreio` | Item + trilha + pontos resolvidos — **público** |
| `GET` | `/api/painel` | Indicadores. Anônimo para conta comum, identificado para operador — **exige conta** |
| `POST` | `/api/itens` | Registra aparelho, gera código e o evento `REGISTRADO` — **exige conta** |
| `POST` | `/api/itens/<codigo>/eventos` | Avança a etapa — **exige operador** (valida a transição) |
| `GET` | `/api/sessao` | Usuário logado, se houver |
| `POST` | `/api/sessao` | Entrar |
| `DELETE` | `/api/sessao` | Sair |
| `POST` | `/api/usuarios` | Criar conta |
| `POST` | `/api/sessao/senha` | Troca a senha da própria conta, pedindo a atual — **exige conta** |
| `GET` | `/api/meus-itens` | Aparelhos da conta autenticada, e só dela |
| `GET` | `/api/admin/itens` | Todos os aparelhos com etapa, origem, dono e nº de leituras — **exige admin** |
| `GET` | `/api/admin/usuarios` | Lista as contas — **exige admin** |
| `PATCH` | `/api/admin/usuarios/<id>` | Papel, ponto vinculado e senha — **exige admin** |
| `DELETE` | `/api/admin/usuarios/<id>` | Exclui a conta — **exige admin e a senha dele** |
| `GET` | `/api/admin/alteracoes` | Trilha de administração — **exige admin** |
| `POST` | `/api/demo/reiniciar` | Recria o banco e sorteia senhas novas — **exige admin** |
| `GET` | `/api/saude` | Diagnóstico: servidor e contagens do banco |

Dá para explorar a API sem abrir o navegador:

```bash
curl http://localhost:8000/api/saude
curl http://localhost:8000/api/itens/MS-3H7K-P2R6/rastreio

# Escrever na cadeia de custódia sem ser operador: 401
curl -X POST -H "Content-Type: application/json" -d "{\"etapa\":\"COLETADO\"}" \
     http://localhost:8000/api/itens/MS-8VNC-5RQ1/eventos
```

---

## Estrutura

```
index.html        Raiz: porta de entrada sem sessão, home com sessão
rastrear.html     Consulta pública: câmera, código digitado, trilha e certificado
registrar.html    Cadastro do dispositivo e (com ?imprimir) folha de etiquetas
scanner.html      Leitura da etiqueta e registro da etapa (exige operador)
pontos.html       Mapa SVG de MS + lista filtrável de pontos de coleta
painel.html       Indicadores para gestores, cooperativas e empresas
conta.html        Minha conta e meus aparelhos
admin.html        Aparelhos, contas, papéis e trilha de administração (exige admin)

backend/app.py      Flask: rotas da API + entrega das páginas
backend/banco.py    Conexão SQLite, esquema, carga inicial, transações
backend/modelo.py   Regras impostas pelo servidor (etapas, código, categorias)
backend/schema.sql  DDL, índices e gatilhos de somente-acréscimo
dados/*.json        Pontos de coleta e itens de demonstração (fonte única)

js/model.js       Etapas, categorias, composição material, código, Haversine, mapa
js/store.js       Camada de dados — ÚNICA porta de acesso à API — conta e papéis
js/indicadores.js Cálculo dos indicadores do painel (funções puras)
js/qr.js          Geração e leitura de QR Code
js/ui.js          Cabeçalho, avisos, formatação e linha do tempo

vendor/qrcode.js  qrcode-generator (MIT) — geração
vendor/jsqr.js    jsQR (Apache-2.0) — leitura, quando não há BarcodeDetector
sw.js             Service worker: consulta offline
backup/           Versão anterior, só front-end, preservada
```

---

## Funcionamento sem internet

Depois da primeira visita, o service worker guarda as **duas páginas públicas**
(a entrada e o rastreio) e os arquivos do front-end. Sem conexão, consultar a
trilha de um código já visitado continua funcionando, com os últimos dados que
passaram pelo navegador.

Registrar aparelho, avançar etapa e entrar **não funcionam offline**: dependem do
servidor, que é quem valida e grava. A tela mostra um erro claro em vez de fingir
sucesso — uma fila de gravações offline está listada como melhoria futura.

---

## Limitações desta versão

As principais, com o detalhamento na seção 14 do
[Relatório Técnico](docs/RELATORIO-TECNICO.md):

- **o papel não distingue as etapas** — um operador de ponto de coleta ainda
  consegue registrar `EM_RECICLAGEM`;
- **sem HTTPS** — a senha trafega em texto claro; em `localhost` não é problema,
  em rede é;
- **gravação exige conexão**, e o servidor é o de desenvolvimento do Flask;
- **os dados são de demonstração** — pontos de coleta fictícios sobre
  coordenadas reais, peso declarado e não pesado, e fatores de CO₂e que são
  médias de referência, não medições.

---

## Licença das bibliotecas de terceiros

- [qrcode-generator](https://github.com/kazuhikoarase/qrcode-generator) — Kazuhiko Arase, MIT
- [jsQR](https://github.com/cozmo/jsQR) — Cosmo Wolfe, Apache-2.0
- [Flask](https://flask.palletsprojects.com/) — Pallets, BSD-3-Clause
