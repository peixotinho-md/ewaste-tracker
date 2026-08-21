# Relatório Técnico de Projeto

## e-Trilha MS — rastreamento de resíduos eletrônicos por QR Code

**Curso:** 262 — Tecnologia em Análise e Desenvolvimento de Sistemas
**Disciplinas articuladas:** Algoritmos e Programação · Arquitetura de Computadores ·
Redes de Computadores · Sistemas Operacionais · Projeto de Extensão em Sustentabilidade e Diversidade
**Professor de referência:** Vitor Gabriel de Souza Farias — RF1440
**Eixo:** 3 — Resíduos e Economia Circular

**Equipe**

| Nome | RA |
|---|---|
| Rafael Dias | 205220 |
| Vinicios Pereira | 208618 |
| José Victor | 204998 |
| Eder Maciel | 205969 |
| Renato Peixoto | 205683 |

> **Como usar este documento.** As seções já estão na ordem exigida pela DAC e
> preenchidas com o que o protótipo permite afirmar hoje. Onde aparece
> **[PREENCHER]**, falta um dado local que a equipe precisa levantar — é
> justamente isso que diferencia um trabalho genérico de um trabalho aplicado a
> uma realidade concreta, como o enunciado exige.

---

## 1. Problema

O descarte inadequado de resíduos eletrônicos — celulares, computadores,
baterias, cabos e eletrodomésticos — é um problema crescente no Brasil. Boa parte
desses itens vai para o lixo comum ou fica parada em casas e empresas sem destino
definido, por desconhecimento de onde descartar ou por falta de pontos de coleta
acessíveis. O resultado é a contaminação do solo e da água por metais pesados
(chumbo, mercúrio, cádmio) e o desperdício de materiais recicláveis valiosos
(cobre, ouro, alumínio, terras raras) que poderiam voltar à cadeia produtiva.

Há, porém, um segundo problema **menos visível e não resolvido pelas soluções
existentes**: mesmo quem faz a coisa certa e entrega o aparelho num ponto de
coleta **não tem nenhuma prova de que ele foi realmente reciclado**. Não existe
rastreabilidade entre a entrega e a destinação final. Essa lacuna de confiança:

- desestimula o cidadão, que não vê consequência no próprio esforço;
- impede a empresa de comprovar conformidade com a Política Nacional de Resíduos
  Sólidos;
- deixa o gestor público sem dados sobre onde a logística reversa trava.

### 1.1 As oito perguntas de caracterização

**1. Qual é o problema?**
Resíduos eletrônicos são descartados de forma inadequada e, quando são entregues
corretamente, não há rastreabilidade que comprove a destinação final. A cadeia de
logística reversa é opaca entre o ponto de coleta e a recicladora.

**2. Onde o problema ocorre?**
Estado de Mato Grosso do Sul. O recorte é estadual porque a estrutura de coleta é
desigual: a capital concentra ecopontos e cooperativas, enquanto municípios do
interior dependem de campanhas pontuais.
> **[PREENCHER]** Levantar quantos dos 79 municípios de MS têm ponto de coleta de
> e-waste cadastrado, e citar a fonte (prefeituras, IMASUL, Green Eletron).

**3. Quem é afetado?**
- Moradores urbanos com eletrônicos obsoletos sem destino;
- Pequenas e médias empresas de TI, que geram sucata continuamente (servidores,
  impressoras, no-breaks, cabeamento);
- Cooperativas e empresas de reciclagem, que precisam de volume e previsibilidade;
- Órgãos públicos municipais responsáveis pela gestão de resíduos.

**4. Quais são as consequências?**
- *Ambientais:* contaminação de solo e água por chumbo, mercúrio, cádmio e lítio;
- *Econômicas:* perda de cobre, alumínio, aço, ouro e terras raras que teriam
  valor de mercado e evitariam mineração primária;
- *Sociais:* perda de renda para cooperativas de catadores e exposição de
  trabalhadores a resíduos perigosos em desmontagem informal.
> **[PREENCHER]** Buscar estimativa de geração de e-waste em MS (t/ano) — Global
> E-waste Monitor traz o dado nacional; verificar Plano Estadual de Resíduos Sólidos.

**5. Como o problema é tratado atualmente?**
- Ecopontos municipais e pontos de entrega voluntária, divulgados de forma
  fragmentada;
- Programas de logística reversa de fabricantes e a rede Green Eletron;
- Campanhas pontuais de coleta em escolas, órgãos e empresas.

Nenhum desses instrumentos oferece **rastreabilidade por item**: a informação para
por "recebemos o material".
> **[PREENCHER]** Descrever o que existe hoje especificamente em MS e, se possível,
> conversar com um ecoponto ou cooperativa para relatar como o registro é feito
> na prática (planilha? papel? nada?).

