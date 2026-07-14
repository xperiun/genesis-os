# Motor — como o scrub, os beats, o stepper e o statement funcionam

Tudo em `src/main.js`. Stack: Lenis (smooth scroll) + GSAP ScrollTrigger.

> **Duas gerações do motor.** O template padrão (v1/v2) usa **scrub de `<video>`** (§1 abaixo). O **build v3** (pack-level, ver `pack-fable5-decupagem.md`) reconstruiu pra **canvas frame-sequence** (§0), que é o jeito Apple/Awwwards e o alvo de qualidade. Código real do canvas: `producao/sites/portfolio-bi-template/v3/src/main.js`.

## 0. Scrub via CANVAS frame-sequence (o jeito pack-level, v3)

O `<video>.currentTime` trema no scrub (o decoder tem que decodificar do keyframe anterior). O jeito Apple/Awwwards é **desenhar frames num `<canvas>`** por posição de scroll: buttery e determinístico. Passos:

1. **Extrair o vídeo em N frames** (imagens) com ffmpeg: `ffmpeg -i journey.mp4 -vf "fps=8,scale=1280:-1" -q:v 4 public/frames/f_%04d.jpg`. ~8fps sobre 24s = ~193 frames (~13MB). Frames (`.jpg`) NÃO são gitignored (só `.mp4`), então viajam no repo.
2. **Preload** todos os `Image()` (gate o preloader até ~60% carregado).
3. **Desenhar** o frame do índice = `progresso * (N-1)` num canvas fixo full-screen, cover-fit, com DPR:
```js
function drawFrame(idx) {
  const img = imgs[clamp(Math.round(idx),0,N-1)];
  if (!img || !img.complete) return;
  const s = Math.max(cw/img.naturalWidth, ch/img.naturalHeight);
  const w = img.naturalWidth*s, h = img.naturalHeight*s;
  ctx.drawImage(img, (cw-w)/2, (ch-h)/2, w, h);
}
// no pin: onUpdate: self => drawFrame(self.progress * (N-1))
```
4. `sizeCanvas()` no resize seta `canvas.width/height` com DPR e redesenha.

**A jornada scruba a página inteira** (não só um hero pin): a pin da `.journey` roda por `innerHeight*6` e o progresso 0→1 mapeia a jornada de 24s inteira. Sobre ela: beats editoriais + HUD + color-grade (§0.1). Depois da pin, o frame congela e o conteúdo rola por cima com `bg-shade`.

### 0.1 Dispositivos de scroll do v3 (todos dirigidos pelo mesmo `render(p)`)
- **HUD medidor** vertical na direita (`.hud`): `hudFill.height = p*100%`, `hudPct = round(p*100)`, `hudStage` stepped (dado bruto → modelo → painel → decisão). É o "depth meter" do ABYSSAL adaptado.
- **Color-grade** (`.grade`): 3 gradientes stepped por faixa de `p` (navy → teal → lime), opacidade rampada. CSS com `transition: background .6s` suaviza a troca.
- **Grão de filme** (`.grain`): SVG `feTurbulence` fixo, `mix-blend-mode: overlay`, opacity ~.05.
- **Beats editoriais** (`.jbeat`): tipo gigante uppercase (Bricolage 800), crossfade por janelas `WIN`, `<br>` pra quebras. **Cuidado de calibragem:** o beat com sub+CTA precisa de headline menor + sub curto (senão estoura em viewport estreito), e um **scrim** no lado da copy (`journey__pin::before`, gradiente escuro) pra legibilidade sobre frames brilhantes. Testar em viewport estreito/retrato, não só 1440.

**Contraste texto-sobre-canvas é o furo nº1** do canvas-scrub: o frame final (dashboard aceso) lava o texto. Sempre por scrim no lado da copy.

## 1. Scrub do vídeo (o coração) — geração v1/v2 (`<video>`)

O vídeo é `<video>` fixo em tela cheia no fundo (`#bgv`), `muted playsinline preload="auto"` + `poster`. Um `ScrollTrigger` **pina** a primeira dobra (`.rhero__pin`) por `innerHeight * 5.4` (5,4 telas de rolagem). Durante esse pin, o progresso 0→1 vira `bgv.currentTime` via `seek(p)`:

```js
function seek(p) {
  if (!videoReady || !bgv.duration) return;
  const t = clamp(p, 0, 1) * (bgv.duration - 0.05);
  if (Math.abs(t - lastT) > 0.008) { try { bgv.currentTime = t; lastT = t; } catch (e) {} }
}
```

