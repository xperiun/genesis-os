---
description: Monta (ou remonta) o seu OS, a entrevista que cria o seu time sob medida
---

O usuário quer montar (ou remontar) o OS dele. Conduza assim, com tom caloroso e em português do Brasil:

1. **Suba o Genesis** rodando, em segundo plano (background), o comando:

   ```
   python .genesis/sobe.py
   ```

   Isso prepara o ambiente (só na primeira vez) e abre a cena do Genesis no navegador,
   em `http://localhost:7799`. Se o navegador não abrir sozinho, mostre esse endereço.

2. **Explique pro usuário, em uma ou duas frases**, o que vai acontecer: ele vai fazer uma
   entrevista rápida na tela, e VOCÊ (o Claude Code dele) vai pesquisar na web e montar um
   time de agentes e skills sob medida, escrito do zero pro caso dele. Roda na assinatura
   dele, R$ 0 de API.

3. A entrevista e a montagem acontecem **na tela do navegador**. Quando terminar, o OS dele
   nasce aqui no repositório:
   - `.claude/agents/` — os especialistas dele, invocáveis
   - `.claude/skills/` — as automações sob medida
   - `contexto/` e `CLAUDE.md` — quem ele é (o cérebro do OS)
   - e ele cai no **painel do OS vivo** (`/painel`), onde vê o time dele.

4. Depois de montado, ele volta pra cá e é só pedir o que precisar ("monta o relatório da
   semana") ou rodar uma skill dele. Você já vai conhecer ele pelo `CLAUDE.md`.

Se ele quiser refazer o time, é só rodar `/config-os` de novo. As entregas em `producao/`
ficam intactas.