**6. Onde a tecnologia poderá contribuir?**
Na etapa que hoje não tem registro nenhum: o percurso entre a entrega e a
destinação final. Uma etiqueta com identificador único, lida a cada passagem,
transforma um processo opaco em uma cadeia de custódia auditável — e os registros
acumulados viram indicadores de gestão.

**7. Qual solução será desenvolvida?**
O **e-Trilha MS**: uma aplicação web em que o dispositivo é registrado, recebe um
código único e uma etiqueta QR impressa, e tem sua passagem registrada por leitura
do QR em cada etapa, até a emissão de um certificado de destinação final
consultável publicamente.

**8. Como será possível verificar se a solução funciona?**
Pelos testes descritos na seção 11: percurso completo de um aparelho pelas seis
etapas, recusa de transições inválidas, consulta pública sem login, funcionamento
sem conexão e conferência manual dos indicadores do painel.

---

## 2. Justificativa

- O e-waste é a categoria de resíduo que mais cresce no mundo, segundo o
  *Global E-waste Monitor*;
- A Lei 12.305/2010 (Política Nacional de Resíduos Sólidos) exige logística
  reversa para eletroeletrônicos, mas a adesão e a informação ao consumidor final
  ainda são baixas;
- A falta de visibilidade sobre pontos de coleta e sobre o destino do material é
  uma barreira concreta e resolvível com tecnologia;
- O tema tem aplicação direta no contexto profissional de TI, área que gera
  e-waste constantemente: HDs, impressoras, servidores e cabeamento.
> **[PREENCHER]** Acrescentar uma evidência local: notícia, dado da prefeitura,
> foto de descarte irregular em MS ou depoimento de cooperativa.

---

## 3. Público beneficiado

| Público | O que ganha |
|---|---|
| Cidadão | Sabe onde entregar e recebe prova de que o aparelho foi reciclado |
| PMEs de TI | Comprovam conformidade com a PNRS ao descartar sucata |
| Cooperativas e recicladoras | Ganham previsibilidade de volume e registro do que processaram |
| Gestores públicos municipais | Enxergam volume, cobertura territorial e gargalos da logística reversa |

---

## 4. Objetivos

**Geral.** Desenvolver uma solução tecnológica que dê rastreabilidade ao descarte
de resíduos eletrônicos em Mato Grosso do Sul, do registro do aparelho até a
comprovação da destinação final.

**Específicos.**
1. Gerar identificador único e etiqueta QR para cada dispositivo descartado;
2. Registrar a passagem do aparelho por cada etapa da cadeia por leitura do QR;
3. Garantir que o histórico seja somente de acréscimo e que nenhuma etapa possa
   ser pulada ou revertida;
4. Permitir consulta pública do andamento pelo código, sem exigir cadastro;
5. Mapear e tornar consultáveis os pontos de coleta do estado;
6. Produzir indicadores de massa desviada do aterro, material recuperado, CO₂e
   evitado e gargalos da cadeia;
7. Permitir consulta sem conexão nos pontos de coleta;
8. Garantir que as regras da cadeia sejam impostas pelo servidor e que o
   histórico não possa ser alterado nem apagado;
9. Assegurar que aparelhos com memória não volátil só sigam adiante com prova
   de que os dados foram destruídos de forma compatível com a tecnologia da mídia.

---

## 5. Pesquisa de soluções existentes

| Solução | O que faz | O que não resolve |
|---|---|---|
| Green Eletron | Rede nacional de pontos de coleta de logística reversa | Não dá rastreabilidade por item ao consumidor |
| Aplicativos municipais de coleta seletiva | Localizam pontos e informam horários | Param na entrega; não acompanham a destinação |
| Sistemas internos de recicladoras | Controlam lotes e pesagem | Fechados, sem acesso ao cidadão ou ao gestor público |
| MTR / SINIR (manifesto de resíduos) | Rastreiam transporte de resíduos entre empresas | Instrumento de conformidade B2B, por lote, não por aparelho, e sem interface para o cidadão |

**Lacuna identificada:** nenhuma das soluções acompanha o *item individual* de
ponta a ponta nem devolve essa informação a quem entregou o aparelho.
> **[PREENCHER]** Verificar se algum município de MS já usa aplicativo próprio de
> coleta e comparar. Registrar as URLs consultadas nas Referências.

---

## 6. Requisitos

### 6.1 Funcionais

