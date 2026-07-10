---
description: Monta (ou remonta) o seu OS, a entrevista que cria o seu time sob medida
---

O usuário quer montar (ou remontar) o OS dele. Conduza assim, com tom caloroso e em português do Brasil:

1. **Knowledge base primeiro (o passo zero).** ANTES da entrevista, peça pro usuário jogar os
   documentos do negócio dele (quem é, produtos, tom de voz, público, números, casos) na pasta
   `contexto/referencia/`. Essa pasta **já vem pronta no repo** (com um `README.md` explicando o
   que colocar), então só aponte ele pra ela, não precisa criar. Diga, em uma frase, que quanto
   mais real o material aqui, mais afiado o time sai, e que sem nada ele nasce só pelo que você
   contar na entrevista. Espere ele dizer que colocou (ou que quer seguir sem), e só então suba
   o Genesis.

2. **Suba o Genesis** rodando, em segundo plano (background), o comando:

   ```
   python .genesis/sobe.py
   ```

   Isso prepara o ambiente (só na primeira vez) e abre a cena do Genesis no navegador,
   em `http://localhost:7799`. Se o navegador não abrir sozinho, mostre esse endereço.

3. **Explique pro usuário, em uma ou duas frases**, o que vai acontecer: ele vai fazer uma
   entrevista rápida na tela, e VOCÊ (o Claude Code dele) vai LER o knowledge base dele em
   `contexto/referencia/` e pesquisar na web pra montar um time de agentes e skills sob medida,
   escrito do zero pro caso dele. Roda na assinatura dele, R$ 0 de API.

4. A entrevista e a montagem acontecem **na tela do navegador**. Quando terminar, o OS dele
   nasce aqui no repositório:
   - `.claude/agents/` — os especialistas dele, invocáveis
   - `.claude/skills/` — as automações sob medida
   - `contexto/` e `CLAUDE.md` — quem ele é (o cérebro do OS)
   - e ele cai no **painel do OS vivo** (`/painel`), onde vê o time dele.

5. Depois de montado, ele volta pra cá e é só pedir o que precisar ("monta o relatório da
   semana") ou rodar uma skill dele. Você já vai conhecer ele pelo `CLAUDE.md`.

Se ele quiser refazer o time, é só rodar `/config-os` de novo. As entregas em `producao/`
ficam intactas.
