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

## 3. Competência por etapa

O papel de operador permite registrar qualquer etapa. O desenho correto é o
ponto de coleta registrar `COLETADO` e a recicladora registrar `PROCESSADO`,
com o vínculo entre papel, organização e etapa permitida. É a limitação nº 1 do
Relatório Técnico.
