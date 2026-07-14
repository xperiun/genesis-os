# Auditoria + verification loop

Como levar o site de "bom" a "200%". Foi o processo que levou a implementação de referência de ~7.5 pra ~9.

## Verification loop (INVIOLÁVEL antes de declarar pronto)

Texto sem render mente. CSS quebra em viewport diferente. Rodar:

```bash
node scripts/shoot.cjs   # gera .scratch/shots/ desktop 1440x900 + mobile 390x844, N pontos de scroll
```

O `shoot.cjs` tira screenshots em vários pontos de scroll (topo → beats do reveal → cada seção). Loop:
1. Escreve/edita.
2. Roda `shoot.cjs`.
3. Read dos PNGs (Read aceita imagem).
4. Critica contra este checklist.
5. Corrige os 3-5 piores.
6. Repete. Máx 3 iterações. Passou de 3 e ainda tem issue = falha estrutural, reportar.

## Auditoria de 4 lentes em paralelo (pra elevar a 200%)

Disparar 4 agents via Agent tool em paralelo (`subagent_type: general-purpose`), cada um lendo os screenshots + código, devolvendo achados priorizados (P0/P1/P2) com fix concreto. As lentes:

1. **UI / visual** — hierarquia, tipografia, cor, espaçamento, consistência de DS, contraste WCAG, craft de motion.
2. **UX / interação** — fluxo, o pacing do reveal, wayfinding, mobile, acessibilidade (foco de teclado, reduced-motion), transições.
3. **Copy** — headline/beats, copy de seção, CTA, tom, caça a vícios de IA, acentuação PT-BR. (Colar `contexto/posicionamento.md §8.3`.)
4. **Layout / CRO / performance** — breakpoints, overflow, largura de linha, CTA, atrito até o contato, peso do vídeo/LCP, fontes, SEO/meta.

Depois sintetizar (consenso + severidade), aplicar a leva segura, re-verificar.

## Checklist consolidado (os furos que aparecem sempre)

### P0 (graves)
- **[Mobile] Asset fixo vaza atrás do conteúdo** — o vídeo `fixed` aparece atrás de stats/impact/contato e destrói a legibilidade. FIX: seções pós-hero com `background:var(--bg)` sólido no `@media(max-width:900px)` + shade cap 0.95 no mobile. **É o furo nº1, sempre.**
- **[Desktop] Contraste de texto sobre o asset aceso** — parágrafos sobre o asset congelado brilhante caem abaixo de 4.5:1. FIX: shade mais forte (0.82) + scrim radial nas seções com texto corrido.
- **[Perf] Vídeo pesado com `preload="auto"`** — trava o LCP. FIX: re-encode leve (~2-4MB), preloader revela no 1º frame (`loadeddata`), fallback curto.
- **[A11y] Token de texto informativo falhando WCAG** — `--ink-3` (#5E655E) sobre near-black dá ~3:1. FIX: token `--ink-2b` (~#8A9288, 4.5:1) pros labels; `--ink-3` só decorativo.
- **[SEO] Sem meta description / OG** — link compartilhado sai sem preview. FIX: `<meta description>` + `og:*` + `twitter:card`.

### P1/P2 (polish)
- Um `<h1>` só (beats extras viram `div role="text"`); seções com `<h2>` semântico.
- `:focus-visible` global; Lenis desligado sob reduced-motion; `aria-hidden` no vídeo decorativo.
- Título de seção saindo de baixo da nav → `scroll-margin-top`.
- Thumbnails/imagens que brigam com a paleta → dessaturar em repouso, cor plena no hover.
- Nav com estado de seção ativa (wayfinding).
- Barra de progresso + stepper durante o pin longo (resolve "por que não rola?").
- Eyebrow/labels órfãos no mobile; `100vh`→`100svh`/`100dvh` nos pins.
- Botões empilhados no mobile; sparklines/gráficos contidos.
- CSS morto removido.
- Copy: frase-soco por seção, zero vício de IA (travessão em prosa, ponto do meio, tríades, "não é X é Y" repetido), acentuação PT-BR completa.

## Regra de decisão

O único lever que exige rebuild de asset (não de código) é **trocar o vídeo** (ex: câmera fixa → em movimento). Tudo mais é iteração no lugar. **Nunca clonar pra refazer** um site que já passou pela auditoria, é jogar fora trabalho resolvido.
