---
name: extrair-design-system
description: "Extrai o design system de um HTML/URL/print e gera um design-system.html canônico (11 seções, anatomia replicável, regras do/dont, tokens CSS, classes .ds-*, WCAG AA, voz, versionamento) preservando 100% das classes/animações originais. Salva o DS mestre do seu OS em contexto/design-system.html e a referência extraída em contexto/design/refs/{slug}/ (com index.html + assets baixados, roda offline). Tema dark/light detectado automaticamente e confirmado. Use quando pedirem 'extrai o design system desse HTML', 'gera um style guide do site', 'cria pattern library a partir desse HTML', ou passarem URL/arquivo HTML/print pedindo documentação visual."
---

# Extract HTML Design System

Você é um **Design System Architect**.

Recebe um arquivo HTML de referência (caminho absoluto ou URL) via `$ARGUMENTS` e produz o **DS mestre do seu OS** em `contexto/design-system.html`, mais uma **pasta de referência completa** da fonte extraída em `contexto/design/refs/{slug-do-host}/`. A pasta de referência contém:

- `index.html` — clone do HTML original (baixado pra biblioteca, pra referência viva)
- `assets/` — todos os CSS/JS/imagens externas que o original carrega (baixados pra rodar offline)
- `design-system.html` — **o entregável da skill** (referencia `assets/` via path relativo, fica standalone)
- `_preview.png` — screenshot de validação do DS gerado

A skill **gera** o `design-system.html`. Os outros arquivos são o **substrato** que faz o DS rodar isolado, sem depender da rede ou do site original.

Esse arquivo funciona como um **template canônico de design system** — preservando look & behavior exato do original (classes, animações, keyframes) e adicionando uma camada de documentação estrutural madura: anatomia replicável, regras do/dont, tokens formais, acessibilidade, voz e versionamento.

Não é uma aproximação. Não é um moodboard. É o contrato entre design e implementação.

---

## Quando usar

- "Extrai o design system desse HTML"
- "Gera um style guide do site X"
- "Cria um pattern library a partir desse HTML"
- "Documenta visualmente o design desse arquivo"
- Usuário cola um caminho/URL de HTML pedindo documentação visual

## Quando NÃO usar

- Quando o usuário quer **criar** um design novo do zero (outra skill cuida disso — essa preserva o existente)
- Quando o usuário quer apenas listar tokens em texto/markdown (não HTML)
- Quando o HTML alvo não existe ou não está acessível

---

## Estrutura canônica (o alvo)

O `design-system.html` que você gera segue sempre a mesma arquitetura (esqueleto replicável,
detalhado seção a seção abaixo). Emula a ESTRUTURA, nunca o estilo visual — cada HTML alvo
tem sua própria identidade; o esqueleto é que se repete. O output tem:

- Os **6 slots da anatomia** por seção (eyebrow, título, descrição, conteúdo, regras, tokens)
- As **11 seções canônicas** (anatomia, tipografia, cores, componentes, layout, motion, ícones, composições, a11y, voz, versionamento)
- Um **bloco de regras do/dont** por seção
- **40+ tokens CSS** declarados em `:root` (extraídos do original)
- As **classes `.ds-*`** canônicas de meta-documentação
- Acessibilidade **WCAG AA**, voz editorial, e component status + changelog

---

## Hard Rules (INVIOLÁVEIS)

### Preservação do design original
1. **Não redesenhe nada.** Nenhum estilo novo, nenhuma "melhoria" visual do design original.
2. **Reuse os nomes de classe exatos**, animações, timing, easing, hover/focus do HTML fonte.
3. **Referencie os mesmos assets CSS/JS** que o original usa.
4. **Se um estilo/componente não existe no original, NÃO inclua** como exemplo.

### Camada de documentação (meta)
5. **Adicione sempre** as classes `.ds-*` de sistema (section-eyebrow, section-title, section-desc, subsection-title, rules-block, rules-box, meta-template). Elas são META-documentação — não alteram o design original, são do doc.
6. **Declare `:root` tokens** extraídos do CSS original. Tokens não são "novos" — são o CSS existente exposto como API.
7. **Bloco de regras `do/dont`** é obrigatório em toda seção (exceto hero). Sem regras = brochura, não DS.
8. **`:focus-visible`** obrigatório em todo CTA/link — a11y não é opcional.
9. **Português brasileiro com TODOS os acentos** em qualquer texto explicativo. Sem exceção.

---

## Inputs