| ID | Requisito | Status |
|---|---|---|
| RF01 | Registrar dispositivo com categoria, marca, peso e ponto de entrega | Implementado |
| RF02 | Gerar código único com dígito verificador e QR Code | Implementado |
| RF03 | Emitir folha de etiquetas para impressão | Implementado |
| RF04 | Ler QR pela câmera e registrar a etapa seguinte | Implementado |
| RF05 | Aceitar digitação manual do código como alternativa à câmera | Implementado |
| RF06 | Impedir pular etapas e retroceder | Implementado |
| RF07 | Consultar a trilha pelo código, sem login | Implementado |
| RF08 | Emitir certificado de destinação final | Implementado |
| RF09 | Consultar pontos de coleta com filtro por município e tipo de resíduo | Implementado |
| RF10 | Ordenar pontos pela distância até o usuário | Implementado |
| RF11 | Exibir indicadores de massa, material recuperado, CO₂e, gargalo e pendências | Implementado |
| RF12 | Conta opcional com histórico de aparelhos do usuário | Implementado |
| RF13 | Compartilhar dados entre dispositivos e usuários diferentes | Implementado (API + SQLite) |
| RF14 | Autenticar operadores por perfil (ponto, cooperativa, recicladora) | **Pendente — ver Limitações** |
| RF15 | Exigir atestado de apagamento de dados na triagem de aparelhos com memória não volátil | Implementado |
| RF16 | Recusar método de apagamento incompatível com a tecnologia da mídia | Implementado |

### 6.2 Não funcionais

| ID | Requisito | Status |
|---|---|---|
| RNF01 | Consultar sem conexão com a internet | Implementado (service worker) |
| RNF02 | Rodar em navegador de celular e de desktop, sem instalação | Implementado (PWA responsiva) |
| RNF03 | Não depender de serviço externo pago ou de CDN | Implementado (bibliotecas em `vendor/`) |
| RNF04 | Interface em português e acessível por teclado | Implementado |
| RNF05 | Armazenamento seguro de credenciais | Implementado (PBKDF2 com sal, no servidor) |
| RNF06 | Regras de negócio impostas pelo servidor, não pela tela | Implementado |
| RNF07 | Histórico de eventos impossível de alterar ou apagar | Implementado (gatilhos no banco) |

---

## 7. Solução proposta

O núcleo é uma **cadeia de custódia** de seis etapas, em que a etiqueta QR colada
no aparelho funciona como identificador físico persistente:

```
REGISTRADO → COLETADO → EM_TRIAGEM → EM_TRANSPORTE → EM_RECICLAGEM → PROCESSADO
   dono      ponto de     cooperativa   transporte     recicladora    certificado
             coleta                                                   emitido
```

Três decisões de projeto sustentam a proposta:

1. **O QR carrega a URL de rastreio, não só o código.** Quem apontar o app de
   câmera do próprio celular para a etiqueta já cai na página do aparelho, sem
   precisar instalar nada.
2. **O histórico é somente de acréscimo.** Nenhum evento é apagado ou reescrito; a
   etapa atual é apenas um espelho do último evento. É isso que dá credibilidade à
   cadeia — e é por isso que retroceder é recusado: permitiria mascarar um extravio.
3. **O prazo (SLA) de cada etapa é parte do modelo.** Um item parado além do prazo
   vira pendência automaticamente, sem ninguém precisar reportar. É assim que o
   sistema aponta *onde* a logística reversa trava, em vez de só arquivar dados.

---

## 8. Tecnologias utilizadas

| Camada | Escolha | Por quê |
|---|---|---|
| Interface | HTML5, CSS3 e JavaScript (ES Modules) | Sem build e sem framework: legível para quem está no 1º/2º semestre e sem etapa de compilação para dar errado na apresentação |
| Servidor | Python 3 com Flask | Framework mínimo, de rotas explícitas; o mesmo processo entrega a API e as páginas, o que evita CORS e simplifica a demonstração |
| Banco de dados | SQLite | Roda em processo, sem instalação nem configuração, e ainda assim oferece transações ACID, chaves estrangeiras e gatilhos de verdade |
| Senhas | PBKDF2 (`werkzeug.security`) | Hash lento e com sal aleatório: testar senhas em massa deixa de ser viável |
| Sessão | Cookie assinado do Flask, `HttpOnly` e `SameSite=Lax` | O JavaScript da página não lê o cookie, o que limita o estrago de uma falha de XSS |
| QR — geração | `qrcode-generator` (MIT), em `vendor/` | Gera SVG, que imprime nítido em qualquer tamanho |
| QR — leitura | `BarcodeDetector` (API nativa) com `jsQR` (Apache-2.0) como alternativa | O caminho nativo é mais rápido; a biblioteca cobre os navegadores sem suporte |
| Offline | Service Worker | Pontos de coleta e galpões de triagem nem sempre têm conexão |
| Mapa | SVG desenhado pela própria aplicação | Não depende de serviço externo de mapas nem de internet |

A única dependência a instalar é o Flask (`pip install -r requirements.txt`).
Nada é baixado em tempo de execução.

---

## 9. Arquitetura e estrutura

### 9.1 Cliente e servidor

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

