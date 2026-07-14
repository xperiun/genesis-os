---
name: site-reveal-cinematico
description: Cria sites scroll-driven com reveal cinematográfico, um vídeo controlado quadro a quadro pelo scroll (estilo "Apple product reveal"), com texto que evolui em beats, stats colossais, galeria de cases e momento "produto flutuando". Stack Vite + GSAP ScrollTrigger + Lenis. Use quando pedirem "site com reveal", "aquele efeito de rolar e o vídeo abrir", "scroll cinematográfico", "site tipo Apple", "landing com vídeo scrubbed", "portfólio dark cinematográfico", ou mostrarem uma referência daquele gênero (vídeo/produto que se monta conforme a rolagem).
---

# Site Reveal Cinematográfico

Sites onde **cada scroll avança um frame de um vídeo** (notebook abrindo, produto se montando, câmera descendo), com o texto entrando em **beats** sincronizados. É o gênero "Apple product reveal" / "scroll-cinematic". Dark, premium, uma cor-tema só.

A skill é **self-contained**: o scaffold completo e funcional está em [`templates/`](templates/) (é só copiar e trocar). Não depende da produção. O **conhecimento** todo mora aqui (SKILL.md + `references/`).

O `templates/` é uma cópia do build **v1 (reveal de notebook)**: um notebook que abre revelando um dashboard, câmera fixa, copy em 1ª pessoa, pronto pra um aluno usar como portfólio/consultoria. Existe também um estilo alternativo **v2 (reveal de dados se materializando)**, câmera em órbita, vídeo gerado por IA. Os dois builds de exemplo (v1 e v2) vivem em [`producao/sites/portfolio-bi-template/`](../../../producao/sites/portfolio-bi-template/) (o **resultado**, pra comparar). O caso de estudo completo (construção + auditoria + decisões) está em [`references/caso-real.md`](references/caso-real.md).

## Quando usar

- Pedido explícito: "site com reveal", "scroll cinematográfico", "vídeo que abre conforme rola", "tipo Apple", "landing com vídeo scrubbed".
- O usuário mostra uma referência daquele gênero (produto/cena que se monta na rolagem).
- Portfólio, landing de produto premium, apresentação de um asset visual forte (dashboard, produto, cena 3D).

## Quando NÃO usar

- Site institucional comum, blog, e-commerce, app com muitas telas. Esta skill é pra **uma página** cinematográfica com um asset-herói forte, não pra um site multi-página.
- LP de campanha de tráfego pago da Xperiun com regras próprias (GTM, popup AC, deploy em `site-xperiun/lp/`). Pra isso, ver as skills de funil. Esta aqui é pra o gênero "reveal", que é outro animal.

## Stack e como roda

**Vite + GSAP ScrollTrigger + Lenis** (smooth scroll). Roda local:
```bash
npm install
npm run dev        # http://localhost:5173/
npm run build      # dist/
```

O coração está em `src/main.js`. Detalhamento do motor (scrub decouplado, beats, stepper): [`references/motor.md`](references/motor.md).

## Fluxo de trabalho

### 0. Setup (primeira vez / quando roda fora do xperiun-os)

Antes de tudo, garantir os pré-requisitos. O template é portável e traz um preflight que reporta o que falta:

```bash
node scripts/preflight.mjs   # (ou npm run preflight, depois do npm install)
```

Checa e orienta: **Node 18+**, dependências npm, **ffmpeg** (necessário pro vídeo, comando de instalar por SO), e **Playwright** (opcional, só pro verification loop). Resolver o que estiver faltando antes de prosseguir:
- `npm install` (deps do site)
- ffmpeg: Windows `winget install Gyan.FFmpeg` · Mac `brew install ffmpeg` · Linux `sudo apt install ffmpeg`
- Playwright (se for rodar o verify): `npx playwright install chromium`

**Higgsfield é opcional** (é o caminho recomendado pra gerar o vídeo por IA, ver §Vídeo). Configura-se à parte conectando o conector via MCP no Claude Code, não é pré-requisito pra rodar o site. Guia humano completo em [`COMECE-AQUI.md`](COMECE-AQUI.md).

