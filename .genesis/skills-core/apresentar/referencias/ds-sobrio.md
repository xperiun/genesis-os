# DS Sóbrio — o visual de reserva do `/apresentar`

Este é o **plano B**, não o plano A.

O plano A é o **seu** design system: aquele que o `/extrair-design-system` tirou do seu site,
do seu material, da sua marca. Deck com a sua identidade sempre ganha de deck com identidade
emprestada, mesmo que a emprestada seja bonita.

Use este aqui quando:

- você ainda não rodou o `/extrair-design-system`
- a marca não tem identidade visual definida
- o deck é interno e ninguém liga pra marca
- é um pitch pra um terceiro e você quer neutralidade proposital

Ele é **corporate sóbrio**: dark, tipografia limpa, um accent só, ornamento discreto. Não
chama atenção pra si, deixa o conteúdo falar. É o terno cinza dos design systems.

---

## Vibe em uma frase

> Dark executivo com um accent teal. Sóbrio, respirado, nada de neon. Serifa só nos heróis.

---

## Tokens

Cole direto no `:root` do `esqueleto.html`, substituindo os placeholders `/* DS_TOKEN */`.

```css
:root {
  /* --- Background dark (3 stops do gradient radial) --- */
  --bg-dark-1: #16161C;
  --bg-dark-2: #0D0D12;
  --bg-dark-3: #060609;

  /* --- Background light --- */
  --bg-light:      #F5F3EF;
  --bg-light-card: #FFFFFF;

  /* --- Accents: uma cor só, em três intensidades --- */
  /* O DS sóbrio tem UM accent. Os três slots são a mesma teal em intensidades
     diferentes, não três cores. É o que mantém o deck monocromático.
     ATENÇÃO ao tertiary: o esqueleto troca overline, nav dot e contador pra ELE
     nos slides claros. Se você puser uma cor clara ou de outra família aí, todo
     slide light sai com um acento estranho. Ele TEM que ser a variante escura. */
  --accent-primary:   #31B0A6;  /* teal — o accent, em fundo escuro (7.4:1) */
  --accent-secondary: #93E3DA;  /* teal claro — realce leve, ornamento */
  --accent-tertiary:  #1B8177;  /* teal escuro — é o que o modo claro usa (4.3:1 em cream) */

  /* --- Texto --- */
  --text-on-dark:       #FFFFFF;
  --text-on-dark-soft:  rgba(255,255,255,.70);
  --text-on-light:      #1A1A1A;
  --text-muted:         #737373;

  /* --- Fontes --- */
  --font-sans:     'Inter', system-ui, sans-serif;
  --font-ornament: 'Playfair Display', Georgia, serif;
  --font-display:  'Inter', system-ui, sans-serif;  /* não tem display próprio, repete a sans */
}
```

### Link das fontes

Vai no `<head>`, no lugar do `<!-- FONTS_PLACEHOLDER -->`:

```html
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Playfair+Display:ital,wght@0,700;0,800;1,700&display=swap" rel="stylesheet">
```

---

## Como aplicar (as 3 decisões que importam)

**1. Ornamentação: gradient radial, não bokeh.**
Este DS é sóbrio. Os `<div class="bokeh">` do esqueleto são pra visual maximalista. Aqui:
remova dois dos três, deixe um só com opacidade baixa (`8-10%`), ou apague todos e deixe o
gradient radial do `.slide` trabalhar sozinho. Glow demais num DS corporate parece erro.

**2. A serifa é exclusiva dos heróis.**
`Playfair Display` só em: título da capa, big numbers, e a punchline de fechamento. Todo o
resto é `Inter`. Serifa em texto de apoio deixa o slide com cara de convite de casamento.

**3. Em slide claro, o teal já escurece sozinho.**
`#31B0A6` sobre `#F5F3EF` tem contraste baixo demais pra texto. Como o `--accent-tertiary`
desta tabela já é a variante escura, e o esqueleto troca pra ela nos slides `.light`, isso
resolve sem você fazer nada. **Só não troque o tertiary por outra cor**, senão quebra.

Se você escrever um destaque à mão dentro de um slide claro, use o tertiary pelo nome, nunca
o primary:

```html
<span style="color: var(--accent-tertiary)">a palavra destacada</span>
```

**Precisa de verde e vermelho** pra "melhorou / piorou" num gráfico? Use `#1F8A5F` e `#B4443C`
inline no elemento, sem promover a token de accent. Eles são semântica de dado, não
identidade. Cor de marca é uma só.

---

## Se você quiser trocar só a cor

O accent é o único ponto onde este DS aceita personalização sem virar outra coisa. Trocar
`#31B0A6` pela cor da sua marca funciona, desde que:

- a cor tenha contraste ≥ 4.5:1 sobre `#0D0D12` (texto) — teste antes
- você troque também a variante escura pro modo light
- você não adicione uma segunda cor de marca. Um accent. Esse é o ponto do DS sóbrio.

Se a sua marca tem duas ou três cores que importam, você não quer este DS. Você quer rodar o
`/extrair-design-system` no seu material e usar o resultado.
