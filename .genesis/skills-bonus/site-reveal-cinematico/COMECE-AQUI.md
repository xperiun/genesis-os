# Comece aqui — Site com Reveal Cinematográfico

Esta skill cria um **site de uma página** onde **cada rolagem avança um frame de um vídeo** (uma planilha virando dashboard, um produto se montando, uma câmera descendo numa cena), com o texto entrando em partes sincronizado. É o gênero "Apple product reveal". Dark, premium, uma cor-tema só.

Ela é **auto-suficiente**: o site inteiro já vem pronto dentro de `templates/` (você só troca marca, cor, textos e o vídeo). Serve muito bem como **portfólio** (mostrar seus dashboards/projetos) ou landing de um produto/serviço.

> **Pré-requisito único que você instala à parte:** o **Claude Code**. O resto (Node, ffmpeg, dependências) a própria skill configura pra você. Se ainda não tem o Claude Code, instale primeiro e volte aqui.

---

## O jeito fácil (dentro do Claude Code)

1. Abra o Claude Code na pasta onde quer trabalhar.
2. Digite:

   ```
   /site-reveal-cinematico
   ```

3. Responda as perguntas do intake (nome/marca, cor-tema, qual é o vídeo do reveal, seções).
4. Pronto. O Claude faz o setup, copia o template, troca tudo pela sua marca e te mostra o site rodando.

Foi pra isso que a skill existe: você conversa, ele constrói. As seções abaixo são pra quem quer entender o que acontece por baixo (ou fazer na mão).

---

## O que a skill instala/configura (setup)

Na primeira vez, o Claude roda o **preflight** e resolve o que faltar:

```bash
npm run preflight        # mostra o que está OK e o que falta
```

Os pré-requisitos:

| O quê | Pra quê | Como instalar |
|---|---|---|
| **Node 18+** | rodar o site (Vite) | https://nodejs.org (versão LTS) |
| **Dependências** (Vite, GSAP, Lenis) | o motor do site | `npm install` |
| **ffmpeg** | preparar o vídeo (re-encode + frames) | Windows: `winget install Gyan.FFmpeg` · Mac: `brew install ffmpeg` · Linux: `sudo apt install ffmpeg` |
| **Playwright** (opcional) | tirar screenshots pra revisão | `npm install` + `npx playwright install chromium` |

O Claude faz tudo isso por você quando roda a skill. Manualmente é só seguir a tabela.

---

## Rodar o site local

```bash
npm install
npm run dev        # abre em http://localhost:5173/
```

Editou HTML/CSS/JS? Só atualizar o navegador. O site já vem com um exemplo funcional (a consultoria fictícia "Cota Dados") pra você trocar em cima.

---

## Deixar seu (o que trocar)

O guia completo de swap está na [`SKILL.md`](SKILL.md) (seção "Swap checklist"). Resumo:

- **Marca** (logo, nav, footer, título): buscar "Cota Dados" no `index.html`.
- **Cor-tema:** tokens `--accent`, `--accent-2`, `--accent-glow` no `src/style.css`.
- **Textos** (beats do hero, stats, cases, seções): `index.html`.
- **Cases:** suas imagens em `public/dashs/` + a copy no `index.html`.
- **Vídeo do reveal:** `public/bg.mp4` (ver abaixo) + `public/poster.jpg` (1º frame).

---

## O vídeo do reveal (o coração)

O vídeo precisa ser **all-keyframe** (todo frame independente), senão treme ao rolar. Sempre passe pelo re-encode:

```bash
ffmpeg -y -i "SEU-VIDEO.mp4" -an -vf "scale=1280:-2" \
  -c:v libx264 -crf 30 -preset slow -g 1 -keyint_min 1 -sc_threshold 0 \
  -pix_fmt yuv420p -movflags +faststart public/bg.mp4
ffmpeg -y -i public/bg.mp4 -frames:v 1 -q:v 3 public/poster.jpg
```

Você tem dois caminhos pra conseguir esse vídeo:

### Opção A — Gerar por IA com Higgsfield (recomendada) ⭐

É o que dá o resultado "de agência" (planilha morta virando dashboard/automação, produto se montando no escuro). **A skill já vem pronta pra isso via MCP** — não precisa configurar nada além de conectar o Higgsfield.

1. Crie uma conta no **Higgsfield** (a geração de vídeo/imagem por IA é um recurso pago da plataforma — é o único custo, e é o que entrega o efeito premium).
2. **Conecte o conector Higgsfield no Claude Code** (pelas configurações de conectores do claude.ai, ou rodando `/mcp` numa sessão interativa).
3. Peça pro Claude gerar. Ele já sabe a receita (imagem-herói no Nano Banana Pro → clipes encadeados no Seedance → concatena → re-encode). O passo a passo técnico está em [`references/video-pipeline.md`](references/video-pipeline.md).

### Opção B — Traga seu próprio vídeo (100% grátis)

Não quer usar IA? O template funciona igual com **qualquer vídeo**:

- Um **screen-record** do seu dashboard abrindo/filtrando (grave a tela).
- Um render 3D, uma cena de câmera descendo, um produto girando.
- Qualquer mp4 com câmera relativamente estável.

Passe pelo re-encode all-keyframe acima e pronto. O motor, os beats e o design são os mesmos.

> **Resumindo:** o template e o motor são **grátis e completos**. O Higgsfield é **opcional**, mas é a melhor escolha pra quem quer o efeito de reveal generativo sem gravar nada — e a skill já está pronta pra usá-lo.

---

## Revisar antes de publicar (opcional)

Com o `npm run dev` rodando, em outro terminal:

```bash
npm run verify        # gera screenshots desktop + mobile em scripts/shots/
```

Abra as imagens e confira contra os checklists em [`references/audit-checklist.md`](references/audit-checklist.md). (Primeira vez: `npx playwright install chromium`.)

---

## Publicar

O site é estático. `npm run build` gera a pasta `dist/`. É só subir em qualquer host de estáticos:

- **Cloudflare Pages / Vercel / Netlify:** conecte o repositório (build `npm run build`, output `dist`) ou arraste a pasta `dist/`.

---

## Onde está o conhecimento

Tudo que a skill sabe mora em `references/`:

- [`motor.md`](references/motor.md) — como o scrub, os beats e o reveal funcionam (código).
- [`video-pipeline.md`](references/video-pipeline.md) — ffmpeg all-keyframe + geração Higgsfield/Seedance.
- [`audit-checklist.md`](references/audit-checklist.md) — as 4 lentes de auditoria + verification loop.
- [`receitas-e-gotchas.md`](references/receitas-e-gotchas.md) — receitas de CSS + armadilhas conhecidas.
- [`referencias-visuais.md`](references/referencias-visuais.md) — as referências do gênero e a decupagem.
- [`caso-real.md`](references/caso-real.md) — o caso de estudo completo de um build real.
