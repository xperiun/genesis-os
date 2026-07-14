# Referências visuais

As referências que definiram o gênero desta skill. Guardar aqui pra alimentar novos sites.

> **Decupagem completa + método:** [`pack-fable5-decupagem.md`](pack-fable5-decupagem.md) tem a extração integral do "One-Prompt Website Pack" (as 5 regras do método, os 3 arquétipos de prompt — produto / jornada / portfólio —, as pro-tips e o gap analysis). Os **frames de referência** dos sites do vídeo (ABYSSAL com HUD, AURUM macro, portfólio, Awwwards/SEROTONINN) estão em [`pack-frames/`](pack-frames/). O PDF original está nesta pasta (`Fable5-Higgsfield-Website-Prompt-Pack.pdf`).

## Implementação de referência viva (estudar antes de começar)

O caso de estudo completo do primeiro build (construção + auditoria de 4 lentes + decisões + refinamentos) está em [`caso-real.md`](caso-real.md), aqui na skill. O **resultado** (o site pronto) mora em [`producao/sites/portfolio-bi-template/`](../../../../producao/sites/portfolio-bi-template/), mas isso é só o output, o conhecimento é aqui. O template em `templates/` é uma cópia desse build.

## Links

**Shorts que originaram a ideia** (o efeito "cada scroll rola um frame do vídeo do dashboard"):
- https://www.youtube.com/shorts/A2b8F0IdbVo
- https://www.youtube.com/shorts/kzfvVizScuU

**Vídeo decupado** (workshop construindo 3 sites cinematográficos premium com Claude Fable 5 + Higgsfield):
- https://youtu.be/m-f56P_L660 — "Claude Fable 5 Built a $10K Website in Minutes", Zubair Trabzada, 15:17.

> Pra decupar um vídeo de referência novo, usar a skill `/resumir-video` no modo visual (baixa em baixa resolução, fatia frames com ffmpeg, analisa a edição/identidade). Salvar os frames curados numa pasta `referencia/` do projeto.

## Decupagem — os 3 sites do vídeo

1. **PROOF OF WORK** — portfólio pessoal dark. Fundo cinematográfico com lâmpadas quentes e bokeh, hero colossal, faixa "SELECTED WORK" com cards. Um card literalmente chamado "SCROLL-CINEMATIC" descrevendo o efeito. É o irmão direto de um portfólio feito com esta skill.

2. **AURORA & NOIR** — relógio de luxo. Ouro sobre preto absoluto, produto flutuando com partículas, tagline "Darkness. Perfected." Lição: **produto único no centro + uma frase-soco + preto com glow da cor-tema**. Virou a seção `.statement` ("produto flutuando").

3. **ABYSSAL** — expedição submarina fictícia. Submersível desce pelo oceano enquanto o texto entra em beats: "AT 1,000 METERS, PRESSURE IS 100× THE SURFACE". Stats gigantes com label mono, glow ciano. **É a estrutura da skill (reveal + beats + stats + medidor de profundidade) em outro tema.** O medidor virou o `.rh-steps` (stepper rotulado).

## Padrões replicáveis (o que faz o gênero)

- **Vídeo scrubbed pelo scroll** — o motor. Cada scroll avança um frame do asset se montando.
- **Texto em beats** — a copy evolui em batidas sincronizadas com o asset, não fica estática.
- **Medidor/stepper de profundidade** — ancora a narrativa e resolve wayfinding ("AT 1,000 METERS" / "dado → decisão").
- **Momento "produto flutuando"** — asset isolado num frame flutuante + uma frase-soco só.
- **Stats colossais** com label mono.
- **Marca fictícia premium + one-liner afiado** ("Darkness. Perfected.", "Dados parados viram decisão").
- **Fundo preto + 1 cor-tema + glow/partículas ambient** — disciplina de paleta é o que faz parecer premium/"$10K".

## Como os assets são gerados na referência

O workshop gera os vídeos/imagens com **Higgsfield MCP + Seedance 2.0**, encadeando clipes (frame final de um = inicial do próximo) pra um reveal contínuo sem emenda. Receita completa em [`video-pipeline.md`](video-pipeline.md).