> **Uso como brinde / dentro do genesis:** esta skill é self-contained e portátil (sem caminhos absolutos nem dependência do xperiun-os). Pode ser distribuída como template gratuito ou empacotada num pacote maior. O único requisito que o aluno instala à parte é o **Claude Code**; o resto a skill configura. Ver `COMECE-AQUI.md`.

### 1. Intake PRIMEIRO (não escrever código antes)

Perguntar em **texto puro** (nunca AskUserQuestion):
- **Marca/tema:** nome (pode ser fictício), setor, tom. Ex: "Cota Dados", consultoria de BI.
- **Asset-herói:** qual vídeo vai ser scrubbed? Já existe (render/gravação) ou precisa gerar? (ver §Vídeo)
- **Cor-tema:** 1 cor de acento sobre near-black. Se tiver imagem de referência, extrair o hex dela (não chutar).
- **Seções:** o padrão é hero-reveal → impact → stats → cases → statement → capacidades → sobre → contato. Confirmar quais fazem sentido.
- **A narrativa dos beats:** que história o texto conta enquanto o asset se monta? (ver §Beats)

### 2. Scaffold a partir do template

Copiar `templates/` pra pasta de destino (`producao/sites/<slug>/` por padrão, ou onde o usuário pedir). Rodar `npm install`.

O template já vem com o site "Cota Dados" inteiro funcionando (é a implementação de referência). **Não construir do zero**, partir dele e trocar.

### 3. Swap checklist (o que trocar do template)

| O quê | Onde |
|---|---|
| Nome da marca (logo, nav, footer, preloader, título) | `index.html` (buscar "Cota Dados"/"CotaDados") |
| Cor-tema | `src/style.css` tokens `--accent`, `--accent-2`, `--accent-glow` |
| Vídeo do reveal | `public/bg.mp4` (re-encodar all-keyframe, ver §Vídeo) + `public/poster.jpg` (1º frame) |
| Copy dos 4 beats | `index.html` `.rh-beat` + timing em `src/main.js` array `WIN` |
| Labels do stepper | `index.html` `.rh-steps` (ex: "dado bruto → modelo → painel → decisão") |
| Stats (números + labels) | `index.html` seção `.stats-sec` |
| Cases (imagens + copy) | `public/dashs/*.jpg` + `index.html` seção `.cases` |
| Frase-soco do statement | `index.html` `.statement` `.stmt__line` |
| Copy das seções (capacidades, sobre, contato) | `index.html` |
| Meta/SEO/OG | `index.html` `<head>` |

### 4. Beats (a narrativa que evolui)

O hero conta uma história em **4 batidas** sincronizadas com o asset se montando. Cada `.rh-beat` no HTML, timing no array `WIN` do `main.js` (janelas `[entra_ini, entra_fim, sai_ini, sai_fim]` em fração do pin). Regra de copy: **frase-soco curtíssima e cinematográfica** por beat, sem vício de IA. Exemplo (BI/notebook):
1. fechado → "Todo dado começa fechado."
2. abrindo → "Trancado numa planilha que ninguém abre."
3. tela acende → "Até alguém traduzir em painel."
4. asset cheio → "Aí ele para de informar. E começa a decidir." + sub + CTA

### 5. Vídeo (asset-herói)

Detalhamento: [`references/video-pipeline.md`](references/video-pipeline.md). Resumo:
- O vídeo **precisa ser all-keyframe** (todo frame I-frame), senão treme no scrub. Re-encodar com ffmpeg (`-g 1 -keyint_min 1 -sc_threshold 0`).
- Alvo leve: 1280px, CRF ~30, sem áudio → ~2-4MB (LCP e mobile agradecem).
- **Gerar do zero via IA:** Higgsfield MCP (imagem-herói de referência) + Seedance 2.0 (clipes encadeados, frame final de um = inicial do próximo → descida/reveal contínuo sem emenda). Receita completa no `references/video-pipeline.md`.
- `*.mp4` é gitignored no repo. Guardar o vídeo-fonte junto do projeto pra regenerar.

### 6. Auditoria + verification loop (INVIOLÁVEL antes de declarar pronto)

Rodar o **verification loop** (screenshots no browser, ver `references/audit-checklist.md`):
```bash
node scripts/shoot.cjs   # gera .scratch/shots/ desktop + mobile em N pontos de scroll
```
Ler os PNGs, criticar contra o checklist, corrigir os 3-5 piores, repetir (máx 3 iterações).