- `$ARGUMENTS` = caminho absoluto pro HTML de referência (ex: `C:\projeto\landing.html`) ou URL pública.

Se o argumento for vazio, perguntar ao usuário qual HTML usar.

---

## Pasta de saída — INVIOLÁVEL

O **DS mestre do seu OS** vai pra `contexto/design-system.html`. A **referência extraída** da
fonte (o site original + o DS dela) vai pra uma pasta em `contexto/design/refs/`:

```
contexto/
├── design-system.html              ← DS MESTRE do OS (fonte de verdade de todo entregável)
└── design/refs/{slug-do-host}/
    ├── index.html                  ← HTML original baixado (curl da URL ou cópia do local)
    ├── assets/                     ← CSS/JS + imagens externas que o original carrega
    │   ├── index.css               (ou nome original)
    │   └── ...
    ├── design-system.html          ← o DS extraído DESSA fonte (referencia assets/ relativo)
    └── _preview.png                ← screenshot de validação
```

O `contexto/design-system.html` (mestre) é onde TODO entregável do OS ancora. A pasta em
`design/refs/` guarda a extração bruta de cada fonte, pra rastreabilidade.

**Como baixar os assets:**
1. Após `curl` do `index.html`, parsear `<link rel="stylesheet" href="...">` e `<script src="...">` que apontem pra mesmo host (não CDN público — esses ficam absolutos).
2. Pra cada um, `curl` pra `assets/{basename}` e reescrever o href/src no `index.html` baixado pra apontar pra `assets/...` relativo.
3. Imagens críticas (logo, hero img) também vão pra `assets/`. CDNs públicos (fonts.googleapis, jsdelivr, unpkg) ficam absolutos — não baixar.
4. Se o site for SPA com iframe (caso `aura.build`), baixar também o iframe HTML e seus assets.

**No `design-system.html` gerado:** referenciar os mesmos CSS/JS via path relativo (`<link href="assets/index.css">`). Assim o DS roda offline e fica decoupled da URL original.

**Onde:**
- `{slug-do-host}` = host da URL (ex: `nexastream.exemplo.com`) ou slug do nome do arquivo se input local
- O **tema** (dark/light) é detectado e confirmado, e fica refletido nos tokens do DS (não vira pasta separada)

**Antes de criar a pasta:**

1. **Detectar tema automaticamente** via Playwright (rodar antes de qualquer geração):
   - Renderizar a URL/arquivo, ler `getComputedStyle(document.body).backgroundColor`
   - Se luminância < 0.3 → sugerir `dark`. Se ≥ 0.5 → sugerir `light`. Caso entre 0.3–0.5 → perguntar sem default.
2. **Confirmar com o usuário** apresentando a sugestão:

   ```
   Detectei tema escuro (bg #020408). O DS vai refletir esse tema. Confirma? (dark / light)
   ```

   Esperar resposta antes de criar a pasta. Se o usuário responder com 1/2 ou "dark"/"light", seguir.
3. **Se a pasta já existir** (re-extração), perguntar se sobrescreve `design-system.html` ou aborta. Não tocar em `index.html`/`assets/` que o usuário possa ter editado sem aprovar.

Os caminhos são sempre relativos à raiz do seu OS (o repo onde o Claude Code está rodando).

---

## Pipeline de execução

### Passo 1 — Ler e auditar o HTML original

1. Ler o arquivo HTML completo
2. Identificar e listar:
   - Folhas de estilo externas (`<link rel="stylesheet">`)
   - Scripts externos (`<script src=...>`)
   - CSS inline em `<style>` blocks
   - Fontes do Google Fonts ou outras
   - Sistemas de ícones (lucide, heroicons, feather, font-awesome, SVGs inline)
3. **Mapear todos os tokens visuais** usados — e preparar pra declarar em `:root`:
   - Cores (hex, rgb, hsl, var(--...)) + suas variantes com alpha
   - Gradientes nomeados (hero, button, card)
   - Tipografia (font-family, font-size, line-height, font-weight)
   - Espaçamentos recorrentes
   - Border-radius, shadows, blurs
   - Animations e keyframes (`@keyframes`)
   - Transitions, easings, durações
   - Focus ring (se já existir — se não, derive dos acentos)
4. **Mapear componentes** presentes:
   - Hero, botões (+ estados), inputs, cards, navs, grids, ícones
5. **Extrair vocabulário editorial** do copy existente:
   - Traços usados (—, -, ·), aspas (curvas/retas), números (formatação de moeda, %)
   - Casing de headings (sentence/title), de eyebrows (uppercase)
   - Princípios implícitos (frases curtas? contraste binário?)

