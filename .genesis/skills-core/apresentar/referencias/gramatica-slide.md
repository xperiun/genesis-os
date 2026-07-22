# Gramática de slide — regras universais de widescreen 16:9

Este arquivo define a **gramática de slide**: o conjunto de regras, tipos e padrões que valem pra **qualquer apresentação HTML widescreen**, independente do visual escolhido.

A **identidade visual** (paleta, tipografia, ornamentação, vibe) vem sempre de fora: do **seu** design system (extraído com `/extrair-design-system`) ou do sóbrio de reserva em [ds-sobrio.md](./ds-sobrio.md). Esta skill não tem visual próprio, de propósito.

Este documento responde "como um slide deve funcionar". O DS responde "qual a cara do slide".

---

## 🚨 FILOSOFIA EDITORIAL — LEIA ANTES DE CONSTRUIR QUALQUER SLIDE

Essas 5 regras são **independentes do DS visual** escolhido. Valem pra pitch minimalista corporate, pra deck neon maximalista, pra deck educacional limpo, qualquer um.

### As 5 regras invioláveis

#### 1. UM HERÓI POR SLIDE — hierarquia brutal

Cada slide tem **UM elemento hero** e tudo ao redor é **minúsculo** pra não competir.

- Big number / big statement: **`clamp(6rem, 16vw, 16rem)`** (96 a 256px)
- Texto de suporte abaixo: **`clamp(0.95rem, 1.6vw, 1.4rem)`** (15 a 22.4px)
- **Proporção ≥10:1** entre herói e apoio

> Se o texto de apoio estiver em `clamp(32px, 3vw, 56px)` ou similar, **tá errado**, é 2x maior do que deveria. O herói não vai dominar.

> Isso vale mesmo em DS sóbrio e corporativo. A escala dramática do herói é **o que diferencia slide de página web**. Numa página, `h1: 3rem` é dominante. Num slide widescreen, precisa de 10-16rem pro mesmo peso visual.

#### 2. RESPIRAÇÃO É DESIGN — espaço vazio é IDEAL

Metade do slide vazia é o **padrão correto** pros big numbers, não um problema a resolver. Slides respirando parecem editorial premium; slides cheios parecem dashboard projetado.

- Padding `.slide-content`: `clamp(2rem, 5vw, 5rem) clamp(2rem, 6vw, 6rem)` — generoso
- `max-width: min(800px, 85%)` em textos de apoio pra forçar fim de linha cedo
- Sem scroll interno em nenhum slide — se não couber, dividir em 2

#### 3. CARDS SÓBRIOS — sem backdrop-blur gratuito, sem glow pesado

- Border: `1px solid rgba(<accent>, 0.3)` — nunca 0.35 ou 0.4
- Background: `rgba(<accent>, 0.06)` — nunca mais opaco
- Box-shadow: `0 0 30px rgba(<accent>, 0.08)` — nunca mais forte
- **Um único ornamento sutil** por card (ex: `::before` com gradient horizontal no topo)
- **NUNCA** `backdrop-filter: blur()` em cards default (só em UI fixa como slide-counter)
- **NUNCA** border-top gradiente grosso inline (`height: 2px` + `linear-gradient(...)`)

> Adaptar as cores (`<accent>`) à paleta do DS escolhido, mas a **sobriedade é universal**. Cards de site são mais pesados porque a pessoa para e lê; cards de slide são ancoragem visual.

#### 4. UI FIXA MÍNIMA — slide-counter + nav-dots, nada mais

A UI fixa no viewport é **mínima e neutra**, identifica o documento sem competir com o conteúdo.

- **Slide counter `01 / 14`** no **canto superior direito** (pill pequeno, 11-14px font)
- **Nav dots verticais** no lado direito (8×8px, accent ativo com glow sutil)
- **Nada mais fixo no viewport** — sem brand-pill, sem logo permanente, sem watermark

O handle do apresentador aparece **apenas** na capa (slide 1) e no CTA final, não em todos os slides. Num pitch, **todo slide já é sobre a marca**, martelar logo no canto é redundância.

#### 5. Tipografia com função clara — sóbria de base, ornamental só em heróis

