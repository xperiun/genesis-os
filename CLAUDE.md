# Xperiun OS (ainda não montado)

Este repositório é o seu Xperiun OS. Ele ainda está **vazio**: falta montar o seu time.
Quem monta é o **Genesis Studio**, uma entrevista rápida que projeta os agentes e as
skills sob medida pra você e escreve tudo aqui dentro.

## Como começar (é uma vez só)

Fale comigo (Claude Code) qualquer uma destas:

> **"sobe o localhost"**  ·  "abre o Genesis"  ·  "monta meu OS"

Quando você pedir, eu rodo:

```bash
python .genesis/sobe.py
```

Isso prepara o ambiente (uma vez) e abre a cena do Genesis no seu navegador. Você faz a
entrevista, eu (o seu Claude Code, na sua assinatura) conduzo, pesquiso na web e **escrevo
o seu time do zero**. No fim, seu OS nasce aqui no repo:

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