**Regra de projeto:** nenhuma tela conversa com o servidor diretamente; tudo
passa por `js/store.js`. Foi essa regra que tornou a migração barata. Na versão
anterior, o mesmo `store.js` lia e gravava no `localStorage`, e todas as suas
funções já eram assíncronas justamente para que a troca não exigisse mexer nas
telas. Quando o back-end entrou, **só o corpo dessas funções mudou** — de acesso
local para `fetch`. Nenhuma das oito páginas precisou ser reescrita.

### 9.2 Por que a validação existe dos dois lados

As regras de etapa aparecem tanto em `js/model.js` quanto em `backend/modelo.py`.
A duplicação é intencional, e o motivo é diferente em cada lado:

- **no navegador**, para dar resposta imediata ao usuário;
- **no servidor**, porque ele não pode confiar no cliente. Qualquer pessoa
  consegue chamar a API por fora da tela, com `curl` ou pelo console do
  navegador. A tela valida para ajudar; o servidor valida para valer.

Só o que o servidor precisa impor está em Python. As tabelas de composição
material e os fatores de CO₂e ficaram apenas no front-end, porque servem para
exibição e não para decidir se uma gravação é aceita.

### 9.3 API REST

| Método | Rota | O que faz |
|---|---|---|
| `GET` | `/api/pontos` | Pontos de coleta |
| `GET` | `/api/itens` | Todos os itens (painel) |
| `GET` | `/api/eventos` | Todos os eventos (painel) |
| `GET` | `/api/itens/<codigo>` | Um item |
| `GET` | `/api/itens/<codigo>/rastreio` | Item + trilha + pontos resolvidos |
| `POST` | `/api/itens` | Registra aparelho, gera código e o evento `REGISTRADO` |
| `POST` | `/api/itens/<codigo>/eventos` | Avança a etapa (valida a transição) |
| `GET` / `POST` / `DELETE` | `/api/sessao` | Usuário atual, entrar, sair |
| `POST` | `/api/usuarios` | Criar conta |
| `GET` | `/api/meus-itens` | Itens do usuário logado ou do visitante |
| `POST` | `/api/demo/reiniciar` | Recria o banco com os dados de exemplo |
| `GET` | `/api/saude` | Diagnóstico do servidor e do banco |

Os códigos de status carregam significado: `201` quando algo é criado, `400`
quando uma regra de negócio é violada (com a mensagem já pronta para a tela),
`401` em credencial inválida e `404` quando o código não existe.

### 9.4 Modelo de dados

| Tabela | Colunas |
|---|---|
| `pontos` | `id`, `nome`, `tipo`, `municipio`, `endereco`, `lat`, `lng`, `aceita`, `horario`, `telefone` |
| `usuarios` | `id`, `nome`, `email` (UNIQUE), `senha_hash`, `criado_em` |
| `itens` | `codigo` (PK), `categoria`, `marca`, `peso_kg`, `dono_id`, `visitante_id`, `ponto_origem_id`, `criado_em`, `atualizado_em`, `etapa_atual`, `demo` |
| `eventos` | `id`, `item_codigo`, `etapa`, `ponto_id`, `responsavel`, `observacao`, `em` |

Um item pertence a um usuário (`dono_id`) **ou** a um visitante sem conta
(`visitante_id`, guardado no cookie de sessão). Ao criar conta, os itens do
visitante são adotados por ela — é isso que mantém o cadastro opcional sem
perder o histórico de quem registrou antes de se cadastrar.

### 9.5 O banco garante a cadeia de custódia

Não basta a aplicação prometer que não reescreve o histórico: um bug, um script
de manutenção ou alguém com acesso ao banco poderiam apagar a prova de que um
aparelho passou por uma etapa. Por isso a garantia está no **próprio SQLite**:

```sql
CREATE TRIGGER eventos_sem_update BEFORE UPDATE ON eventos
BEGIN
  SELECT RAISE(ABORT, 'O histórico de eventos é somente de acréscimo: alterar é proibido.');
END;
```

Existe um gatilho equivalente para `DELETE`. `etapa_atual`, na tabela `itens`, é
apenas um espelho do último evento, mantido para consulta rápida — a verdade
continua sendo a tabela de eventos.

### 9.6 Apagamento seguro: onde a arquitetura do hardware vira regra de negócio

Um aparelho descartado não carrega só metal: carrega dados. É o caso direto do
público que o próprio projeto identificou — as PMEs de TI que descartam "HDs,
impressoras, servidores". Apagar um arquivo ou formatar **não destrói o
conteúdo**: só marca o espaço como livre.

E o método correto de destruição depende de **como a mídia guarda o bit**, o que
é uma questão de arquitetura do hardware, não de software:

