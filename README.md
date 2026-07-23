# Meu OS

O seu sistema operacional pessoal, montado por você. Você faz uma entrevista rápida e o
seu próprio Claude Code pesquisa e monta um time de agentes e skills sob medida, escritos
do zero pro seu caso. Roda na sua assinatura do Claude Code, R$ 0 de API.

## Começar (uma vez só)

> **Nunca usou o Claude Code?** Instala ele primeiro (`npm i -g @anthropic-ai/claude-code`),
> **reinicia o VS Code** e só então siga os passos abaixo. Assim nada trava no meio.

1. **Abra esta pasta no VS Code** por `Arquivo > Abrir Pasta` (selecione a pasta do repo).
   Abrir a pasta fresca é o que faz o Claude Code carregar o comando `/setup`.
2. No Claude Code, **peça "monta meu OS"** — ou digite **`/setup`**. (É a única coisa que
   você faz aqui.)
3. O Genesis abre no navegador: conecte o material do seu negócio e faça a entrevista. No
   fim, seu OS nasce aqui no repo.
4. Volte pro Claude Code e comece a trabalhar (ex: `/relatorio-executivo`), ou rode
   **`/painel`** pra abrir a sala de controle do seu OS.

> **O `/setup` não apareceu ao digitar `/`?** Acontece se você clonou dentro de uma janela
> que já estava aberta: o Claude Code só indexa os comandos ao abrir a pasta. Basta pedir em
> palavras ("monta meu OS") que funciona do mesmo jeito, ou dar um
> `Ctrl+Shift+P → Reload Window` uma vez.

Detalhe em `CLAUDE.md`.

## O que nasce aqui

- `.claude/agents/` — o seu time, como subagents reais e invocáveis do Claude Code.
- `.claude/skills/` — as suas automações sob medida.
- `contexto/` — quem você é (o que faz o time te entender). Os docs do negócio vão em
  `contexto/referencia/`, e suas **planilhas** (`.csv`/`.xlsx`) em `contexto/dados/`.
- `CLAUDE.md` — o cérebro do seu OS, lido pelo Claude Code toda sessão.
- `producao/` — onde as entregas do time caem.

## Custo

Roda na sua assinatura do Claude Code. Sem chave de API paga, sem mensalidade.

Quer refazer o time? Rode `/setup` de novo. Suas entregas em `producao/` ficam intactas.
