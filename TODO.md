# TODO — e-Trilha MS

Os 14 itens pedidos estão implementados. O registro do que foi feito e por quê
está no histórico do git e nos comentários do código; a fundamentação das
decisões está no [Relatório Técnico](docs/RELATORIO-TECNICO.md).

Ficou em aberto:

## 1. A pasta `backup/` nunca foi commitada

São 25 arquivos e 724 KB — a maior massa do repositório depois de `vendor/`. O
`.gitignore` diz que "o histórico do git já cumpre esse papel", **mas não
cumpre**: `git ls-files backup` não devolve nada, ou seja, a v1 só-front-end
existe apenas nessa pasta. Apagar perde a v1 para sempre.

Saídas: commitar a v1 numa tag antes de apagar, ou deixar como está.

## 2. Sortear senha nova sem recriar o banco

A senha das contas iniciais é sorteada na carga e aparece uma vez no terminal.
Quem a perde só tem dois caminhos, e os dois custam caro: trocá-la em `/admin`
(exige estar logado, que é justamente o que se perdeu) ou reiniciar a
demonstração, que apaga contas e aparelhos junto.

Falta um comando de administração:

```powershell
python backend/app.py --nova-senha admin@etrilha.ms
```

Sorteia, grava só o hash novo, imprime uma vez e não toca em mais nada. É também
o desenho correto para uso real — recuperação de acesso é ato de quem opera o
servidor, não da interface que exige o login perdido.

## 3. Testar a interface num celular de verdade

O CSS ganhou um ponto de quebra em 640 px — menu que desliza em vez de quebrar
em três linhas, alvos de toque de 44 px, margens menores. A verificação foi por
inspeção do código, sem aparelho na mão. É justamente no celular que o sistema é
usado de pé, num galpão.

## 4. Competência por etapa

O papel de operador permite registrar qualquer etapa. O desenho correto é o
ponto de coleta registrar `COLETADO` e a recicladora registrar `PROCESSADO`,
com o vínculo entre papel, organização e etapa permitida. É a limitação nº 1 do
Relatório Técnico.