| | Disco magnético (HDD) | Memória flash (SSD, NVMe, eMMC) |
|---|---|---|
| Como o bit é guardado | Orientação magnética de uma região do prato | Carga elétrica presa numa célula |
| Endereço lógico → físico | Correspondência estável | **Não há**: a *flash translation layer* remapeia blocos o tempo todo |
| Sobrescrever setores | Funciona | **Não funciona** — o *wear leveling* deixa cópias em blocos remapeados, e há ainda a área de *over-provisioning*, invisível ao sistema operacional |
| Desmagnetizar (degausser) | Funciona | **Não faz nada** — não há magnetismo guardando o dado |
| O que funciona em ambos | Secure Erase, crypto-erase, destruição física | Secure Erase (o próprio controlador apaga), crypto-erase, trituração |

Na etapa `EM_TRIAGEM`, aparelhos das categorias com memória não volátil
(`celular`, `notebook`, `desktop`, `servidor`, `hd`, `impressora`) só avançam
com um **atestado de apagamento**: tipo de mídia e método usado. O servidor
recusa a combinação ineficaz, e a recusa explica o motivo técnico:

```
POST /api/itens/MS-YFFG-ZXBC/eventos
  {"etapa":"EM_TRIAGEM","apagamento":{"midia":"flash","metodo":"SOBRESCRITA"}}

HTTP 400  "Sobrescrita de todos os setores" não destrói os dados em memória
          flash (ssd, nvme, emmc, cartão). Sobrescrever pelo endereço lógico
          não alcança os blocos que o wear leveling remapeou nem a área de
          over-provisioning: em memória flash, restam cópias legíveis do dado.
```

Multifuncionais entram na lista porque as corporativas guardam cópias
digitalizadas em disco ou memória flash interna — é uma fonte de vazamento que
costuma passar despercebida no descarte.

O atestado é gravado na mesma transação do avanço de etapa (ou o item avança
com a declaração, ou não avança), fica visível no rastreio público junto ao
certificado, e a tabela `apagamentos` tem os mesmos gatilhos de
somente-acréscimo dos eventos: uma vez declarado, não se altera.

Isso liga o projeto a duas coisas ao mesmo tempo: **Arquitetura de
Computadores**, de forma aplicada e não decorativa, e a **LGPD**, já que
descartar mídia sem destruir o dado é incidente de segurança, não descuido.

### 9.7 Concorrência

As escritas usam `BEGIN IMMEDIATE`, que toma o bloqueio de escrita já na
abertura da transação, e não no primeiro `INSERT`. Isso importa porque as
gravações aqui são do tipo "ler a etapa atual, decidir, gravar": sem o bloqueio
antecipado, dois operadores lendo o mesmo QR ao mesmo tempo poderiam ambos ver
`COLETADO` e gravar `EM_TRIAGEM` duas vezes. O banco opera em modo WAL, que
permite leituras simultâneas às escritas.

### 9.8 Superfície exposta pelo servidor

A lista de arquivos que o servidor entrega é explícita (`PAGINAS`,
`ARQUIVOS_RAIZ` e `PASTAS_PUBLICAS`, em `app.py`). Um servidor que entregasse
qualquer arquivo da pasta acabaria servindo também `backend/etrilha.db` — o
banco inteiro, com os hashes de senha — e a pasta `backup/`. O que não está na
lista responde 404.

### 9.9 Algoritmos relevantes

- **Máquina de estados** (`validar_transicao`): só aceita o passo imediatamente
  seguinte; recusa retrocesso e salto de etapa, com mensagem explicando o motivo.
  Roda no servidor, dentro da transação, sobre a etapa lida do banco — nunca
  sobre o que o cliente afirmou ser a etapa atual.
- **Dígito verificador** (`digito_verificador`): soma ponderada módulo 32 sobre um
  alfabeto base32 **sem os caracteres I, L, O e U** — os que as pessoas confundem
  ao ler uma etiqueta suja. Detecta todos os erros de um caractere e a maioria das
  transposições. A normalização ainda corrige `O→0`, `I→1`, `L→1` e `U→V`.
- **Validação do apagamento** (`validar_apagamento`): confere se o método
  declarado destrói o dado naquele tipo de mídia; a tabela de compatibilidade
  vem da arquitetura da mídia, não de convenção (seção 9.6).
- **Haversine** (`distanciaKm`): distância entre o usuário e cada ponto de coleta,
  calculada no próprio aparelho — a localização não é enviada a lugar nenhum.
- **Detecção de gargalo**: para cada etapa, média das durações **encerradas**
  dividida pelo SLA. A etapa com a maior razão é o gargalo. Durações em aberto são
  excluídas de propósito, pois ainda não terminaram e distorceriam a média.
- **Projeção cartográfica**: equirretangular, com o eixo X comprimido por
  `cos(latitude média)` para o estado não sair esticado.

### 9.10 Articulação com as disciplinas

