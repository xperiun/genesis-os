# Seus dados (`contexto/dados/`)

Solte aqui as planilhas do seu trabalho.

Aceita **`.xlsx`** e **`.csv`**. Pode ser o export do sistema, o relatório que você
recebe todo mês, a planilha que você mantém na mão. Não precisa limpar nada antes:
a bagunça é justamente o que o seu OS foi feito pra enxergar.

Depois é só pedir, em português:

> *"o que aconteceu com a margem no último trimestre?"*
> *"qual região puxou o faturamento pra baixo?"*
> *"quais clientes sumiram em relação ao ano passado?"*

Ele **audita antes de responder**: mostra o que achou de estranho no arquivo
(subtotal misturado com os dados, coluna com dois formatos, célula mesclada, data
ambígua) e só então entrega o número, dizendo de onde ele veio e quantas linhas
entraram na conta.

## Isso nunca sai da sua máquina

Tudo que você colocar nesta pasta fica **só aqui**. Não sobe pro Git, não vai pra
lugar nenhum. É por isso que dá pra jogar a planilha de verdade, com nome de
cliente e faturamento real, sem pensar duas vezes.

O único arquivo desta pasta que é versionado é este README.

## Entra aqui, sai em producao/

- **`contexto/dados/`** é o que você traz.
- **`producao/`** é o que o seu time produz a partir disso: o relatório, e também
  o **script de análise**, que fica salvo e roda de novo mês que vem com o arquivo
  novo. Você não ganha uma resposta, ganha um analisador.

## Planilha grande?

Pode trazer. O tamanho não é problema: o seu OS lê o arquivo inteiro por fora e só
traz pra conversa o resumo do que encontrou.

## O que não vai aqui

Documento sobre o **negócio** (quem você é, produtos, tom de voz, casos) vai em
`contexto/referencia/`. Aquilo serve pra sua equipe te entender. Esta pasta aqui é
pro dado que ela vai analisar.