Todo DS terá uma fonte-base sóbria (Inter, Poppins, IBM Plex, Roboto) e geralmente uma fonte-ornamental (Playfair italic, Cormorant, uma serif editorial, ou um display type).

- **Base sóbria** — taglines, statements, descriptions, UI: é a fonte default (99% do texto)
- **Fonte ornamental** — EXCLUSIVA de heróis: big numbers, punchline curta de fechamento, título de capa dramático
- Se o DS tem **só uma fonte**: usar peso e tamanho pra fazer hierarquia, não família

> **NÃO** usar a fonte ornamental em taglines longas, descriptions, ou qualquer texto > 2 linhas. Serif italic longo em slide vira ilegível a 3m de distância.

### Red flag check antes de finalizar cada slide

- Big number tem só 2-3x o tamanho do texto de apoio → **texto tá grande demais**, reduzir
- Cards têm `backdrop-filter: blur()` sem razão, border glow visível, border-top gradient grosso → **reduzir tudo**
- Slide cheio até as bordas → **falta respiração**, cortar conteúdo
- Brand-pill/logo fixa no canto inferior → **remover**, deixar só slide-counter + nav-dots
- Tagline longa em serif italic ornamental → **trocar pra base sóbria**
- Overline com `font-size` > 16px → **reduzir pra 11-14px**

---

## 1. Tipos de slide (T1 a T11)

Repertório canônico. **Não são moldes fixos**, são a tipologia de layout. A composição de cada slide é livre dentro da gramática.

| Tipo | O que é | Herói |
|---|---|---|
| **T1 Capa** | Split 2 colunas (título/tagline à esquerda + stats à direita) OU centro dramático | Título da capa em fonte ornamental gigante |
| **T2 Seção divider** | Número grande + label + título curto | Número em fonte ornamental enorme |
| **T3 Big statement** | Uma frase dominando o slide | A frase em si (base sóbria, peso pesado) |
| **T4 Big number** | Número hero + contexto + statement + source | O big number |
| **T5 2 colunas** | Texto à esquerda + imagem/card/dado à direita | Depende — texto OU visual |
| **T6 Contraste** | 2 cards lado a lado com "vs" central | A comparação |
| **T7 Framework horizontal** | 3-4 cards em grid (letra/número + label + descrição) | O conjunto de cards |
| **T8 Lista / bullets** | Título + 4-6 items com border-left + numeração | Os items numerados |
| **T9 Quote** | Aspas grandes + citação italic + divider + atribuição | A citação |
| **T10 Image full-bleed** | Foto cobrindo o slide + overlay gradient + título sobre a foto | A foto |
| **T11 CTA final** | Statement + divider + handle + card com URL | O statement |

### Densidade máxima por tipo (inviolável)

**Cada slide cabe numa janela. Sem scroll interno. Nunca.**

| Tipo | Máximo de conteúdo |
|---|---|
| T1 Capa | 1 título + 1 tagline + 3 stats (se split) OU 1 subtítulo |
| T2 Seção | 1 número grande + 1 label + 1 título curto |
| T3 Big statement | 1 frase (máx 2 linhas) + opcional 1 punchline |
| T4 Big number | 1 número + 1 caption italic + 1 statement + 1 source |
| T5 2 colunas | 1 lado texto (overline + título + 1 parágrafo) + 1 lado visual |
| T6 Contraste | 2 cards (máx 3 linhas cada) + opcional 1 punchline |
| T7 Framework | 1 overline + 1 título + 3-4 cards (label + título + 1 frase) |
| T8 Lista | 1 overline + 1 título + 4-6 items (numeração + título + opcional 1 frase) |
| T9 Quote | 1 citação (máx 3 linhas) + 1 atribuição |
| T10 Image | 1 imagem + overlay opcional (1 overline + 1 título) |
| T11 CTA | 1 statement + 1 divider + 1 handle + 1 card (URL/handles) + opcional 1 punchline |

**Excedeu o limite? Dividir em 2 slides. Nunca espremer, nunca rolar.**

---

## 2. UI fixa (obrigatória em todo deck)

### 2.1 Slide counter (top-right)

Pill pequeno no canto superior direito, formato `01 / 14` com zero-padding. **Substitui a brand-pill**.