**Não inventar nada que não esteja no HTML original.** O output documenta o que já existe — incluindo os tokens e vocabulário.

### Passo 2 — Construir o `design-system.html`

Estrutura **obrigatória** (11 seções + hero):

#### Hero (clone exato, texto adaptado)
- **Clone direto** do Hero original — mesma estrutura HTML, classes, layout, imagens, animações, botões, background.
- **Única mudança permitida:** substituir o texto do hero para apresentar o Design System (manter tamanho/hierarquia).
- Adicionar stats badges ao final do hero — ex: `"11 seções · 11 blocos de regras · 40+ tokens · WCAG AA"`.
- Adicionar nota clarificando: demos renderizadas vêm do original (copy real), tokens/patterns são canônicos.

#### Seção 00 — Anatomia de seção (meta-template)

Documenta o padrão replicável ANTES de aplicá-lo.

**Estrutura:**
- 6 slots explicados em `ds-meta-slot` cards:
  1. **Eyebrow** — `<div class="ds-section-eyebrow">/ NN · NOME</div>`
  2. **Título canônico** — `<h2 class="ds-section-title">Afirmação <span class="accent">com acento.</span></h2>`
  3. **Descrição** — `<p class="ds-section-desc">1 parágrafo, max 2 linhas</p>`
  4. **Conteúdo** — sub-seções `<h3 class="ds-subsection-title">` + cards/tabelas/previews
  5. **Regras (obrigatório)** — `<div class="ds-rules-block">` com do + dont em par
  6. **Tokens & snippet (opcional)** — `<div class="ds-code">` com export
- Bloco de regras do/dont pra própria anatomia.
- **Snippet HTML esqueleto** em `ds-code` — pronto pra copiar e colar em seções novas.

#### Seção 01 — Tipografia

Renderizar como **tabela de spec / lista vertical**.

Cada linha:
- Nome do estilo (ex: "Heading 1", "Bold M", "Big Stat")
- Preview ao vivo usando o **elemento HTML e classes CSS exatos** do original
- Label de tamanho/line-height à direita (formato: `40px / 48px`)

Incluir APENAS estilos que existem no original, nesta ordem:
- Heading 1, 2, 3, 4
- Bold L / Bold M / Bold S
- Paragraph (body)
- Regular L / Regular M / Regular S
- Eyebrow / Overline
- Big Stat (se existir)

**Fim da seção:** bloco de regras (`✓ Invioláveis` + `✕ Vetado`) — mínimo 5 regras em cada.

#### Seção 02 — Cores & Superfícies

Sub-seções `ds-subsection-title`:
- **Backgrounds** — swatches com hex, nome, uso
- **Bordas & divisores** — variantes de alpha
- **Overlays radiais** (se existirem no original) — com posição e cor
- **Gradientes** — swatches em blocos
- **Cores de texto** — tabela com cada alpha/cor documentada

**Regras obrigatórias — incluir "cores vetadas explícitas"** (o que NUNCA usar fora da paleta): roxo/amarelo/etc. Deriva do original — se só usa teal, as vetadas são todas as outras.

#### Seção 03 — Componentes UI

Apenas os que existem no HTML:
- Botões, inputs, cards, badges, pills, etc.
- Mostrar **estados lado a lado**: default / hover / active / focus / disabled
- Inputs apenas se presentes (default / focus / error se aplicável)
- Cada componente com seu próprio sub-header + descrição de uso + snippet de classes

**Bloco de regras** ao final — específico pros componentes do original.

#### Seção 04 — Layout & Spacing

- Container patterns (max-widths documentados)
- Grids (2 col, 3 col, splits)
- Section padding/spacing tokens
- Hero layout anatomy
- Breakpoints responsivos (derivar do Tailwind/CSS custom)

**Regras obrigatórias** — `max-width` fixo? `py-X` padrão?

#### Seção 05 — Motion & Interação

Mostrar todos os comportamentos de motion presentes:
- Animações de entrada (se houver) — `fadeSlideIn`, `slideUp`, etc.
- Hover lifts/glows
- Transições de botão
- Scroll/reveal behavior (apenas se presente)
- Keyframes inline
- Easing functions usadas

**Motion Gallery** — cada animação demonstrada com hover trigger ou loop visível.

**Regras** — easing padrão, duração, reduced-motion obrigatório.

#### Seção 06 — Ícones

