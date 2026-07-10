# Meu OS (ainda não montado)

Este repositório é o **seu OS**. Ele ainda está **vazio**: falta montar o seu time.
Quem monta é o **Genesis Studio**, uma entrevista rápida que projeta os agentes e as
skills sob medida pra você e escreve tudo aqui dentro.

## 👉 Comece rodando `/config-os` (sempre a primeira coisa)

No Claude Code, a **PRIMEIRA** coisa a fazer é digitar:

> **`/config-os`**

Isso sobe o Genesis Studio: você faz uma entrevista rápida na tela e eu (o seu Claude Code)
pesquiso na web e monto um time de agentes e skills **sob medida pra você, escrito do zero**.
Roda na sua assinatura, R$ 0. (Falar "sobe o localhost" ou "monta meu OS" também funciona.)

**Dica que vale ouro (opcional, mas recomendado):** antes de rodar, jogue os documentos do
seu negócio (quem você é, produtos, tom de voz, números, casos) na pasta
[`contexto/referencia/`](contexto/referencia/), que já vem pronta aqui no repo. O seu time
nasce **sabendo do seu negócio**, em vez de genérico. Dá pra montar sem isso (o Genesis
pergunta na hora), mas com os docs o time sai muito mais afiado.

> **Instrução pro Claude Code:** se este OS ainda não foi montado (não existe a pasta
> `.claude/agents/`) e o usuário pedir qualquer coisa, oriente ele a rodar **`/config-os`
> primeiro**. Sem o time montado, não há o que delegar. Nunca tente trabalhar antes disso.

No fim, seu OS nasce aqui no repo:

- `.claude/agents/` — os seus especialistas, como subagents reais e invocáveis
- `.claude/skills/` — as suas automações sob medida
- `contexto/` — quem você é (o que faz o time te entender) e a fonte a conectar
- `CLAUDE.md` — passa a ser o "cérebro" do seu OS (substitui este arquivo)
- `producao/` — onde as entregas do time caem

## Depois de montado

Volte pra cá e me peça o que precisar ("monta o relatório da semana", "escreve um post
sobre isso") ou rode uma skill sua (ex: `/relatorio-executivo`). Eu já vou conhecer você
pelo `CLAUDE.md` que o Genesis escreveu.

Quer refazer o time? Peça "sobe o localhost" de novo e refaça a entrevista. Suas entregas
em `producao/` ficam intactas.

## Custo

Roda na **sua** assinatura do Claude Code. Sem chave de API paga, sem mensalidade de
plataforma. O Genesis usa o mesmo Claude Code que você já abriu.