| Disciplina | Contribuição concreta ao projeto |
|---|---|
| **Algoritmos e Programação** | Máquina de estados, dígito verificador, Haversine, agregações e ordenações do painel |
| **Arquitetura de Computadores** | Duas contribuições, ambas viradas em código. (1) O **atestado de apagamento** (seção 9.6): a diferença entre disco magnético e memória flash — orientação magnética contra carga em célula, endereçamento estável contra *flash translation layer* com *wear leveling* — define quais métodos destroem o dado, e essa distinção virou uma regra que o servidor impõe. (2) A **tabela de composição material** sai da arquitetura real do hardware: ouro nos contatos e no encapsulamento dos circuitos integrados, cobre nas trilhas da placa e nos enrolamentos, alumínio nos dissipadores e no chassi, terras raras nos ímãs de HDs e alto-falantes — é o que permite estimar o que se recupera de cada aparelho |
| **Redes de Computadores** | Arquitetura cliente-servidor sobre HTTP; API REST com verbos e códigos de status; cookie de sessão; mesma origem para evitar CORS; e o QR transportando o identificador **sem depender de rede** no ponto de coleta |
| **Sistemas Operacionais** | Processo servidor escutando numa porta; navegador como ambiente de execução com sandbox e **modelo de permissões** para câmera e geolocalização (o app nunca fala direto com o dispositivo); service worker como processo em segundo plano; concorrência, bloqueio de arquivo e journaling (WAL) no SQLite |

---

## 10. Desenvolvimento

> **[PREENCHER]** Registrar como o trabalho foi dividido na equipe, as decisões
> que mudaram no meio do caminho e as dificuldades encontradas. Vale colar
> capturas de tela da evolução entre as pré-entregas de 04/09, 25/09 e 23/10.

Marcos previstos no cronograma da DAC:

| Etapa | Data | Entrega |
|---|---|---|
| 2 | 04/09 | Pré-entrega 1: problema, evidências, objetivos e referências |
| 5 | 25/09 | Pré-entrega 2: proposta técnica + protótipo inicial + relatório v0.3 |
| 8 | 23/10 | Pré-entrega 3: fluxo principal funcionando + evidências de teste |
| 9 | 29/10 | Entrega: MVP + Relatório Técnico |
| 10 | 03–06/11 | Apresentação final |

---

## 11. Testes

### 11.1 Roteiro executado

| # | Cenário | Resultado esperado |
|---|---|---|
| 1 | Registrar um notebook | Código com dígito verificador válido e QR gerado |
| 2 | Pré-visualizar a folha de etiquetas | QR legível, um por aparelho selecionado |
| 3 | Ler o QR e avançar as seis etapas | Item chega a `PROCESSADO` e o certificado é emitido |
| 4 | Tentar pular uma etapa | Recusado, com o motivo exibido |
| 5 | Tentar retroceder uma etapa | Recusado, com o motivo exibido |
| 6 | Consultar o código em janela anônima | Trilha completa exibida sem login |
| 7 | Digitar o código com erro de um caractere | Rejeitado pelo dígito verificador |
| 8 | Digitar o código em minúsculas, sem hífen e com `O` no lugar de `0` | Aceito e normalizado |
| 9 | Filtrar pontos por município e por tipo de aparelho | Lista e mapa refletem o filtro |
| 10 | Conferir os indicadores do painel à mão | Massa e contagens batem com os itens cadastrados |
| 11 | Recarregar sem conexão | Aplicação continua abrindo e consultando (service worker) |
| 12 | Abrir no Firefox | Leitura cai para o jsQR, pois não há `BarcodeDetector` |
| 13 | Registrar um item num navegador e consultá-lo em **outro** | O segundo navegador vê o item, a trilha e o responsável |
| 14 | Chamar a API por fora da tela, com `curl`, pedindo uma etapa inválida | Recusado com HTTP 400 e a mesma mensagem da interface |
| 15 | Tentar `UPDATE` ou `DELETE` em `eventos` direto no SQLite | Recusado pelos gatilhos do banco |
| 16 | Pedir `backend/etrilha.db` pelo navegador | HTTP 404 — não está na lista de arquivos servidos |
| 17 | Concluir a triagem de um HD sem informar o atestado | Recusado: a etapa não avança |
| 18 | Declarar sobrescrita de setores em memória flash | Recusado, com a explicação do *wear leveling* |
| 19 | Declarar desmagnetização em memória flash | Recusado: não há magnetismo guardando o dado |
| 20 | Declarar ATA Secure Erase em memória flash | Aceito; atestado aparece no rastreio público |
| 21 | Avançar um monitor (sem mídia) para a triagem | Aceito sem exigir atestado |
| 22 | Tentar `UPDATE` ou `DELETE` na tabela `apagamentos` | Recusado pelos gatilhos |

### 11.2 Resultados obtidos