Se o reference usa ícones:
- Mostrar o **mesmo sistema/estilo de ícones**
- Variantes de tamanho e color inheritance
- Usar o **mesmo markup e classes**
- Tamanhos canônicos (w-3.5, w-4, w-5, w-6, etc.)

Se não há ícones, **omitir a seção inteira** — mas documentar no changelog: "sem ícones no original".

**Regras** — Feather vs heroicons? stroke-width? currentColor?

#### Seção 07 — Composições / Slide Types (se aplicável)

Apenas se o original tiver padrões de composição repetidos (ex: apresentação com N tipos de slide, landing com M blocos de seção):
- Grid de previews
- Cada um com label + descrição do trabalho narrativo que resolve

Se o original é uma LP única sem padrões replicáveis, **omitir** e ajustar numeração das seções seguintes (08→07, 09→08, 10→09).

#### Seção 08 — Acessibilidade

**Obrigatória em todo output.**

Sub-blocos:
- **Tabela de contraste** — cada par cor/background do original medido (AA/AAA), inclusive texto com alpha sobre page base
- **Foco visível** — demo de CTAs com `:focus-visible` ring canônico (var(--focus-ring))
- **Regras invioláveis + vetadas** — semantic HTML, aria-hidden em decorativos, prefers-reduced-motion, etc.

Se o original **não tem** focus ring visível, derive um do acento primário e documente como "adicionado pela camada DS — o CSS original não o previa".

#### Seção 09 — Voz & Conteúdo

**Obrigatória.**

Sub-blocos:
- **Traços & pontuação** — em dash (—), bullet médio (·), aspas curvas, hífen
- **Números & casing** — formato de moeda, %, sentence case vs title case
- **Princípios editoriais** — extrair do copy do original: frases curtas? contraste binário? verbo forte?

**Regras invioláveis + vetadas** — listar do/dont específicos (ex: "aspas curvas em depoimentos" ✓, "Title Case em headings" ✕).

#### Seção 10 — Versionamento & Status

**Obrigatória.**

Sub-blocos:
- **Status dos componentes** — tabela com cada componente do DS + status (stable/beta/deprecated) + desde (versão) + nota
- **Changelog** — mínimo v1.0 (lançamento = extração) com data absoluta (YYYY-MM)
- **Como contribuir** — 5 passos: ler anatomia → duplicar snippet → preencher slots → validar regras → bump versão

**Regras invioláveis + vetadas** — SemVer, deprecation obrigatória, tokens como API.

---

### Tokens CSS canônicos — declaração obrigatória em `:root`

Estrutura formal dentro do `<style>`, extraída do CSS original:

```css
:root{
  /* Cores — paleta (global) */
  --color-bg:              /* extrair */;
  --color-bg-glass:        /* extrair */;
  --color-border-1:        /* extrair */;
  --color-border-2:        /* extrair */;
  --color-primary:         /* acento principal */;
  --color-primary-bright:  /* acento claro */;
  --color-success:         /* se existir */;
  --color-danger:          /* se existir */;
  --color-text-1:          /* mais forte */;
  --color-text-2:          /* body */;
  --color-text-3:          /* card body */;
  --color-text-4:          /* secondary */;
  --color-text-meta:       /* meta/disclaimer */;
  --color-white:           #FFFFFF;

  /* Alpha variants do acento primário — pra glows, borders, gradients */
  --color-primary-05:      /* rgba(R,G,B,.05) */;
  --color-primary-10:      /* ... */;
  --color-primary-20:      /* ... */;
  --color-primary-30:      /* ... */;
  --color-primary-45:      /* ... */;
  --color-primary-60:      /* ... */;
  --color-primary-80:      /* ... */;

  /* Tipografia */
  --font-sans:             /* extrair */;
  --font-serif:            /* se existir */;
  --text-eyebrow:          .75rem;
  --text-section-title:    clamp(1.5rem, 3vw, 2.25rem);
  --text-subsection-title: clamp(1.5rem, 2.5vw, 1.875rem);
  --text-section-desc:     1.125rem;
  --tracking-widest:       .22em;
  --tracking-tight:        -.02em;

  /* Layout */
  --container-max:         /* extrair do max-w-* */;
  --container-inner:       /* ... */;
  --gutter-mobile:         /* ... */;
  --gutter-desktop:        /* ... */;
  --section-gap:           /* ... */;

  /* Motion */
  --ease-standard:         /* extrair — cubic-bezier principal */;
  --ease-entrance:         /* ... */;
  --dur-fast:              .15s;
  --dur-base:              .25s;
  --dur-slow:              .6s;
  --dur-fade-in:           1s;

  /* Acessibilidade — focus ring canônico */
  --focus-ring:            0 0 0 3px rgba(<primary-rgb>,.35), 0 0 0 5px var(--color-bg);
  --focus-ring-offset:     2px;
}
```