Pra elevar de "bom" a "200%", rodar a **auditoria de 4 lentes em paralelo** (UI/visual, UX/interação, copy, layout/CRO/perf) via Agent tool, cada um lendo os screenshots + código. Foi o que levou a referência de 7.5 pra ~9. O checklist consolidado (P0 mobile bg-leak, contraste sobre asset, a11y, perf, SEO) está em [`references/audit-checklist.md`](references/audit-checklist.md).

## Design system — regra

DS **autoral dark cinematográfico** ("Sinal no Ruído" no template): near-black (`#0A0B0D`) + **uma** cor de acento. Disciplina de paleta é o que faz parecer premium. Nunca inventar segunda cor forte. Sempre ancorar nos tokens `--color-*` do `src/style.css`.

Esta skill é **self-contained**: tudo que precisa está na própria pasta (`templates/` + `references/`). Não depende de outras skills. O DS aqui é distinto do `/criar-design` de propósito (é um gênero visual específico), então não usa os templates `_xperiun`.

## Padrões replicáveis (da decupagem das referências)

Ver [`references/referencias-visuais.md`](references/referencias-visuais.md) pros links e a decupagem. Os padrões que definem o gênero:
- **Vídeo scrubbed pelo scroll** (o motor).
- **Texto em beats** que evolui conforme o asset se monta.
- **Stepper/medidor de profundidade** ancorando a narrativa ("AT 1,000 METERS" / "dado → decisão").
- **Momento "produto flutuando"** (asset isolado + uma frase-soco).
- **Stats colossais** com label mono.
- **Marca fictícia premium + one-liner** ("Darkness. Perfected.").
- **Fundo preto + 1 cor + glow/partículas ambient** pra profundidade.

## Aprendizados de build (Marina Vhilar, 2026-07-13)

Portfólio fictício "Marina Vhilar" (arquiteta de dados & automação), tema âmbar `#FF7A1A`, vídeo Excel morto → dashboard vivo → esteira de automação. Lições reutilizáveis:

1. **Local default mudou pra `producao/sites/<slug>/`** (era `producao/diversos/`). Os builds de exemplo (`portfolio-bi-template`) também moram lá agora.

2. **Variante "vídeo cobre a página inteira".** Além do hero-pin-depois-congela, dá pra deixar o vídeo full-bleed visível o site todo: baixar o cap do `bg-shade` (de 0.82 pra ~0.70 no desktop) e as seções passam por cima do frame congelado. Foi o pedido do founder aqui ("página coberta pelo vídeo, texto por cima", referência Northline que é full-bleed estático + texto).

3. **Cor de acento NUNCA em headline grande sobre imagem/vídeo quente (INVIOLÁVEL).** O vídeo esquenta pro âmbar e a palavra em `--accent` (laranja) some no fundo. Regra: **display headline = branco/creme sobre imagem**; o acento fica no chrome (eyebrow, nav, botões, stats, labels) e só em headline sobre fundo sólido escuro. Aplicar em `.rh-line em` (beats do hero), `.ph-title em` (Sobre), e avaliar `.stmt__line em` / `.buy__title em`. Trocar `color:var(--accent)` por `color:inherit`.

4. **Section-head: eyebrow é `<span class="secnum">`, NUNCA `<h2 class="secnum">`.** Um `h2.secnum` herda `font-size` de título (`.section-head h2`) e o rótulo `[ 01 — ... ]` renderiza gigante. Padrão certo (já no template): `.section-head__txt` > `span.secnum` + `h2` (título real) + `p.lead` (subtítulo). CSS defensivo no template: `.section-head h2.secnum{...mono pequeno...}`.

5. **Seção "Sobre" estilo Northline (retrato editorial full-bleed).** Pessoa à direita, espaço negativo escuro à esquerda pro texto, headline branca gigante + kicker + fio + subcopy + botões. **Foto limpa, SEM véu preto** (o lado esquerdo do retrato já é escuro; `.ph-scrim{background:none}`). **Pinar a seção e revelar o texto EM PARTES no scroll**: fatiar em `.ph-part` (título linha a linha, subcopy frase a frase) e revelar auto-espaçado ao longo do pin (`seg(p, 0.04+i*span, ...)`). Começa só com a foto parada + o eyebrow. Detalhe do reveal em [`references/motor.md`](references/motor.md).

