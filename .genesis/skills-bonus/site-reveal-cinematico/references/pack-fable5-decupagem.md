# Decupagem completa — "The One-Prompt Website Pack" (Fable 5 + Higgsfield)

Extração em texto do método que define o nível-alvo desta skill (o PDF `Fable5-Higgsfield-Website-Prompt-Pack.pdf` é imagem, não é buscável; este doc é o conteúdo dele + a decupagem do vídeo + o gap analysis).

- **Vídeo:** https://youtu.be/m-f56P_L660 — "Claude Fable 5 Built a $10K Website in Minutes", Zubair Trabzada (AI Workshop), 15:17.
- **PDF:** `Fable5-Higgsfield-Website-Prompt-Pack.pdf` (13 páginas) nesta pasta.
- **Frames brutos** (efêmeros): `.scratch/frames-video/` do projeto.

## O método (as 5 regras do pack)

1. **Cola o prompt inteiro, sem editar, na primeira vez.** Cada prompt é um brief completo: os planos de vídeo, a estrutura do site, a direção de design, e a instrução de lançar e verificar.
2. **O truque da hero-image é o que faz funcionar.** Gera UMA imagem-herói primeiro, passa como referência em TODO clipe de vídeo. É o que mantém o produto/pessoa/lugar idêntico em todos os planos.
3. **Encadeia clipes pra jornada "one continuous shot".** Seedance aceita `start_image` + `end_image`. Os prompts de jornada usam o **frame final de cada clipe como frame inicial do próximo** → 5 clipes que scrubam como um único movimento de câmera ininterrupto.
4. **Controla o gasto de crédito.** Default: `std`, 1080p, ~8s, sem áudio. Só sobe pra 4K no render final showpiece.
5. **Itera como diretor, não como dev.** Notas por sensação: "deixa o hero 20% mais lento", "essa seção tá chapada, adiciona uma interação sutil de cursor", "troca a fonte, tá genérica".

## As 3 estruturas de prompt (os arquétipos)

### Prompt 01 — Produto de luxo (AURUM & NOIR, relógio)
VISUALS (Seedance, std, 1080p, 16:9, ~8s): 1 imagem-herói do produto → 3 clipes: **HERO ORBIT** (turntable 360° do produto flutuando no void, rim light), **MACRO FLY-THROUGH** (close extremo glidando no detalhe), **EXPLODED ASSEMBLY** (produto se montando de componentes flutuantes).
WEBSITE: **scroll-scruba a hero orbit como canvas frame sequence** (rolar gira o produto). Lenis. Seções: hero com nome tracking-in → story ("Crafted in Darkness") → macro details scrubando o clipe 2 → exploded engineering view com spec callouts → "Edition of 88 — $48,000" → CTA de waitlist. Off-black + acento dourado + serifada display de alto contraste + sans mínima. Tom: quieto, caro, pouquíssimas palavras. Lança no localhost e verifica cada animação de scroll.
> "Make it yours": troca o relógio por qualquer produto (fone, perfume, tênis). Mantém orbit + macro + exploded-assembly.

### Prompt 02 — Experiência/jornada (ABYSSAL, mergulho)
VISUALS: 1 imagem-herói do submersível → **5 clipes encadeados** (frame final = início do próximo) numa descida única: THE SURFACE → SUNLIT ZONE → TWILIGHT ZONE → MIDNIGHT ZONE → THE FLOOR.
WEBSITE: **concatena os 5 clipes e scruba a descida inteira como canvas frame sequence: rolar pra baixo É mergulhar.** HUD fixo de profundidade contando 0m → 3.800m com labels de zona. Seções pinadas por zona: hero ("How deep will you go?") → um fato marcante por zona → spec callouts → "8 seats. $250,000. Departing March 2027." → "Join the Manifest" CTA. Fundo **color-grade** navy → preto puro com a profundidade. Acento ciano bioluminescente. Sans técnica fina com micro-detalhes de HUD.
> Mesma estrutura serve pra escalada de montanha, lançamento de foguete, tour de caverna, "jornada pela nossa fábrica".