**Regra:** se o valor não existe no original, derive do que mais se aproxima + documente no changelog como "adicionado pela camada DS".

### Meta-documentation CSS — classes `.ds-*` obrigatórias

Incluir no `<style>` (adicional ao CSS original, não substitui):

```css
/* Section header pattern */
.ds-section-eyebrow{...}
.ds-section-title{...} .ds-section-title .accent{...}
.ds-section-desc{...}
.ds-subsection-title{...}

/* Rules box (do/dont) */
.ds-rules-block{display:grid;grid-template-columns:1fr;gap:1rem;}
@media(min-width:768px){.ds-rules-block{grid-template-columns:1fr 1fr;}}
.ds-rules-box{...}
.ds-rules-box--do{/* verde sucesso */}
.ds-rules-box--dont{/* vermelho veto */}
.ds-rules-label{...}
.ds-rules-list{...}

/* Meta-template (seção 00) */
.ds-meta-template{...}
.ds-meta-slot{...}

/* Utility helpers */
.ds-swatch, .ds-row, .ds-tag, .ds-grid-diagram, .ds-code, .ds-anchor-nav

/* Focus canônico */
a:focus-visible{outline:none;box-shadow:var(--focus-ring);}
[CTA-classes]:focus-visible{outline:none;box-shadow:var(--focus-ring);}
```

Gere esses blocos `.ds-*` a partir das descrições acima, adaptando as cores/tokens pro original alvo.

### Nav horizontal sticky

Logo após o hero, incluir navegação com âncoras pra **todas** as seções presentes:

```
[Visão] [Anatomia] [Tipografia] [Cores] [Componentes] [Layout] [Motion] [Ícones] [Slides?] [A11y] [Voz] [Status]
```

- Scroll spy ativo (IntersectionObserver highlight em `.active`)
- Usa o estilo do design original — não inventar visual novo
- Links com `:focus-visible` ring

### Acessibilidade obrigatória (sempre)

Além da seção 08, aplicar em todo o doc:
- `:focus-visible` em todo CTA, link, botão
- `@media (prefers-reduced-motion:reduce)` reduzindo tudo pra 0.01ms
- Semantic HTML (`<nav>`, `<section>`, `<h1-h3>` hierárquicos)
- `aria-hidden="true"` em SVGs decorativos
- `rel="noopener"` em links externos + `aria-label` descritivo
- Contraste mínimo AA (4.5:1 texto normal, 3:1 texto grande)

---

### Passo 3 — Salvar e validar

1. Salvar o DS mestre em `contexto/design-system.html` e a extração da fonte em `contexto/design/refs/{slug}/design-system.html` (ver "Pasta de saída"). Conferir que `index.html` e `assets/` estão no mesmo nível da extração.
2. Abrir no navegador (Playwright ou comando do sistema) pra confirmar:
   - Todas as 11 seções renderizam (ou 10 se slide-types omitida)
   - Hero está idêntico ao original (exceto texto)
   - Animações funcionam
   - Nav sticky com scroll spy ativo
   - Focus rings visíveis ao usar Tab
   - Nenhum estilo inventado quebrou o visual original
3. Reportar ao usuário:
   - Caminho do arquivo gerado
   - Seções incluídas (+ razão se alguma foi omitida, ex: sem ícones, sem slide-types)
   - Tokens extraídos e declarados
   - Versão inicial registrada (v1.0 · YYYY-MM)

---

## Estratégia de geração de arquivo grande

Um `design-system.html` canônico fica tipicamente entre **1500–2000 linhas** (~70–150KB). Usar sempre **esqueleto + Edit incremental**:

1. Primeiro `Write` cria esqueleto pequeno com placeholders:
   ```html
   <!-- PLACEHOLDER_STYLE_TOKENS -->
   <!-- PLACEHOLDER_STYLE_ORIGINAL -->
   <!-- PLACEHOLDER_STYLE_DS -->
   <!-- PLACEHOLDER_HERO -->
   <!-- PLACEHOLDER_NAV -->
   <!-- PLACEHOLDER_SECTION_00_ANATOMIA -->
   <!-- PLACEHOLDER_SECTION_01_TIPOGRAFIA -->
   <!-- PLACEHOLDER_SECTION_02_CORES -->
   <!-- PLACEHOLDER_SECTION_03_COMPONENTES -->
   <!-- PLACEHOLDER_SECTION_04_LAYOUT -->
   <!-- PLACEHOLDER_SECTION_05_MOTION -->
   <!-- PLACEHOLDER_SECTION_06_ICONES -->
   <!-- PLACEHOLDER_SECTION_07_COMPOSICOES -->
   <!-- PLACEHOLDER_SECTION_08_ACESSIBILIDADE -->
   <!-- PLACEHOLDER_SECTION_09_VOZ -->
   <!-- PLACEHOLDER_SECTION_10_VERSIONAMENTO -->
   <!-- PLACEHOLDER_FOOTER -->
   <!-- PLACEHOLDER_SCRIPT -->
   ```
2. Depois usar `Edit` pra substituir cada placeholder (Edit envia só o diff).
3. Validar visualmente abrindo no navegador antes de dar como feito.

O Write tool falha silenciosamente em arquivos > 1500 linhas / 70KB — não confundir com rejeição do usuário.

---

## Checklist final (antes de reportar como feito)

### Estrutura
- [ ] DS mestre em `contexto/design-system.html` + extração em `contexto/design/refs/{slug-do-host}/`, tema confirmado
- [ ] `index.html` original baixado + `assets/` populado (CSS/JS/imagens locais re-roteadas)
- [ ] `design-system.html` referencia `assets/` por path relativo (roda offline)
- [ ] Hero clonado exato (só texto adaptado + stats badges DS)
- [ ] Nav sticky com âncoras pra todas as seções + scroll spy ativo
- [ ] **11 seções** presentes (ou 10 com justificativa no changelog pra omissão)

### Conteúdo das seções
- [ ] **00 Anatomia** — 6 slots + rules block + snippet HTML esqueleto
- [ ] **01 Tipografia** — apenas estilos existentes no original, com labels `XXpx / YYpx`
- [ ] **02 Cores** — swatches de backgrounds/bordas/gradientes/overlays/texto + "cores vetadas" explícitas
- [ ] **03 Componentes** — todos os estados (default/hover/active/focus/disabled) renderizados
- [ ] **04 Layout** — containers, grids, spacing tokens, breakpoints
- [ ] **05 Motion** — gallery com cada animação demonstrada + keyframes + easings
- [ ] **06 Ícones** — documentados (ou seção omitida se não houver)
- [ ] **07 Composições** — só se o original tiver padrões repetidos (omitir c/ justificativa)
- [ ] **08 Acessibilidade** — tabela de contraste + focus ring demo + regras
- [ ] **09 Voz** — traços/pontuação/casing/princípios + regras
- [ ] **10 Versionamento** — tabela de status + changelog (mínimo v1.0) + como contribuir

### Regras invioláveis (por seção)
- [ ] Toda seção numerada tem bloco `ds-rules-block` com `do` + `dont` em par
- [ ] Mínimo 5 regras em cada lado (do/dont)

### Tokens & classes
- [ ] `:root` declarado com **mínimo 25 tokens** extraídos do original
- [ ] Alpha variants do acento primário declaradas
- [ ] Focus ring canônico (`--focus-ring`) declarado
- [ ] Classes `.ds-*` de meta-documentação presentes (section-eyebrow, section-title, section-desc, subsection-title, rules-block, rules-box--do/--dont, meta-template)
- [ ] Headers de seção usam `.ds-section-*` (não Tailwind inline repetido)
- [ ] H3 sub-sections usam `.ds-subsection-title`

### Preservação do original
- [ ] Mesmas folhas de CSS/JS/fontes do original referenciadas
- [ ] Zero classes/estilos novos do design original introduzidos
- [ ] Classes originais preservadas 100% nos exemplos renderizados

### Acessibilidade
- [ ] `:focus-visible` em todo CTA/link
- [ ] `prefers-reduced-motion` implementado
- [ ] Semantic HTML (`<nav>`, `<section>`, h1-h3 hierárquicos)
- [ ] SVGs decorativos com `aria-hidden="true"`

### Idioma
- [ ] Texto explicativo em português brasileiro com acentos corretos (revisar hashtags, eyebrows, descrições)

### Validação visual
- [ ] Validado no navegador — sem regressões no design original
- [ ] Scroll spy na nav funcionando
- [ ] Hover states, focus rings e animações funcionais