6. **Retratos Soul (soul_2) assam texto/gibberish falso na imagem.** No prompt, negativos fortes (`no text, no letters, no numbers, no watermark, no screens, no signage`) e fundo de espaço negativo limpo (bokeh/orbs, não "telas/dashboards" que disparam UI falsa). Se sobrar, assar escurecimento gradiente no lado do texto: `ffmpeg -vf "geq=lum='lum(X,Y)*clip((X/W-0.14)*2.0,0.04,1)':..."`. Gerar 3-4 e escolher. Pra consistência de identidade, passar um retrato anterior como `medias[image]`.

7. **Botão de nav numa seção aponta pra FRENTE.** "Ver os cases" numa seção abaixo dos cases faz o site subir (burrice). Seção "Sobre" perto do fim → CTA = "Falar comigo" (contato) + "LinkedIn", não link pra seção anterior.

8. **h1 do hero 100% no primeiro frame.** `WIN[0]` com `inB <= 0` (ex: `[-0.12,-0.02,0.18,0.26]`) faz o beat 1 nascer pronto no repouso, sem resíduo de blur/movimento. Founder prefere ancorado (headline presente já ao carregar), não cold-open vazio. Idem o eyebrow: `seg(p,-0.05,-0.01)`.

9. **Higgsfield MCP — pipeline confirmado (ver [`references/video-pipeline.md`](references/video-pipeline.md)).** `generate_image`/`generate_video` exigem `model` **e** `prompt` DENTRO de `params`. Recusar preset recomendado via `declined_preset_id` dentro de `params` + reformular o prompt (tirar palavras que casam com o preset, ex "in the dark"). Usar o `job_id` da imagem direto como `start_image`. Encadear clipes: extrair último frame → `media_upload` → PUT bytes → `media_confirm` → usar como `start_image` do próximo. Modelos: `nano_banana_pro` (imagem-herói 4k) + `soul_2` (retrato) + `seedance_2_0` (clipes 1080p std, `generate_audio:false`). Resultado: ~6.6MB / 16s all-keyframe.

## Estrutura da skill

```
site-reveal-cinematico/
├── SKILL.md                        ← este arquivo
├── references/
│   ├── motor.md                    ← como o scrub/beats/stepper/statement funcionam (código)
│   ├── receitas-e-gotchas.md       ← receitas de CSS-craft + armadilhas conhecidas
│   ├── video-pipeline.md           ← ffmpeg all-keyframe + geração Higgsfield/Seedance
│   ├── audit-checklist.md          ← as 4 lentes + P0/P1/P2 + verification loop
│   ├── referencias-visuais.md      ← links das referências + decupagem dos padrões
│   ├── pack-fable5-decupagem.md    ← decupagem COMPLETA do "One-Prompt Website Pack" (método + 3 arquétipos de prompt + gap analysis)
│   ├── pack-frames/                ← frames de referência dos sites do vídeo (ABYSSAL, AURUM, portfólio, Awwwards)
│   ├── Fable5-Higgsfield-Website-Prompt-Pack.pdf  ← o PDF original (imagem; texto extraído no .md acima)
│   └── caso-real.md                ← caso de estudo do 1º build (Cota Dados): construção + auditoria + decisões
└── templates/                      ← o site inteiro funcionando (copiar e trocar). Cópia do build v1 (reveal de notebook).
    ├── index.html                  ← copy em 1ª pessoa (portfólio do aluno)
    ├── README.md                   ← guia "como tornar seu" (viaja com o scaffold pro aluno)
    ├── src/{main.js,style.css,glass.css,enhance.css}
    ├── public/{favicon.svg,poster.jpg,dashs/*.jpg}   ← 9 dashboards de exemplo (fin/RH/comercial/logística)
    ├── scripts/shoot.cjs           ← verification loop (Playwright)
    └── package.json
```

> **O `bg.mp4` NÃO vem no scaffold** (`*.mp4` é gitignored no repo, vídeos são pesados). Ao scaffoldar um site novo, gerar o vídeo do reveal via `references/video-pipeline.md` (Higgsfield + Seedance) ou trazer um pronto, e sempre passar pelo re-encode all-keyframe. O `poster.jpg` (1º frame do reveal do notebook) vem como preview.
