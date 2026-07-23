# Meu OS (ainda não montado)

Este repositório é o **seu OS**. Ele ainda está **vazio**: falta montar o seu time.
Quem monta é o **Genesis Studio**, uma entrevista rápida que projeta os agentes e as
skills sob medida pra você e escreve tudo aqui dentro.

## 👉 Comece rodando `/setup` (sempre a primeira coisa)

No Claude Code, a **PRIMEIRA** coisa a fazer é digitar:

> **`/setup`**

É só isso que você digita aqui. O Genesis abre no navegador e o resto acontece lá: você
conecta o material do seu negócio, faz uma entrevista rápida, e eu (o seu Claude Code)
pesquiso na web e monto um time de agentes e skills **sob medida pra você, escrito do zero**.
Roda na sua assinatura, R$ 0. (Falar "sobe o localhost" ou "monta meu OS" também funciona.)

**Dica:** se você já tem os documentos do seu negócio em arquivo (quem você é, produtos, tom
de voz, números, casos), pode jogar eles na pasta [`contexto/referencia/`](contexto/referencia/)
antes de rodar. Não precisa: a própria cena deixa você soltar os arquivos, colar o link do seu
site ou trazer o contexto de outro assistente. De um jeito ou de outro, quanto mais real o
material, mais afiado o time sai.

**Se você está no plano Pro:** não precisa fazer nada aqui, mas vale saber o que vai
acontecer. Montar o time é a parte pesada, uns 5 minutos de trabalho contínuo do seu Claude
Code pesquisando e escrevendo. No Pro, o **Opus tem uma cota própria**, mais apertada, e é
ela que costuma acabar primeiro. Se acabar no meio, sai um time **base** em vez do sob
medida. Por isso, se a sua máquina estiver usando Opus, **a própria cena te oferece montar
com Sonnet** antes de começar, e é só marcar a caixinha. No Max, pode ignorar.

Depois de montado, use **`/painel`** pra abrir a sala de controle do seu OS (o time, as
tarefas, o chat com cada agente). O `/setup` é uso único, o `/painel` é o dia a dia.

> **Instrução pro Claude Code:** se este OS ainda não foi montado (não existe a pasta
> `.claude/agents/`) e o usuário pedir qualquer coisa, oriente ele a rodar **`/setup`
> primeiro**. Sem o time montado, não há o que delegar. Nunca tente trabalhar antes disso.
>
> **Se o `/setup` não estiver disponível no menu de comandos (`/`)**, não trave nem mande o
> usuário reabrir o VS Code. Comando de projeto só é indexado no início da sessão, então num
> repo recém-clonado ele pode ainda não aparecer no autocomplete. Isso NÃO impede a execução:
> quando o usuário pedir pra montar o OS por qualquer via (`/setup`, "monta meu OS", "sobe o
> localhost", "rode o setup", "clona e roda o setup"), **leia o arquivo
> [`.claude/commands/setup.md`](.claude/commands/setup.md) e execute o roteiro dele de ponta a
> ponta**, do jeito que está escrito. O slash command é só um atalho pra esse mesmo roteiro.

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
