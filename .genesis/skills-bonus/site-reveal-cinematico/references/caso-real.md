# Caso real — "Cota Dados" (o primeiro site feito com esta skill)

> Caso de estudo. Documenta o build de referência que hoje mora em `producao/sites/portfolio-bi-template/` (o **resultado**). Todo o **conhecimento** reutilizável está nas outras refs da skill (`motor.md`, `video-pipeline.md`, `audit-checklist.md`, `receitas-e-gotchas.md`, `referencias-visuais.md`); este doc é o "porquê" de cada decisão, contado como narrativa do build real. Os caminhos citados (`public/bg.mp4`, "raiz do projeto" etc.) se referem à pasta da produção.

Site portfólio scroll-driven de consultoria de BI. O hero é um vídeo de notebook que abre revelando um dashboard Power BI, controlado quadro a quadro pelo scroll (estilo "Apple product reveal"). Cada rolagem avança um frame do vídeo enquanto a copy troca em batidas.

Demo fictícia "Cota Dados" (dados 100% ilustrativos, setor BR genérico). DS autoral "Sinal no Ruído" (near-black `#0A0B0D` + lima `#C5F82A`).

---

## 1. A ideia

Referência: sites de reveal cinematográfico onde a rolagem controla um vídeo de produto quadro a quadro, com texto entrando em etapas por cima (ex: shorts de landing pages de hardware, notebooks, apps). O founder trouxe 2 shorts do YouTube como norte e o vídeo `bg-notebook-dashboard-v4-camera-fixa.mp4` (notebook fechado → tampa abre → dashboard aparece com painéis voando, câmera fixa, fundo near-black).

**Shorts de referência (o norte inicial):**
- https://www.youtube.com/shorts/A2b8F0IdbVo
- https://www.youtube.com/shorts/kzfvVizScuU

(O vídeo longo decupado depois está no §9.)

Decisões de fork tomadas no início:
- **Marca:** manter o personagem fictício "Cota Dados" (portfólio de consultoria, não Xperiun real).
- **Base:** clonar o projeto irmão `cota-dados-motion` (que já tinha o motor de scrub pronto) numa pasta nova, sem destruir o original.
- **Estrutura:** o reveal do notebook ocupa a rolagem inteira da primeira dobra (pin cinematográfico), texto entra por cima em etapas, depois vêm as seções de conteúdo.

---

## 2. Como o motor funciona

Stack: **Vite + GSAP ScrollTrigger + Lenis** (smooth scroll).

O truque central mora em `src/main.js`:

1. O vídeo é `<video>` fixo em tela cheia no fundo (`#bgv`), `muted playsinline preload="auto"`, com `poster.jpg` enquanto carrega.
2. Um `ScrollTrigger` **pina** a primeira dobra (`.rhero__pin`) por `innerHeight * 5.4` (5,4 telas de rolagem). Durante esse pin, o progresso 0→1 é mapeado direto pro `currentTime` do vídeo via `seek(p)`. É isso que faz "cada scroll = 1 frame".
3. Depois do pin, o vídeo **congela no último frame** (dashboard cheio) e as seções de conteúdo rolam por cima.

Por que **all-keyframe** importa: pra fazer scrub suave (pular pra qualquer `currentTime` sem travar), o vídeo precisa ter todos os frames como keyframe (I-frames). Vídeo normal usa P/B-frames e "treme" no scrub. Ver seção 4.

O scrub é **decouplado** do scroll global: o vídeo só roda no pin do hero, não no site inteiro. Isso deixa a experiência limpa (reveal concentrado na primeira dobra) e libera o resto da página pra rolar normal.

### Copy em beats (a narrativa que evolui)

Em vez de uma headline estática, o hero conta uma história em **4 batidas** sincronizadas com o notebook abrindo. Cada beat é um `.rh-beat` no HTML; o `main.js` tem um array `WIN` com as janelas de entrada/saída de cada um (em fração do progresso do pin):

| Beat | Momento do vídeo | Copy |
|---|---|---|
| 1 | notebook fechado | "Todo dado começa fechado." |
| 2 | tampa abrindo | "Trancado numa planilha que ninguém abre." |
| 3 | tela acende, painéis voando | "Até alguém traduzir em painel." |
| 4 | dashboard cheio | "Aí ele para de informar. E começa a decidir." + sub + CTA |

Cada beat faz cross-fade com blur/translate por palavra. Uma barra de progresso fina (`#rhProg`) aparece no rodapé durante o pin pra orientar o usuário ("ainda tem reveal pela frente").

---

## 3. Estrutura de arquivos

