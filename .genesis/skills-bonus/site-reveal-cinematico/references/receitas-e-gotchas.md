# Receitas de craft + gotchas

Padrões de CSS/JS reutilizáveis e armadilhas conhecidas. Complementa o `motor.md` (que cobre scrub, beats, stepper, statement). Aqui ficam as receitas de acabamento e os perrengues.

> Nota histórica: a versão original deste motor usava **scrub global** (o vídeo scrubava com o scroll do documento inteiro) + uma seção "laptop" que abria a tampa via CSS + um `hero__viz` (dashboard flutuante no hero). Tudo isso foi **substituído**: hoje o scrub é **decouplado** (só no pin do hero, ver `motor.md`) e a "abertura" é o próprio vídeo. Se encontrar referência a `setupLaptop`, `laptop.css`, `hero__viz` ou `scrubVideo` global em algum código antigo, é a arquitetura velha, não replicar.

## Camadas (z-index) — manter a pilha intacta

O fundo é fixo, o conteúdo rola por cima:

| elemento | z | papel |
|---|---|---|
| `.bg-video` (`#bgv`) | 0 | vídeo fixo full-screen, `object-fit:cover`, scrubbed no pin do hero |
| `.bg-tint` | 1 | escurecimento radial/linear pra legibilidade |
| `.bg-shade` | 2 | escurece o asset congelado atrás do conteúdo (cap 0.82 desktop / 0.95 mobile) |
| `.ambient` | 3 | glows blur à deriva (profundidade) |
| `#page` (seções) | 10 | todo o conteúdo |
| `.rhero-progress` / `.rh-steps` | 70/71 | barra + stepper do reveal |
| `#cursor` | 100 | cursor custom |

O **footer** é irmão das seções (faixa preta full-bleed); o vídeo dissolve pra preto acima dele via gradiente CSS.

## Hooks de dev (rodar no console antes de assumir bug)

Expostos em `window`: `__lenis` (Lenis, ou null sob reduced-motion), `__ST` (ScrollTrigger), `__bgv` (o vídeo). Pra inspecionar um estado pinado, force o `render(progress)` da seção e tire screenshot.

## Receitas de CSS-craft

### Tipografia colossal com wipe-in
`.showcase__line` em `clamp(3rem,10vw,8.5rem)` com `clip-path:inset(0 100% 0 0)` que abre pra `inset(0 0 0 0)` quando `.section-head.in`. Type gigante kinético é o que faz parecer das referências.

### Stats como mini-dashboards
Cada `.stat` ganha um sparkline SVG (`polyline pathLength="1"` com `stroke-dashoffset` que se desenha via `.stat.in`) + baseline que cresce (`scaleX`). Número com `white-space:nowrap` pra não quebrar "R$ X,XM"; unidade menor (`.num .u{font-size:.56em;vertical-align:.04em}`). No mobile, conter a sparkline (`max-width:190px`).

### Glass panels / cards
Adicionar `glass` (superfície fosca, `glass.css`) + classe de layout. `glass.css` já resolve z-index dos filhos com `.glass>*{position:relative;z-index:2}` (acima do sheen do `::before`). Botões: `glass-btn glass-btn--primary|--ghost`. Card sobre asset brilhante usa bg semi-opaco pra copy continuar legível.

### Footer dissolve-to-black
Footer fora das seções (full-bleed), bg preto sólido + gradiente acima faz o dissolve, sem ScrollTrigger:
```css
.footer { position: relative; margin-top: 24vh; padding: 14vh ... 7vh; background: var(--bg); }
.footer::before { content:""; position:absolute; left:0; right:0; bottom:100%; height:42vh;
  background: linear-gradient(to bottom, transparent, var(--bg)); pointer-events:none; }
```

### Reveals genéricos (IntersectionObserver)
`main.js` adiciona `.reveal` a `.stat`, `.cap`, `.section-head`, `.case-card`, `.stmt__line` etc., e um IntersectionObserver adiciona `.in` quando entram na tela. Dispara sparklines, acentos de card, wipe-in do type, tudo declarativo no CSS. Count-up dos números é observer separado (`.cv`).

### Congelar/desacelerar o vídeo durante um pin (opcional)
Se uma cena precisar respirar, mapear um "scroll efetivo" que exclui parte do comprimento do pin. `k=1` scrub normal, `k=0` congela, `k≈0.12` ~8× mais lento. A continuidade fecha no fim do pin pra qualquer `k`. Não está ativo no template, mas o padrão vale.

## Gotchas

1. **Ordem de carga do CSS importa.** `glass.css` e `enhance.css` carregam depois de `style.css`. Specificidade igual → o último vence. Se um `.glass` sobrescrever `position` de um card absoluto, out-specify.
2. **Pin novo desloca os pins seguintes.** Qualquer coisa que lê `ScrollTrigger.start/end` usa valores vivos. Preferir `() => '+=' + ...` no `end` e recomputar no refresh.
3. **Write tool falha calado >~70KB.** O `index.html` é grande; editar com Edit incremental, nunca Write inteiro.
4. **Live Server / `file://` no `index.html` da fonte NÃO funciona (site fica sem estilo, "preto e branco").** É um app **Vite**: o CSS é importado via JS (`import './style.css'` no `main.js`), e o browser não entende importar CSS como módulo sem o bundler. Live Server só serve os arquivos crus, sem o transform do Vite → os imports falham → zero estilo. Dois jeitos certos: (a) `npm run dev` (Vite serve tudo transformado, http://localhost:5173); (b) `npm run build` → gera `dist/` com o CSS já embutido como estático → aí sim dá pra abrir o `dist/` com Live Server ou `npx serve dist`. O que não dá é Live Server no `index.html` da pasta-fonte.
5. **`prefers-reduced-motion`.** `enhance.css` e os `setup*()` checam `reduce` e desligam ambient, float, ticker, clip-path, sparkline, e o próprio Lenis. Manter ao adicionar motion novo.
6. **Vídeo que treme no scrub = não é all-keyframe.** Re-encodar (ver `video-pipeline.md`).