**Integração entre o gerador e o leitor de QR** (cenário 1 a 3), verificada de
ponta a ponta: o QR gerado no registro foi rasterizado e decodificado pelo mesmo
`jsQR` que o scanner usa, o código extraído localizou o item e a etapa avançou.

```
PASSOU  codigo gerado e valido: MS-RJYM-60V4
PASSOU  QR desenhado como SVG
PASSOU  jsQR decodificou a imagem do QR
PASSOU  conteudo lido == URL gerada
PASSOU  extrairCodigo devolveu MS-RJYM-60V4
PASSOU  store encontrou o item pelo codigo lido
PASSOU  etapa avancou para COLETADO apos a leitura
PASSOU  pular etapa foi recusado
PASSOU  retroceder etapa foi recusado
```

**Regras impostas pelo servidor** (cenário 14), chamando a API diretamente:

```
POST /api/itens/MS-H432-SQAX/eventos  {"etapa":"PROCESSADO"}
  HTTP 400  Não é possível pular etapas: depois de "Coletado" vem "Em triagem".

POST /api/itens/MS-H432-SQAX/eventos  {"etapa":"REGISTRADO"}
  HTTP 400  Não é possível retroceder de "Coletado" para "Registrado".
            O histórico é somente de acréscimo.
```

**Histórico imutável** (cenário 15), direto no banco:

```
PASSOU  UPDATE em eventos bloqueado -> O histórico de eventos é somente de acréscimo: alterar é proibido.
PASSOU  DELETE em eventos bloqueado -> O histórico de eventos é somente de acréscimo: apagar é proibido.
```

**Dados compartilhados** (cenário 13): item criado numa sessão e avançado para
`COLETADO`; um navegador com perfil limpo, sem nenhum cookie da primeira sessão,
abriu `rastrear.html` com o código e exibiu a trilha completa, incluindo o
responsável registrado pela outra sessão.

> **[PREENCHER]** Anexar as evidências em imagem: capturas de tela de cada
> cenário, especialmente as mensagens de recusa dos cenários 4, 5, 7 e 14.

### 11.3 Conferência manual dos indicadores

Exemplo com o notebook de 1,9 kg dos dados de demonstração:

| Material | Fração | Massa | CO₂e evitado |
|---|---|---|---|
| Alumínio | 21% | 0,399 kg | 3,59 kg |
| Plástico | 31% | 0,589 kg | 1,00 kg |
| Cobre | 9% | 0,171 kg | 0,60 kg |
| Aço | 12% | 0,228 kg | 0,41 kg |
| Ouro | 90 mg/kg | 171 mg | 2,14 kg |
| **Total** | | | **≈ 7,9 kg CO₂e** |

O ouro responde por mais de um quarto do CO₂e evitado apesar de pesar 171 mg:
produzir 1 kg de ouro primário movimenta toneladas de minério.

---

## 12. Viabilidade

**Técnica.** O protótipo já funciona com tecnologias de navegador, sem
dependência de serviço pago. O back-end previsto (API REST + banco relacional) é
compatível com o que a equipe estuda no semestre e não exige infraestrutura
especial. A leitura de QR usa hardware que os operadores já têm: o celular.

**Executiva.** O custo material é baixo — etiquetas adesivas e celulares comuns.
O obstáculo real não é técnico, é de **adesão**: a solução só funciona se os
pontos de coleta, cooperativas e recicladoras registrarem as leituras. Isso exige
articulação institucional com prefeituras e com a rede de logística reversa.

> **[PREENCHER]** Estimar o custo por etiqueta e por mês de hospedagem, e indicar
> qual órgão ou entidade seria o operador natural da plataforma em MS.

---

## 13. Relação com a sustentabilidade

A sustentabilidade está na **mecânica da solução**, não apenas na justificativa:

- **Ambiental** — cada aparelho rastreado é massa que deixa de ir para o aterro.
  O sistema quantifica o que foi recuperado (cobre, alumínio, aço, plástico,
  vidro, terras raras e ouro) e converte em CO₂e evitado, comparando a reciclagem
  com a produção primária. Também registra os contaminantes que o descarte comum
  liberaria (chumbo, mercúrio, cádmio, lítio).
- **Econômica** — devolve material valioso à cadeia produtiva e dá às cooperativas
  previsibilidade de volume, além de permitir que empresas comprovem conformidade
  com a PNRS.
- **Social** — a consulta pública sem cadastro coloca cidadão e gestor com a mesma
  informação, e a detecção de gargalos transforma reclamação difusa em dado
  acionável.

O que impede o projeto de ser "um cadastro que se diz sustentável" é justamente
isso: **o que a plataforma produz é prova de destinação e medida de impacto**,
não um formulário.

---

## 14. Limitações

