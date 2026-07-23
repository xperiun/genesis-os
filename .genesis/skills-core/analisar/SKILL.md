---
name: analisar
description: "Audita e analisa planilha (.xlsx, .csv) antes de responder qualquer pergunta sobre ela. Perfila o arquivo inteiro, mostra as armadilhas que encontrou (subtotal no meio dos dados, coluna de tipo misto, célula mesclada, data ambígua, dado pessoal), escreve o script de análise já defendido contra elas, e reconcilia o resultado contra o próprio arquivo antes de mostrar qualquer número. Use quando pedirem para analisar, somar, agrupar, comparar ou responder pergunta sobre planilha, tabela, base, relatório, export, faturamento, vendas, custo ou qualquer arquivo em contexto/dados/."
---

# Analisar

Você audita a planilha, mostra o que achou de estranho, e **só então** responde.

Essa ordem não é preciosismo. Planilha de negócio brasileira quebra em silêncio:
o script roda liso, sai um número plausível, e está errado. Todos os casos abaixo
foram medidos, não imaginados.

| Armadilha | O que acontece com o número |
|---|---|
| subtotal no meio dos dados | soma dá **3x** o valor certo |
| coluna com float nativo junto de texto BR | a limpeza padrão infla **37x** |
| célula mesclada | **60% do valor** some do agrupamento |
| data BR lida como americana | 6 de 7 linhas caem no mês errado |
| `errors="coerce"` | linha inválida vira nulo e **desaparece sem reduzir o total** |

Nenhuma delas levanta exceção. É por isso que existe procedimento aqui em vez de
você simplesmente ler o arquivo e responder.

---

## O contrato

> **Nenhum número chega na tela sem a própria certidão de nascimento.**
> Se você não consegue enunciar de onde ele veio, quantas linhas entraram,
> quantas ficaram de fora e por quê, você não tem direito de imprimir.

---

## Passe 1 — Perfilar (obrigatório, nunca pule)

```bash
python .claude/skills/analisar/scripts/perfilar.py <arquivo>
```

O profiler lê **100% das linhas** e devolve um relatório de tamanho fixo. Você lê
o relatório, **não o arquivo**.

**Por que não basta olhar as primeiras linhas:** num arquivo de 1.210 linhas com
5 subtotais, o primeiro subtotal aparece na **linha 241**. Amostra de 50, de 100 e
de 250 não veem nenhum. Você concluiria "tabela limpa" e escreveria um script
confiante que erra 3x. A amostra não é amostra, é viés.

Se o arquivo tem várias abas e a escolhida não for a certa, rode de novo com
`--aba "Nome Da Aba"`. Precisa da saída em JSON? `--json`.

**Mostre ao usuário as armadilhas P0 que o profiler achou, em português, antes de
seguir.** Esse é o momento em que ele vê valor: a máquina enxergando o que ele
não enxergava na própria planilha.

## Passe 2 — Escrever o script

Com o relatório na mão, escreva um script Python em `producao/analises/` que
responde a pergunta. Regras:

- **Importe a reconciliação.** `sys.path` até `scripts/reconciliar.py`, e use
  `Auditoria`, `parse_numero` e `marcadores_de_agregacao`. Não reescreva isso.
- **Nunca use `errors="coerce"` sozinho.** Use `Auditoria.numeros()`, que conta e
  lista o que foi descartado. Perda silenciosa é a porta de entrada de tudo.
- **Nunca aplique `replace(".","").replace(",",".")` numa coluna inteira** quando
  o profiler marcou `tipo_misto`. Isso conserta o texto e destrói o float que já
  estava certo. `parse_numero` trata os dois tipos no mesmo passe.
- **Exclua as linhas de agregação do cálculo** e guarde elas: são o gabarito do
  passe 3.
- **Preencha a mescla pra baixo** antes de qualquer `groupby`, se o profiler
  marcou `merge`.
- Se `pandas_disponivel` for `false` no relatório, escreva com `csv` e `openpyxl`
  da biblioteca padrão. Não mande o usuário instalar nada no meio do trabalho.

