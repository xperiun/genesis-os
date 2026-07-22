# Motor HTML — como o deck funciona por dentro

Arquitetura, controller, animação e as armadilhas conhecidas. Este doc responde "como o slide funciona". Pra "como um slide deve ser", ver [gramatica-slide.md](./gramatica-slide.md). Pra "qual a cara dele", ver o seu DS ou [ds-sobrio.md](./ds-sobrio.md).

---

## 1. Um arquivo, sem build

Uma apresentação é **um único HTML** com CSS e JS inline. Sem dependência externa, sem build, sem framework. Abre no navegador e funciona, offline inclusive.

**Única exceção, imagens:** ficam na pasta ao lado do HTML, com caminho relativo (`./assets/foto.jpg`). Não usar base64 em imagem grande, incha o arquivo e o Write começa a falhar.

```
producao/apresentacoes/AAAA-MM-DD-nome/
├── index.html              ← a apresentação
├── briefing.md             ← as decisões que geraram ela
├── export-pdf-slides.js    ← gera o PDF
└── assets/                 ← imagens, se houver
```

Por que HTML e não PowerPoint: o deck vira um link, abre em qualquer máquina, não depende de fonte instalada, e você exporta PDF quando precisar mandar por email. E quem edita é você conversando comigo, não arrastando caixa de texto.

---

## 2. O esqueleto já vem pronto

O ponto de partida é sempre [`../templates/esqueleto.html`](../templates/esqueleto.html). **Copiar, nunca recriar do zero.** Ele já tem:

- Reset, `scroll-snap`, e a estrutura de `1 slide = 1 viewport`
- **Escala tipográfica calibrada pra widescreen** (`--size-big-number`, `--size-statement`, etc.). Não alterar, é o que garante a proporção 10:1
- **Placeholders de paleta e fonte** marcados `/* DS_TOKEN */`, pra receber o DS escolhido
- Variações de fundo (`.slide.dark-tl`, `.dark-tr`, `.dark-bl`, `.dark-br`, `.slide.light`)
- Classes de ornamento (`.bokeh-primary`, `-secondary`, `-tertiary`, mais as variantes `-light`)
- Helpers (`.overline`, `.punchline`, `.divider-accent`, `.big-number`, `.caption-italic`, `.statement`, `.source`, `.card`)
- Slide counter e nav dots, **sem marca fixa no canto**
- As 5 classes de reveal, com stagger automático
- O controller JS completo
- 3 slides de exemplo: capa, big number, CTA

Depois de copiar: trocar o `<title>`, adaptar a capa, apagar o slide de exemplo do meio, e inserir os slides reais por Edit.

---

## 3. O que o controller faz (e só isso)

**Navegação:** setas, PageUp/PageDown, Espaço, Home, End. Roda do mouse com scroll-snap nativo. Swipe no touch com limiar de 50px. Clique nas nav dots.

**Reveal:** um IntersectionObserver com `threshold: 0.5`. Slide metade visível ganha `.visible`, e os filhos `.reveal` entram em sequência via delay no CSS. **Sem GSAP, sem lib de animação.** CSS mais IO cobre tudo que um deck precisa.

**Contador:** `03 / 14` no canto superior direito, com zero à esquerda. Formato de documento, não de carrossel.

**Modo claro:** quando o slide visível tem `.light`, o JS põe `body.current-light`, e o CSS troca contador e dots pra versão de contraste. O JS só liga e desliga classe, quem pinta é o CSS.

Nenhum estado global além do índice atual. O DOM é a fonte da verdade.

---

## 4. Animação: uma bem feita vale por dez

> Um reveal orquestrado na entrada do slide vale mais que dez micro-interações espalhadas.

**Duração 0.6 a 0.9s, easing `cubic-bezier(0.16, 1, 0.3, 1)`.** Nada elástico, nada saltitante. A estética é editorial, não de app de celular.

**Banidos:** parallax, tilt 3D, cursor customizado. São bonitos em portfólio e destroem a credibilidade de um deck executivo.

### As 5 variações de reveal

Todas já estão no esqueleto. Trocar `.reveal` por uma delas quando o fade padrão ficar sem graça:

| Variação | Boa pra |
|---|---|
| `.reveal` | o padrão, fade subindo |
| `.reveal-scale` | big numbers, cards, o elemento focal |
| `.reveal-left` | listas numeradas, timeline, itens com borda à esquerda |
| `.reveal-right` | o lado visual de um slide de 2 colunas |
| `.reveal-blur` | citação, statement que "emerge" |

Combinação sugerida por tipo de slide:

| Slide | Combinação |
|---|---|
| T1 Capa | `.reveal` no geral, `.reveal-blur` no título |
| T3 Big statement | `.reveal-blur` na frase, `.reveal` no resto |
| T4 Big number | `.reveal-scale` no número, `.reveal` no contexto |
| T5 2 colunas | `.reveal` à esquerda, `.reveal-right` à direita |
| T6 Contraste | `.reveal-left` no antes, `.reveal-right` no depois |
| T7 Framework | `.reveal-scale` nos cards, o stagger cuida do resto |
| T8 Lista | `.reveal-left` em cada item |
| T9 Quote | `.reveal-blur` na citação |
| T11 CTA | `.reveal` no geral, `.reveal-scale` no botão |

### Reduced motion não é opcional

O bloco `@media (prefers-reduced-motion: reduce)` já vem no esqueleto e zera transform, filter e animação contínua. **Não remover.** Tem gente que sente enjoo com movimento na tela, e você não sabe quem está na plateia.

---

## 5. Acessibilidade (o mínimo que não se negocia)

- `<section class="slide">`, não `<div>`
- `aria-label` nas nav dots e no container de navegação
- Teclado navega o deck inteiro, sem depender de mouse
- `lang="pt-BR"` no `<html>` e `<title>` preenchido
- `alt` descritivo em toda `<img>`
- Em fundo claro, nunca usar accent de luminosidade alta em texto

---

## 6. Armadilhas conhecidas

**HTML grande faz o Write falhar por volta de 70KB.** Não é rejeição sua, é limite da ferramenta. Em deck com mais de 10 slides: primeiro escreva o esqueleto com comentários `<!-- SLIDE 4 -->` no lugar, depois substitua um por um com Edit.

**`-webkit-text-stroke` junto de `background-clip: text`** gera artefato preto. Escolha um dos dois, nunca os dois.

**`opacity` no container** apaga os filhos junto, texto incluso. Pra dar transparência só no fundo, use `rgba()` na cor.

**Gradiente em texto menor que 100px** vira borrão. Nesse tamanho, cor sólida com `text-shadow`.

**`100vh` no celular** pula quando a barra de endereço some. Usar `100dvh`.

**O primeiro slide não revela ao abrir**, porque o observer entra depois de ele já estar visível. O esqueleto já resolve com um `slides[0]?.classList.add('visible')` logo após criar o observer.

**Fonte demora a carregar** e o deck pisca. Usar `&display=swap` na URL do Google Fonts. Os `preconnect` já estão no esqueleto.

**Reveal disparando toda vez que você volta um slide:** falta `io.unobserve()` no callback.

**Stagger não funciona:** os elementos `.reveal` precisam ser irmãos diretos dentro do slide, senão o `nth-child` não pega.

---

## 7. Exportar PDF

```bash
node export-pdf-slides.js
```

Gera um PDF 1920x1080, uma página por slide, direto da pasta da apresentação. Serve pra mandar por email, anexar em proposta, ou pra quando o local do evento não deixa você usar a sua máquina.

O HTML continua sendo o original. O PDF é uma cópia congelada.