1. **Sem controle de perfis.** Esta é a limitação mais séria. Qualquer pessoa
   com o código pode registrar qualquer etapa. Num sistema real, só um operador
   credenciado da etapa correspondente poderia fazê-lo — o ponto de coleta
   registra `COLETADO`, a recicladora registra `PROCESSADO`, e ninguém registra
   pelo outro. A infraestrutura de sessão já existe; falta o vínculo entre
   usuário, organização e etapa permitida.
2. **Sem HTTPS.** A senha e o cookie de sessão trafegam em texto claro. Em
   `localhost` isso não é problema, porque nada sai da máquina; numa rede real,
   é inaceitável. Em produção, o servidor entraria atrás de um proxy com TLS e o
   cookie ganharia o atributo `Secure`.
3. **Gravação exige conexão.** A consulta funciona sem internet, com os últimos
   dados que passaram pelo navegador, mas registrar um aparelho ou avançar uma
   etapa precisa do servidor — que é quem valida a transição e grava a cadeia.
   A tela mostra um erro claro em vez de fingir sucesso.
4. **Servidor de desenvolvimento.** O `app.run` do Flask atende um pedido por
   vez e não é feito para produção; em uso real, entraria atrás de Gunicorn ou
   equivalente.
5. **Pontos de coleta fictícios**, posicionados sobre coordenadas reais dos
   municípios. Precisam ser levantados e validados em campo.
6. **Composição material e fatores de CO₂e são médias de referência**, não
   medições. Servem para ordem de grandeza, não para contabilidade ambiental oficial.
7. **Mapa esquemático**, com contorno simplificado do estado — é um recurso de
   orientação, não uma base cartográfica.
8. **Câmera exige contexto seguro** (`localhost` ou HTTPS). Pelo celular na rede
   local via HTTP puro, só a digitação manual funciona.
9. **A cadeia depende de confiança nos operadores.** O sistema garante que o
   histórico não seja reescrito, mas não prova que a leitura corresponde a um
   movimento físico real.

---

## 15. Melhorias futuras

1. **Perfis e credenciamento** (prioridade): vincular cada operador a uma
   organização e a uma etapa, de modo que só o ponto de coleta registre
   `COLETADO` e só a recicladora registre `PROCESSADO`. É o que fecha a
   limitação nº 1.
2. **HTTPS**, com o cookie de sessão marcado como `Secure`. Também é o que
   libera a leitura por câmera no celular, hoje bloqueada em HTTP puro.
3. **Fila de gravações offline**: registrar leituras sem conexão e sincronizar
   quando a rede voltar, tratando os conflitos de transição na volta. É a
   funcionalidade que mais mudaria o uso em galpões de triagem.
4. **Assinatura digital do certificado** de destinação, para valer como documento.
5. **Pesagem real na triagem**, substituindo a estimativa por categoria.
6. **Integração com o SINIR/MTR**, aproveitando o registro já existente de
   transporte de resíduos.
7. **Notificação ao dono** a cada avanço de etapa.
8. **Base cartográfica real** com rotas até o ponto de coleta mais próximo.
9. **Levantamento em campo** dos pontos de coleta reais de MS, em parceria com as
   prefeituras e a Green Eletron.

---

## 16. Conclusão

> **[PREENCHER]** Retomar a pergunta da DAC — *"Como a Tecnologia da Informação
> pode contribuir para solucionar ou reduzir um problema real relacionado à
> sustentabilidade?"* — e responder com base no que o protótipo demonstrou.
>
> Argumento central sugerido: a contribuição da TI aqui não foi criar mais um
> cadastro, e sim **produzir informação que antes não existia** — a prova de que
> o aparelho chegou à reciclagem. Essa informação muda o comportamento de três
> públicos ao mesmo tempo: dá retorno ao cidadão, dá conformidade à empresa e dá
> ao gestor público a localização exata do gargalo.

---

## 17. Referências

> **[PREENCHER]** Completar com as datas de acesso e com as fontes locais
> levantadas pela equipe. Formatar conforme ABNT NBR 6023.

- BRASIL. **Lei nº 12.305, de 2 de agosto de 2010.** Institui a Política Nacional
  de Resíduos Sólidos.
- FORTI, V. et al. **The Global E-waste Monitor.** UNITAR/UNU/ITU.
- GREEN ELETRON. *Gestora para logística reversa de eletroeletrônicos.*
  Disponível em: <https://greeneletron.org.br>.
- **[PREENCHER]** Plano Estadual / Municipal de Resíduos Sólidos de MS.
- **[PREENCHER]** Fonte dos percentuais de composição material por categoria de
  equipamento usados em `js/model.js`.
- **[PREENCHER]** Fonte dos fatores de CO₂e evitado por material.

### Bibliotecas de terceiros

- ARASE, Kazuhiko. **qrcode-generator.** Licença MIT.
- WOLFE, Cosmo. **jsQR.** Licença Apache-2.0.
- PALLETS. **Flask** e **Werkzeug.** Licença BSD-3-Clause.