```
portfolio-bi-template/                        ← raiz do projeto (é o próprio site)
├── index.html                                ← markup (hero, impact, stats, cases, capacidades, sobre, contato, footer)
├── src/
│   ├── main.js                               ← motor: Lenis, scrub do vídeo, beats, impact, nav ativa, form
│   ├── style.css                             ← tokens + layout base
│   ├── glass.css                             ← superfícies glass + botões
│   └── enhance.css                           ← craft de motion, reveal-hero, cases, progress bar, form
├── public/
│   ├── bg.mp4                                ← vídeo do reveal (all-keyframe, ~2MB) — GITIGNORED (*.mp4)
│   ├── poster.jpg                            ← poster do vídeo (1º frame)
│   ├── favicon.svg
│   └── dashs/*.jpg                           ← 5 screenshots de dashboard pros cases
├── bg-notebook-dashboard-v4-camera-fixa.mp4  ← vídeo-fonte do reveal (regenera o bg.mp4) — GITIGNORED
├── referencia/                               ← frames curados das referências visuais (.jpg)
└── README.md                                 ← nota enxuta (é o resultado; o conhecimento mora na skill)
```

> O conhecimento (motor, pipeline, auditoria, receitas, decupagem) foi movido pra skill `/site-reveal-cinematico`. Este caso-real.md é o log narrativo do build; as receitas técnicas estão em `motor.md` / `receitas-e-gotchas.md` / `video-pipeline.md` / `audit-checklist.md`.

**Atenção:** `bg.mp4` e o vídeo-fonte são ignorados pelo git (`*.mp4` no `.gitignore` da raiz do repo, vídeos são pesados demais). Quem clonar precisa re-gerar o `bg.mp4` a partir do fonte (ver seção 4). Se o fonte também sumir num clone, pedir pro founder.

---

## 4. O vídeo (re-encode obrigatório)

O vídeo bruto precisa virar **all-keyframe** antes de servir, senão trava no scrub. Comando usado (fonte na pasta pai):

```bash
# rodar da raiz do projeto (portfolio-bi-template/)
ffmpeg -y -i "bg-notebook-dashboard-v4-camera-fixa.mp4" \
  -an -vf "scale=1280:-2" \
  -c:v libx264 -crf 30 -preset slow \
  -g 1 -keyint_min 1 -sc_threshold 0 \
  -pix_fmt yuv420p -movflags +faststart \
  "public/bg.mp4"
```

- `-g 1 -keyint_min 1 -sc_threshold 0` → força **todo frame ser keyframe** (241 I-frames, zero P/B).
- `-an` → sem áudio (o vídeo é `muted`).
- `scale=1280` + `crf 30` → de **16MB pra ~2MB** sem perda visível (câmera fixa, fundo preto comprime bem).

Validar all-keyframe:
```bash
ffprobe -v error -select_streams v -show_entries frame=pict_type -of csv=p=0 public/bg.mp4 | grep -cE "P|B"   # deve dar 0
```

---

## 5. Auditoria (4 especialistas em paralelo)

Depois do site pronto, rodei uma auditoria com 4 agents dos xsquads em paralelo (cada um leu a própria persona + os screenshots reais desktop/mobile + o código):

| Lente | Agent | Nota inicial |
|---|---|---|
| Copy | copy-chief | 8.5 |
| Layout | especialista layout/CRO | 8.0 |
| UI/Visual | design-chief + ui-engineer | 7.5 |
| CRO | especialista layout/CRO | 6.5 |
| UX | ux-designer | 6.5 |
| Performance | especialista layout/CRO | 5.5 |

**Consenso dos 4 (furo nº1):** no mobile o vídeo `fixed` vazava atrás do conteúdo e destruía stats/impact/contato. Foi o maior salto de qualidade disponível.

Método de captura: script Playwright (`.scratch/shoot.cjs`) tira screenshots em 11 pontos de scroll (topo → beats do reveal → cada seção), desktop 1440x900 e mobile 390x844. Salva em `.scratch/shots/`.

---

## 6. Melhorias aplicadas