```css
.slide-counter {
  position: fixed;
  top: clamp(1rem, 2vw, 2rem);
  right: clamp(1rem, 2vw, 2rem);
  font-size: clamp(0.7rem, 1vw, 0.9rem);  /* 11-14px */
  font-weight: 600;
  color: var(--text-on-dark);
  background: rgba(<accent-primary>, 0.08);
  border: 1px solid rgba(<accent-primary>, 0.3);
  padding: 6px 14px;
  border-radius: 100px;
  z-index: 100;
  backdrop-filter: blur(8px);
  letter-spacing: 0.1em;
}
```

- Posição: **top-right** (nunca bottom)
- Font-size: 11-14px (microscópico)
- Formato: `01 / 14` com zero-padding (formato de relatório, não contador casual)
- Cor do accent: usar a cor primária do DS
- Em slides `.light`, trocar pra versão de contraste via `body.current-light` (controller JS já faz)

### 2.2 Nav dots (right vertical)

Pontos verticais à direita, um por slide. 8×8px. Ativo = accent primário do DS com glow + scale 1.3. Inativo = text-on-dark em opacidade 22%.

```html
<nav class="nav-dots" id="navDots" aria-label="Navegação"></nav>
```

O controller JS (ver [motor-html.md](./motor-html.md)) gera os dots automaticamente.

Em slides `.light`, trocar pra versão de contraste via `body.current-light`.
Escondidos em `max-width: 600px`.

### 2.3 Sem brand-pill fixa

**Não há `.brand-pill` fixa no viewport.** O handle do apresentador aparece apenas em 2 lugares:
- **Slide 1 (capa)** — na meta embaixo do título, em caps discreto
- **Slide final (CTA)** — dentro do card de fechamento

---

## 3. Ritmo dark/light

Deck editorial alterna tons pra criar **respiração visual** e **diferenciação tonal** entre seções.

**Regras universais:**
- ~**70% dark** / ~**30% light**
- **NUNCA** dois slides light consecutivos
- Usar light em **seções de transição** (T2), **quotes emocionais** (T9), ou **contrastes conceituais** (T6)
- Máximo 1 slide light a cada 3 dark

**Adaptação ao DS:**
- Se o DS é **dark-first**: a versão light é uma variação dele com `background` trocado pro tom cream/off-white e os accents recalibrados pra contraste adequado
- Se o DS é **light-first** ou **dual**: inverter a proporção (~70% light / 30% dark)
- **Accents que não funcionam em light**: qualquer cor com contraste < 3:1 sobre o fundo light. Testar e substituir (ex: um ciano puro sobre cream fica em ~1.1:1, invisível; a saída é a variante escura da mesma cor, não uma cor nova)

---

## 4. Ornamentação de fundo (bokeh, gradients, shapes)

Slides widescreen precisam de **alguma textura de fundo** pra não parecer chapado, mas a natureza da textura vem do DS.

### 4.1 Padrão com bokeh (DS neon/maximalista)

- **3 glows** em todo slide dark (normalmente: 1 primary + 1 secondary + 1 tertiary accent)
- **2 glows** em todo slide light (opacidade reduzida)
- Posição via inline style com `top/left/width/height` — variar a cada slide
- Alguns podem sangrar fora do canvas (`top:-10%`, `right:-15%`) pra dar continuidade

### 4.2 Padrão com beam lines ou gradient radial (DS corporate/sóbrio)

- **1 gradient radial** no background de cada slide (posição varia) — `radial-gradient(ellipse at X% Y%, bg-1 0%, bg-2 50%, bg-3 100%)`
- **Beam lines sutis** no hero slide apenas (linhas verticais com accent do DS)
- **Sem glows múltiplos** — se o DS é sóbrio, glow sobra

### 4.3 Padrão minimalista (DS flat)

- **Background flat** ou com textura quase imperceptível
- **Borders e dividers** como elementos de respiração em vez de glows
- **Accent pontual** em big numbers e CTA apenas

> A regra é: **o fundo nunca compete com o conteúdo**. Se o bokeh tá forte demais, reduzir opacidade. Se o gradient tá chamativo, suavizar. **Herói domina, fundo sussurra.**

---

## 5. Adaptação de um DS de página web pra slide

Design system quase sempre nasce pra **site**, não pra slide. O que o `/extrair-design-system` tira do seu site vem calibrado pra scroll. Precisa ser adaptado:

### 5.1 Extração de tokens do DS

Ao ler o `design-system.html` escolhido, extrair:
1. **Paleta** — cores primárias, secundárias, texto, background (em hex)
2. **Tipografia** — famílias, pesos disponíveis, hierarquia conceitual (qual é a base sóbria, qual é a ornamental)
3. **Gradients e ornamentação** — se existem (gradient text, glows, beam lines, bokeh, borders específicos)
4. **Componentes relevantes** — cards, botões, badges (padrão visual, border, bg, shadow)
5. **Vibe geral** — 1 frase descrevendo ("dark editorial com acentos ciano", "corporate sóbrio com teal glow", "enterprise minimalista purple")

### 5.2 Escala tipográfica — site → slide

Tamanho de site NÃO serve pra slide. **Sempre** recalibrar:

| Elemento | Site (self-paced) | Slide (projetado) |
|---|---|---|
| Hero title | 3-5rem (48-80px) | 6-16rem (96-256px) |
| Section title | 2-3rem (32-48px) | 2-4.5rem (32-72px) |
| Body/statement | 1rem (16px) | clamp(0.95rem, 1.6vw, 1.4rem) |
| Card title | 1.25rem (20px) | clamp(0.9rem, 1.3vw, 1.15rem) |
| Card desc | 0.95rem (15px) | clamp(0.75rem, 1.05vw, 0.95rem) |
| Overline/label | 0.75rem (12px) | clamp(0.7rem, 1vw, 0.9rem) |

**Sempre usar `clamp()`** em font-sizes de conteúdo, slides precisam escalar entre monitor 24" e projetor full HD sem quebrar.

### 5.3 Densidade de informação — site → slide

- Site: cada seção aguenta título + subtítulo + 3 parágrafos + 6 cards + CTA → **tudo cabe**
- Slide: aguenta 1 ideia hero + 1-2 elementos de apoio → **o resto vai pro próximo slide**

Pegou um hero de site com "4 bullets + botão + imagem + 3 stats"? Vira **3-4 slides** no deck.

### 5.4 Ornamentação — site → slide

- Site tem header, footer, navegação, coluna lateral: **nada disso vai pro slide**
- Site tem cards com padding generoso: **no slide, cards são mais sóbrios** (a decoração é o slide em si)
- Site tem animação sutil no scroll: **no slide, o reveal é mais dramático** (a pessoa navega slide a slide, não rola continuamente)

### 5.5 Token scale (padrão de referência pra qualquer DS)

Esses tokens são a escala **calibrada pra slide widescreen**. Troque cores e fontes pelo DS escolhido, mas **mantenha a escala** (ela já vem no `esqueleto.html`):

```css
:root {
  /* === HERÓIS === */
  --size-big-number:   clamp(6rem, 16vw, 16rem);   /* 96-256px */
  --size-brand:        clamp(4rem, 11vw, 11rem);   /* 64-176px — título capa */
  --size-brand-center: clamp(5rem, 13vw, 14rem);   /* 80-224px — centro dramático */

  /* === TÍTULOS DE SEÇÃO === */
  --size-section-title:    clamp(2rem, 4.5vw, 4.5rem); /* 32-72px */
  --size-section-title-lg: clamp(2rem, 5vw, 5rem);     /* 32-80px */

  /* === TAGLINE / SUBTÍTULO === */
  --size-tagline: clamp(1rem, 1.6vw, 1.4rem); /* 16-22.4px */

  /* === STATS secundários === */
  --size-stat: clamp(3rem, 6vw, 5.5rem); /* 48-88px */

  /* === TEXTOS DE APOIO === */
  --size-statement: clamp(0.95rem, 1.6vw, 1.4rem); /* 15-22.4px */
  --size-caption:   clamp(1rem, 1.8vw, 1.6rem);    /* 16-25.6px */

  /* === CARDS === */
  --size-card-num:   clamp(2rem, 4.5vw, 4rem);       /* 32-64px */
  --size-card-title: clamp(0.9rem, 1.3vw, 1.15rem);  /* 14.4-18.4px */
  --size-card-desc:  clamp(0.75rem, 1.05vw, 0.95rem); /* 12-15.2px */

  /* === UI MINI === */
  --size-overline: clamp(0.7rem, 1vw, 0.9rem);    /* 11-14.4px */
  --size-small:    clamp(0.65rem, 0.9vw, 0.85rem); /* 10.4-13.6px */

  /* === PUNCHLINE (fonte ornamental, só em fechamentos) === */
  --size-punch: clamp(1rem, 2vw, 1.6rem); /* 16-25.6px */
}
```