## Passe 3 — Reconciliar antes de mostrar

```python
a = Auditoria("Faturamento total de 2025")
a.excluir(len(agregacao), "linhas de TOTAL/SUBTOTAL do próprio arquivo")
valores = a.numeros(coluna, convencao="BR", contexto="a coluna Faturamento")
total = a.soma(valores)
a.conferir(total, referencia=total_geral_do_arquivo, fonte="a linha TOTAL GERAL")
if a.bloqueado():
    print(a.certidao())          # mostra a divergência, NUNCA o número
else:
    print(a.certidao(total, moeda=True))
```

**A inversão que faz isso funcionar:** a linha `TOTAL GERAL` que envenena a soma
ingênua é gabarito de graça. Tire ela da conta, depois use ela pra **provar** a
conta. O arquivo quase sempre já traz a própria resposta.

Quando não houver total no arquivo, reconcilie por outro caminho: a soma dos
grupos tem que bater com o total geral (`conferir_partes`). Se não houver nenhuma
conferência possível, **diga isso em voz alta** e trate o número como estimativa.

---

## Regras invioláveis

1. **Ambiguidade não se chuta, se pergunta.** Se o profiler disser
   `separador_ambiguo` ou `data_ambigua`, ele não conseguiu **provar** o formato.
   Pergunte em português: *"nessa planilha, `1.234` é mil duzentos e trinta e
   quatro ou é um vírgula dois? E `05/01` é 5 de janeiro?"*. Perguntar não é
   fraqueza, é a diferença entre uma resposta e um chute com cara de resposta.

2. **Número bloqueado não vira resposta.** Se `bloqueado()` for verdadeiro, você
   mostra a divergência e para. Não arredonde, não escolha o mais bonito, não
   diga "aproximadamente".

3. **Dado pessoal é mascarado antes de qualquer render.** Se o profiler marcar
   `pii`, use `mascarar()` em tudo que for pra tela, relatório ou apresentação.
   CPF, e-mail, telefone e salário não aparecem inteiros. Isso não é bug, é risco
   jurídico, e a tela pode estar sendo projetada ou gravada.

4. **O script fica.** Ele mora em `producao/analises/` e roda de novo mês que vem
   com o arquivo novo. A pessoa não ganhou uma resposta, ganhou um analisador.
   Diga isso a ela.

5. **Nunca invente coluna que não existe no relatório.** Se a pergunta pede algo
   que a planilha não tem, diga o que falta em vez de aproximar por outra coluna.

---

## Onde as coisas moram

| Pasta | O quê |
|---|---|
| `contexto/dados/` | as planilhas do usuário. **Entra aqui.** Fora do Git, nunca sobe pra lugar nenhum |
| `producao/analises/` | o script gerado e o relatório. **Sai aqui** |
| `contexto/referencia/` | material sobre o negócio (quem é, produtos, tom). **Não** é lugar de planilha de dado |

Se o usuário não disser onde está o arquivo, olhe em `contexto/dados/` primeiro.

---

## Quando dá errado

- **`PermissionError` ao abrir:** o arquivo está aberto no Excel. Peça pra fechar.
  Acontece o tempo todo, porque a pessoa acabou de mexer nele.
- **`.xls` antigo:** peça pra abrir no Excel e salvar como `.xlsx`. Não tente
  converter na marra.
- **`.pdf` ou `.docx`:** esses você lê direto com a Read, sem profiler.
- **Arquivo gigante:** não tem problema, o profiler foi feito pra isso. Ele lê
  tudo e devolve relatório curto. O que você nunca faz é jogar o arquivo inteiro
  no contexto.

---

## Regressão

Mexeu no profiler ou na reconciliação, rode antes de dar por pronto:

```bash
cd .claude/skills/analisar/tests
python gerar_fixtures.py && python testar_profiler.py
```

São 33 asserções sobre planilhas hostis que já produziram erro silencioso de
verdade. Todas têm que passar. Se alguma falhar, o erro voltou.
