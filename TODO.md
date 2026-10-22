# TODO — e-Trilha MS

Os 14 itens pedidos estão implementados. O registro do que foi feito e por quê
está no histórico do git e nos comentários do código; a fundamentação das
decisões está no [Relatório Técnico](docs/RELATORIO-TECNICO.md).

Ficou em aberto:

## 0. Decidir sobre o dígito verificador antes de imprimir etiqueta de verdade

A suíte de testes mediu: cerca de **5% dos erros de um caractere passam** pelo
dígito verificador. A causa é aritmética — os pesos são 8, 7, 6, 5, 4, 3, 2, e
todo peso par divide o módulo 32, o que deixa passar a troca cujo efeito na soma
é múltiplo de 32. Pesos todos ímpares fechariam a brecha.

A correção em si é de uma linha em `backend/modelo.py` e uma em `js/model.js`.
O custo está no resto: **todo código já emitido muda de dígito**. Isso invalida
os dez itens de `dados/itens-demo.json` (que precisariam ser regerados), as
capturas de tela já feitas para o relatório e qualquer etiqueta impressa.

Enquanto as etiquetas são de demonstração, o custo é baixo e cai a cada semana
que passa. É a decisão que vale tomar agora, e não depois de 23/10.

**Medido em 22/10: pesos ímpares não resolvem, trocam um defeito por outro.**
Simulação com 3.000 códigos aleatórios, todas as trocas de um caractere e todas
as inversões de dois vizinhos:

| Pesos | Troca de 1 caractere escapa | Inversão de vizinhos escapa |
|---|---|---|
| Atuais (8, 7, 6, 5, 4, 3, 2) | 5,5% | 0% |
| Ímpares (13, 11, 9, 7, 5, 3, 1) | 0% | 3,3% |

Com pesos vizinhos diferindo de 1, a inversão `ab → ba` muda a soma em
`(a − b)`, que nunca é múltiplo de 32. Com pesos ímpares a diferença vira
`2 · (a − b)`, e `a − b = ±16` passa. Como 32 não é primo, nenhum jogo de pesos
numa soma ponderada módulo 32 pega os dois erros ao mesmo tempo.

Saídas que pegam os dois, a avaliar:
- **Algoritmo de Damm** sobre um quasigrupo de ordem 32 — pega toda troca simples
  e toda inversão de vizinhos, com um caractere só.
- **Módulo primo** (31 ou 37) com pesos distintos — pega quase tudo, mas o dígito
  passa a ter 31 ou 37 valores, e o alfabeto de 32 não fecha certo.

Em qualquer caso, o custo continua o mesmo: mudar os dois lados
(`backend/modelo.py` e `js/model.js`), o teste de paridade e o que trava os 5%
em `testes/teste_modelo.py`, regerar `dados/itens-demo.json` e trocar os códigos
citados no relatório e nas capturas de `docs/evidencias-pe3/`.

## 1. A pasta `backup/` nunca foi commitada

São 25 arquivos e 724 KB — a maior massa do repositório depois de `vendor/`. O
`.gitignore` diz que "o histórico do git já cumpre esse papel", **mas não
cumpre**: `git ls-files backup` não devolve nada, ou seja, a v1 só-front-end
existe apenas nessa pasta. Apagar perde a v1 para sempre.

Saídas: commitar a v1 numa tag antes de apagar, ou deixar como está.

## 2. Testar a interface num celular de verdade

O CSS ganhou um ponto de quebra em 640 px — menu que desliza em vez de quebrar
em três linhas, alvos de toque de 44 px, margens menores. A verificação foi por
inspeção do código, sem aparelho na mão. É justamente no celular que o sistema é
usado de pé, num galpão.