---

## 6. Widescreen-specific (regras críticas)

- **Sem scroll interno** em nenhum slide — se não couber, dividir em 2
- **Respiração sobra espaço > comprime conteúdo** — aplicar densidade máxima da §1
- **Padding `.slide-content`**: `clamp(2rem, 5vw, 5rem) clamp(2rem, 6vw, 6rem)` — generoso
- **Imagens com `max-height: 70vh`** — deixar respiro pro texto
- **`clamp()` em TODAS as font-sizes** de conteúdo — px fixo só em UI pequena (counter, bokeh positioning)
- **1 slide = 1 viewport** — `width: 100vw; height: 100vh` (com `height: 100dvh` pra mobile)
- **scroll-snap-type: y mandatory** no HTML

---

## 7. Checklist final

### Filosofia editorial (os 5 invioláveis)
- [ ] **UM herói por slide** — big number ≥10x o texto de apoio
- [ ] **Respiração** — metade do slide vazia em slides de big number é OK
- [ ] **Cards sóbrios** — sem `backdrop-filter`, border 0.3, background 0.06
- [ ] **UI fixa mínima** — só slide-counter top-right + nav-dots, nada de brand-pill
- [ ] **Fonte base sóbria** — ornamental SÓ em heróis e punchline curta de fechamento

### DS aplicado corretamente
- [ ] Tokens de cor do DS escolhido aplicados via CSS variables (`--accent-primary`, `--accent-secondary`, `--text`, `--bg-*`)
- [ ] Fontes do DS carregadas via `<link>` no `<head>`
- [ ] Tipografia escalada com `clamp()` conforme escala da §5.5 (não copiar o px do site)
- [ ] Ornamentação de fundo (bokeh, gradient, beam lines) adaptada à vibe do DS
- [ ] Vibe do DS preservada — slide parece "versão slide" do DS, não "DS neutro qualquer"

### Ritmo dark/light
- [ ] ~70% dark / ~30% light (ou invertido se DS é light-first)
- [ ] NUNCA dois slides light consecutivos
- [ ] Em slides light: accents com contraste < 3:1 sobre fundo claro NÃO aparecem (testar)
- [ ] Slide-counter e nav-dots trocam de cor quando slide atual é `.light`

### Funcional
- [ ] Arrow keys, Space, PageDown navegam
- [ ] Scroll snap funciona
- [ ] Touch/swipe funciona em tablet
- [ ] Nav dots clicáveis
- [ ] Slide counter `01 / NN` atualiza conforme scroll
- [ ] Reveal animations disparam ao entrar no viewport (IntersectionObserver)

### PT-BR
- [ ] Todo texto com acentos corretos (não, você, é, métricas, análise, padrão, decisão, liderança, país)
- [ ] `<title>` do HTML com acentos
- [ ] Hashtags inclusive (`#liderança`)

### Narrativa
- [ ] Arco completo (hook → contexto → conflito → virada → resolução → CTA)
- [ ] Big moment identificável (1-2 slides que carregam o peso)
- [ ] CTA ancora o que o deck construiu (não é um CTA genérico)

### Números
- [ ] Todo número que virou herói de slide tem origem que você sabe enunciar
- [ ] Número que veio de planilha passou pela `/analisar` antes de virar big number
- [ ] Número sem conferência possível está rotulado como estimativa no próprio slide

---

## 8. Referências internas

- **Arquitetura HTML + controller JS + animações** → [motor-html.md](./motor-html.md)
- **DS sóbrio de reserva (tokens prontos)** → [ds-sobrio.md](./ds-sobrio.md)
- **Esqueleto HTML base (DS-agnostic, com placeholders)** → [`../templates/esqueleto.html`](../templates/esqueleto.html)
- **O seu DS** → o que o `/extrair-design-system` gerou a partir do seu site ou material