É isso que faz "cada scroll = 1 frame". O scrub é **decouplado** do scroll global (só roda no pin do hero). Depois do pin, o vídeo **congela no último frame** e as seções rolam por cima.

**Ajustar o pacing:** o `innerHeight * 5.4` no `setupRevealHero`. Cada `+1` ≈ 1 tela a mais pra completar o reveal. Mais lento = mais cinematográfico, mas enterra o CTA (o CTA fixo na nav compensa).

**Pré-requisito duro:** o vídeo tem que ser **all-keyframe** (ver `video-pipeline.md`). Senão o `currentTime` arbitrário trava.

## 2. Beats (texto que evolui)

Cada `.rh-beat` no HTML tem 2 `<span>`. O array `WIN` define as janelas de cada beat em fração do progresso do pin `[entra_ini, entra_fim, sai_ini, sai_fim]` (último beat sem saída):

```js
const WIN = [
  [0.03, 0.12, 0.19, 0.27],
  [0.28, 0.37, 0.45, 0.53],
  [0.54, 0.63, 0.69, 0.75],
  [0.76, 0.85, null, null],
];
const SUB = [0.87, 0.94];   // subheadline entra
const CTA = [0.91, 0.99];   // CTA entra
```

A função `seg(p, inA, inB, outA, outB)` faz a rampa (0→1, segura, 1→0). Cada beat faz cross-fade com blur+translateY por palavra. Sincronizar as janelas com os momentos do vídeo (fechado / abrindo / acendendo / cheio).

## 3. Stepper rotulado (`#rhSteps`)

4 labels no rodapé durante o pin ("dado bruto → modelo → painel → decisão"), o atual aceso em lima. Device de "profundidade" (inspirado no "AT 1,000 METERS" do ABYSSAL). No `render(p)`:

```js
const idx = p < 0.28 ? 0 : p < 0.53 ? 1 : p < 0.75 ? 2 : 3;
stepEls.forEach((s, i) => s.classList.toggle('on', i === idx));
```

Aparece/some junto com a barra de progresso (`chrome = seg(p,0.02,0.08) * (1 - seg(p,0.92,1))`).

## 4. bg-shade e ambient

- `.bg-shade` (fixo): escurece o asset congelado atrás do conteúdo. Cap **0.82 desktop / 0.95 mobile** (via `matchMedia` no `setupBgShade`). Ramp durante a aproximação da 2ª seção.
- `.ambient` (fixo, z-index 3): 3 glows blur à deriva (cor-tema + azul frio) pra profundidade tipo bokeh. Desligados sob reduced-motion.
- **Mobile:** o asset congelado atrás vira ruído. Seções pós-hero ganham `background:var(--bg)` sólido no `@media(max-width:900px)`. O "asset atrás do conteúdo" é luxo de desktop.

## 5. Statement (momento "produto flutuando")

Seção `.statement` entre cases e capacidades: asset num frame glass com tilt 3D + glow + chip, flutuando (keyframe `stmtfloat`), ao lado de uma frase-soco colossal. Palco escurecido por scrim radial (`.statement { background: radial-gradient(...) }`) pra o flutuante não competir com o asset congelado atrás. Lição do AURORA & NOIR (produto isolado + uma frase).

## 6. Acessibilidade (embutida)

- Lenis desligado sob `prefers-reduced-motion` (scroll nativo); `scrollToId()` faz fallback.
- `:focus-visible` global (anel lima).
- Vídeo decorativo com `aria-hidden` + `tabindex="-1"`.
- Token `--ink-2b` pra textos informativos (passa WCAG AA; `--ink-3` só decorativo).
- Um `<h1>` só (os outros beats são `div role="text"`).
- Todos os blocos animados têm branch `reduce` que mostra o estado final estático.

## 7. Outros comportamentos

- **Preloader:** revela no 1º frame (`loadeddata`), não espera o buffer inteiro. Fallback 2,5s.
- **Nav ativa:** IntersectionObserver marca `.active` no link da seção vigente.
- **Impact:** frase word-by-word pinada (`setupImpact`).
- **Form de contato:** submit demo (previne default, mostra confirmação). Pra produção, apontar pra endpoint real.
- **count-up** nas stats, **reveals** genéricos por IntersectionObserver.