### Prompt 03 — Portfólio pessoal (estrelando VOCÊ)
Referência declarada: **Awwwards Site of the Year 2025 (Lando Norris)** — tipografia bold gigante, sequências scroll-driven cinematográficas, e um **elemento 3D central que gira conforme o scroll**. No portfólio, o elemento central é a PESSOA.
VISUALS: **sobe a foto da pessoa no Higgsfield, passa como identity reference em TODA geração** (rosto consistente). 3 clipes: **HERO ORBIT** (a pessoa de braços cruzados num void preto, rim light, câmera orbita 360°), **THE BUILDER** (sentada numa mesa cercada de telas holográficas com o trabalho dela, push-in), **THE CLOSER** (andando pra câmera numa galeria escura de telas, para numa pose-herói).
WEBSITE: scroll-scruba a hero orbit como canvas frame sequence. "[NOME]" em display gigante tracking letra-por-letra. Stats counting-up no scroll. THREE PILLARS sobre o clipe 2. WORK sobre o clipe 3 com cards dos 3 melhores projetos + hover motion. FINALE com CTA + footer social. Ink-black + acento esmeralda + tipografia cream + display **bold condensado**, kinetic type, grão sutil, Lenis.

## Pro-tips do vídeo
- **Consistência > qualidade.** Um clipe um pouco mais mole com o produto idêntico parece mais caro que 4 clipes lindos com o produto variando. Sempre usa a hero-image de referência.
- **Gera 2-3 takes só do hero clip.** O hero scrub é 80% do "wow". Gasta o crédito extra ali, pega o primeiro aceitável no resto.
- **Pede pro Claude comprimir os vídeos.** "compress the videos for web" corta ~90% do tamanho e deixa o scroll buttery. (= nosso re-encode all-keyframe, ver `video-pipeline.md`.)
- **Ir pro ar é mais um prompt.** GitHub → Cloudflare Pages → domínio.
- **O negócio de verdade são os prompts 5, 6, 10** (restaurantes, corretores, academias): faz um de amostra, mostra pra 5 negócios, cobra $2.000+.

## O GAP — o que o pack faz vs o que a gente fazia (v1/v2)

| Dimensão | Pack (nível-alvo) | v1/v2 (antes) |
|---|---|---|
| Scrub | **Canvas frame-sequence** (frames desenhados no canvas por scroll) | `<video>.currentTime` (trema, inferior) |
| Duração | **3-5 clipes encadeados**, 24-50s contínuos, scruba a página inteira | 1 clipe de 8s, só num pin de hero |
| Espinha | O vídeo é a espinha da página (clipes por seção) | Hero-scrub e depois conteúdo estático |
| Sujeito | **Estrela o sujeito** (pessoa via identity ref / produto) | Abstrato (notebook / cluster), sem sujeito |
| Devices | HUD/medidor, color-grade no fundo, spec callouts, tipo letra-por-letra, grão | Só barra de progresso + stepper |
| Tipo | Editorial gigante condensado/serifado (Awwwards) | Grotesk, layout convencional |

## Como o v3 fecha o gap

O build **v3** (`producao/sites/portfolio-bi-template/v3/`) reconstruiu o motor pra esse nível:
- ✅ **Canvas frame-sequence scrub** (extrai frames → preload → desenha por scroll). Ver `motor.md` §canvas.
- ✅ **Jornada encadeada real** (3 clipes Seedance, frame final = início do próximo, 24s contínuos): voo pelo nebula de dados → streams organizando → dashboard montando.
- ✅ **HUD medidor** vertical (dado bruto → decisão, 0→100%).
- ✅ **Color-grade** no scroll + **grão de filme** + **tipo editorial** gigante.
- Pendente pra chegar 100% no prompt-03: **estrelar a pessoa** (o aluno com a própria foto via Higgsfield identity), em vez do reveal abstrato de dados. Decisão em aberto (exige cada aluno gerar com a própria foto).

## Reproduzir a decupagem de um vídeo novo
Usar `/resumir-video` no modo visual (baixa em baixa resolução, fatia frames com ffmpeg, monta contact sheet). Pra PDF imagem: renderizar com PyMuPDF (`fitz`) e ler as páginas. Salvar os achados AQUI (na skill), não no `.scratch`.