### P0 (graves)
- **Mobile bg-leak:** seções pós-hero ganham `background:var(--bg)` sólido no mobile (`style.css`, `@media max-width:900px`). O dashboard congelado atrás é luxo de desktop; no mobile virava ruído. Shade cap subiu pra 0.95 no mobile / 0.82 no desktop (`main.js setupBgShade`).
- **Contraste texto-sobre-dashboard (desktop):** shade mais forte + borda direita do `.bg-tint` reforçada.
- **Performance:** vídeo 16MB → 2MB (seção 4). Preloader revela no 1º frame (`loadeddata`), não espera o buffer inteiro; fallback baixou pra 2,5s.
- **Acessibilidade:** token `--ink-2b` (#8A9288, passa WCAG AA) pros textos informativos que falhavam com `--ink-3`; `:focus-visible` global; Lenis desligado sob `prefers-reduced-motion`; `aria-hidden` + `tabindex="-1"` no vídeo decorativo.
- **SEO:** meta description + OG/Twitter tags (link no WhatsApp/LinkedIn agora tem preview); dois `<h1>` no hero viraram um `<h1>` + `<div role="text">`; header dos cases virou `<h2>`.

### P1/P2 (polish)
- Barra de progresso durante o pin do hero.
- Thumbnails de case dessaturados em repouso (`saturate(.72)`), cor plena no hover — paravam de brigar com a lima.
- Nav com estado de seção ativa (IntersectionObserver → `.active` lima).
- Título de contato saindo de baixo da nav (`scroll-margin-top` + clamp menor).
- Eyebrow órfã no mobile corrigida, "Capacidades" clipando (clamp reduzido), `100vh`→`100svh` nos pins.
- Unidades das stats consistentes, sparkline contida no mobile, botões de contato empilhados no mobile.
- Form de baixa fricção no contato (nome + pergunta, submit demo) + WhatsApp/LinkedIn/e-mail como alternativa.
- CSS morto (`.hgallery`/`.hslide`) removido.

### Copy (do copy-chief)
- Cap 03 "IA aplicada" tinha frase truncada + "Claude e IA" redundante → reescrita.
- Fórmula "deixa de ser X e vira Y" repetia em 3 cases → variada em Logística e CRM.
- Contato tinha "resposta" 3x em 2 frases → lead reescrito.
- Stat R$ 6,2M "decisões destravadas (ilustrativo)" (métrica difusa) → "Em compras e vendas lidos nos painéis" (volume crível).

---

### Refinamentos v2 (inspirados na decupagem, ver §9)

Wins baratos trazidos da referência (ABYSSAL/AURORA), sem clonar nem refazer:
- **Camada ambient** (`.ambient` em `enhance.css`) — 3 glows blur à deriva (lima + azul frio) atrás do conteúdo, dão profundidade tipo bokeh. Desligados sob reduced-motion.
- **Stepper rotulado do reveal** (`#rhSteps`) — 4 estágios "dado bruto → modelo → painel → decisão" no rodapé durante o pin, o atual aceso em lima. Device de "profundidade" igual ao "AT 1,000 METERS" do ABYSSAL. Ancora a narrativa dos beats e resolve wayfinding.
- **Seção statement "produto flutuando"** (`.statement`, entre cases e capacidades) — dashboard num frame glass com tilt 3D + glow + chip lima "atualizado há 2 min", flutuando, ao lado da frase-soco "Uma tela. E a reunião inteira decide por ela." Lição do AURORA & NOIR (produto isolado + uma frase). Palco escurecido por scrim radial pra o flutuante não competir com o dashboard congelado atrás.

## 7. Decisões de produto

- **Duração do reveal:** mantido lento (5,4 telas) por escolha do founder, mesmo os agents de UX/CRO querendo encurtar (dizem que enterra o CTA). Compensado com a barra de progresso + o CTA "Falar comigo" fixo na nav (sempre disponível).
- **Thumbnails dessaturados só em repouso:** o dashboard É o produto, então mostra com alguma vida no hover em vez de matar a cor de vez.

---

## 8. Como rodar e iterar

```bash
npm install
npm run dev        # http://localhost:5173/
npm run build      # gera dist/
```

Iterar no visual: mudança em HTML/CSS/JS pega no refresh (Vite HMR). Mudança no vídeo → re-encodar (seção 4) e dar refresh.

Screenshots de verificação:
```bash
node .scratch/shoot.cjs   # gera .scratch/shots/ (desktop + mobile, 11 pontos cada)
```

Ajustar o pacing do reveal: `innerHeight * 5.4` no `main.js` (`setupRevealHero`), cada +1 ≈ 1 tela a mais de rolagem.
Ajustar os beats: array `WIN` no mesmo bloco (janelas de entrada/saída de cada beat).

---

## 9. Referência visual (decupagem)

**Vídeo:** ["Claude Fable 5 Built a $10K Website in Minutes"](https://youtu.be/m-f56P_L660) — Zubair Trabzada (AI Workshop), 15:17.
Frames de referência salvos em `referencia/` (curados do vídeo, ~854px). Contact sheet dos 16 frames em `referencia/00-contact-sheet-16frames.jpg`.

### O que é

Workshop construindo **3 sites cinematográficos premium** com Claude Fable 5 + Higgsfield MCP. É o mesmo gênero do nosso notebook-reveal (dark cinematic, scroll-driven, vídeo scrubbed). Serve de norte pra elevar o nosso.

### Os 3 sites decupados

1. **PROOF OF WORK** (`referencia/01-...`) — portfólio pessoal dark. Fundo cinematográfico com lâmpadas quentes e bokeh, hero colossal "PROOF OF WORK", faixa "SELECTED WORK" com cards ("CITEVUE", "SCROLL-CINEMATIC", "199 SKILLS"). O card "SCROLL-CINEMATIC" literalmente descreve o efeito de scroll-scrubbed que ele usa. Popup de "novidade" no canto. **É o irmão direto do nosso** (portfólio + scroll-cinematic).

2. **AURORA & NOIR** (`referencia/02-...`) — relógio de luxo. Ouro sobre preto absoluto, produto flutuando com partículas douradas, tagline "Darkness. Perfected." Lição: **produto único no centro + uma frase-soco + fundo preto com glow da cor-tema**. Menos é mais.

3. **ABYSSAL** (`referencia/05,06,07-...`) — expedição submarina fictícia. **O mais próximo do nosso motor.** Um submersível (EREBUS) desce pelo oceano enquanto o texto entra em beats sincronizados: *"AT 1,000 METERS, PRESSURE IS 100× THE SURFACE"*. Tem faixa de stats gigantes com labels mono (`4.000 / 96H / 8 / 12KW`), glow ciano, tipografia condensada. É literalmente a nossa estrutura (reveal + beats + stats) em outro tema.

Também aparece um dashboard "AI WORKSHOP OS" (node graph colorido, `referencia/04-...`) e uma editorial de moda gerada no Higgsfield (`referencia/03-...`).

### Padrões replicáveis (o que trazer pro nosso)

- **Beats de texto sobre o reveal** — o ABYSSAL confirma nossa decisão: texto que evolui em batidas conforme a cena se monta é o padrão premium. Estamos no caminho certo.
- **Frase-soco por seção** — "Darkness. Perfected." / "AT 1,000 METERS...". Copy curtíssima e cinematográfica. Nosso hero em beats já faz isso; dá pra apertar o resto do site nessa direção.
- **Stats colossais com label mono** — idêntico ao que temos. Validado.
- **Marca fictícia premium com one-liner** — AURORA & NOIR, ABYSSAL, PROOF OF WORK. Cada uma é uma marca inventada com posicionamento afiado. Nosso "Cota Dados" segue a mesma lógica.
- **Fundo preto + 1 cor-tema + glow/partículas** — disciplina de paleta. O nosso (near-black + lima) está alinhado.

### A técnica de geração do vídeo (Higgsfield + Seedance)

O prompt do ABYSSAL (`referencia/` frame do Claude Code) revela **como fazer o vídeo do reveal do zero**, útil se quisermos regenerar o nosso notebook via IA em vez de render 3D:

1. Gera **uma imagem-herói de referência** do produto no Higgsfield (ex: Nano Banana Pro, 16:9).
2. Encadeia **~5 clipes Seedance 2.0** (std, 1080p, ~8-10s, sem áudio) passando a imagem-herói como referência em todos, pra o produto ser idêntico em todos os clipes.
3. **Truque central:** usa o **frame final de cada clipe como frame inicial do próximo** (`start_image` / `end_image` do Seedance). Assim os 5 clipes viram **um vídeo contínuo e sem emenda** — exatamente o que precisa pro scroll-scrub ficar liso.
4. Estrutura de takes citada: HERO ORBIT → MACRO FLYTHROUGH → EXPLODED ASSEMBLY (câmera orbita, entra no detalhe, os componentes se montam).

Ou seja: nosso `bg-notebook-dashboard-v4-camera-fixa.mp4` (render 3D) poderia ser regenerado por esse pipeline Higgsfield/Seedance se quisermos iterar o reveal sem depender de render externo.

---

## 10. Pendências

- WhatsApp está `wa.me/5500000000000` e LinkedIn `#` (placeholders). Trocar pelos reais quando for pra produção.
- O form de contato tem submit **demo** (só mostra confirmação, não envia). Pra produção, apontar pra um endpoint real.
- `bg.mp4` não está no git (gitignored). Re-gerar via ffmpeg (seção 4) em cada clone novo.
