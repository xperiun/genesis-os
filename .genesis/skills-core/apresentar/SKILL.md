---
name: apresentar
description: "Transforma um assunto em apresentação widescreen 16:9 que abre no navegador e exporta PDF. Aplica a gramática editorial de slide (um herói por slide, respiração, big number dominante) sobre o design system da própria pessoa, extraído do site dela. Todo número que vira herói de slide passa pela conferência antes. Use quando pedirem apresentação, slides, deck, pitch, talk, keynote, workshop, reunião de diretoria, prestação de contas, material pra projetar, ou pra transformar um relatório ou análise em algo apresentável."
---

# Apresentar

Você transforma assunto em deck. E se recusa a colocar na parede um número que não sabe de onde veio.

Slide de negócio falha de dois jeitos, e os dois são evitáveis. O primeiro é visual: a pessoa joga tudo que sabe no slide, o texto fica do mesmo tamanho do título, e ninguém olha pra tela porque não há pra onde olhar. O segundo é pior: o número gigante e bonito no meio do slide está errado, e alguém na sala sabe disso.

Esta skill resolve os dois na ordem certa. Primeiro o número, depois o design.

---

## O contrato

> **Nenhum número vira herói de slide sem você saber enunciar de onde ele veio.**
> Big number é a coisa mais lembrada de uma apresentação e a mais difícil de desmentir
> depois. Se o número saiu de uma planilha, ele passa pela `/analisar` antes de passar
> pro slide.

O elo é direto: a `/analisar` existe pra provar número, esta aqui existe pra projetar número. Pular a primeira e usar a segunda é construir a parte cara em cima da parte frágil.

Quando o número não vier de planilha e sim de uma fonte externa (pesquisa, relatório de mercado, notícia), a regra vira a fonte no próprio slide, em letra pequena embaixo do número. Sempre.

---

## Passe 1 — Entender o que é

Pergunte em bloco, de uma vez. Se a pessoa já respondeu algo na mensagem dela, não repita a pergunta.

1. **Pra quem** é a apresentação. "Diretoria", "cliente", "meu time", "investidor", "plateia de evento". Isso define tom e profundidade mais do que qualquer outra resposta.
2. **Quanto tempo** você tem. 5 min é 5 a 8 slides. 15 min é 10 a 15. 30 min é 15 a 25. Mais que isso, 25 ou mais.
3. **O que a pessoa deve fazer** ao sair da sala. Aprovar um orçamento, entender um resultado, comprar uma ideia, mudar uma decisão. Deck sem isso vira relatório lido em voz alta.
4. **O que você já tem.** Um documento pronto, uma análise que rodou aqui, uma planilha, ou só o assunto na cabeça.

Se a resposta 4 mencionar planilha ou número, aplique o contrato agora, não depois: rode a `/analisar` no arquivo antes de seguir. Descobrir no passe 5 que o número âncora estava errado significa refazer a narrativa inteira.

**Pasta de saída:** `producao/apresentacoes/AAAA-MM-DD-nome-curto/`. Nome curto e descritivo, sem acento e sem espaço.

---

## Passe 2 — Vestir

O deck precisa de uma cara, e ela não se inventa na hora.

**Ordem de preferência, nesta ordem:**

1. **O DS da pessoa.** Procure **`contexto/design-system.html`** (o DS mestre do OS, que é onde
   a `/extrair-design-system` grava). Se não estiver lá, olhe a biblioteca de referências em
   **`contexto/design/refs/<slug>/design-system.html`** e use a mais recente. É a identidade
   real da marca dela, tirada do site dela. Deck com a cara da própria empresa vale mais que
   deck bonito genérico.
   *(Não procure em `producao/`: ali ficam os entregáveis, não o DS. Este caminho já esteve
   errado aqui e o efeito era silencioso, o deck saía no sóbrio de reserva e ninguém entendia
   por que a marca não aparecia.)*
2. **Rodar o `/extrair-design-system` agora**, se ela tem site e ainda não rodou. Leva alguns
   minutos (a extração lê o site inteiro e baixa os assets), e o resultado serve pra todo deck
   futuro, não só pra este. Se a pessoa estiver com pressa, avise do tempo antes de começar.
3. **O sóbrio de reserva** em [referencias/ds-sobrio.md](./referencias/ds-sobrio.md). Tokens prontos pra colar. Use quando não houver marca, quando o deck for interno, ou quando a neutralidade for proposital.

**Nunca invente uma paleta.** Não escolha cor por gosto, não improvise fonte. Ou vem do DS dela, ou vem do sóbrio. Essas são as duas opções.

Anote no briefing qual foi usado. Na próxima apresentação, ninguém precisa perguntar de novo.

---

## Passe 3 — Narrar

Deck é argumento com ordem, não lista de tópicos com fundo bonito.

Monte o arco antes de escrever qualquer slide:

> **abertura → contexto → conflito → virada → resolução → o que fazer agora**

O **conflito** é o passe que quase todo mundo pula, e é o que faz a plateia prestar atenção. Sem tensão, os slides seguintes são só informação. Se a sua apresentação vai bem de "aqui está a situação" direto pra "aqui está o plano", falta o meio.

A **virada** é onde mora o big moment. Um ou dois slides do deck inteiro carregam o peso. Saiba quais são antes de construir, e proteja eles: são os que ganham o big number, a respiração maior, o silêncio na sala.

**Se o OS tem um agente cuja especialidade encaixa** (alguém de narrativa, de comunicação, do negócio em si), delegue o arco pra ele com o Task. O time foi escrito sob medida pra este negócio, ele sabe do assunto mais que a skill. Se não tiver, faça direto.

Depois do arco, distribua em slides usando os tipos do [referencias/gramatica-slide.md §1](./referencias/gramatica-slide.md). Cada movimento vira 1 a 3 slides. Registre a lista com tipo e modo (claro ou escuro) antes de abrir o HTML.

---

## Passe 4 — Escrever

Texto de slide é **ancoragem visual**, não narração. Quem narra é a pessoa apresentando. O slide segura o olho enquanto a boca trabalha.

- Uma ideia por slide, em frase curta
- Apoio mínimo. Se precisou de três linhas pra explicar, a ideia é grande demais pra um slide
- Frase de efeito só nos 3 ou 4 slides âncora. Em todos, vira ruído
- Português com acento, sempre. `não`, `você`, `é`, `métricas`, `análise`, `decisão`, `padrão`, `país`. Slide com erro de acento na parede queima quem apresenta

Vale a mesma regra do passe 3: se o OS tem agente de escrita ou de comunicação, delegue.

---

## Passe 5 — Construir e conferir

**Copie o esqueleto**, não recrie:

```bash
cp .claude/skills/apresentar/templates/esqueleto.html producao/apresentacoes/<pasta>/index.html
cp .claude/skills/apresentar/templates/export-pdf-slides.js producao/apresentacoes/<pasta>/
```

**Injete o DS:** o `<link>` das fontes no lugar do `<!-- FONTS_PLACEHOLDER -->`, e as cores nos placeholders `/* DS_TOKEN */` do `:root`. **Não mexa na escala tipográfica.** Ela vem calibrada pra projeção e é o que garante a proporção de 10 pra 1 entre o herói e o apoio.

**Preencha slide por slide com Edit**, não de uma vez com Write. Acima de mais ou menos 70KB o Write falha, às vezes em silêncio. Em deck com mais de 10 slides, deixe comentários `<!-- SLIDE 4 -->` no esqueleto e substitua um por um.

**Use só as variáveis CSS** (`var(--accent-primary)`, `var(--font-ornament)`). Cor em hex no meio do slide quebra o DS na primeira troca de identidade.

**Abra no navegador antes de dizer que está pronto.** Texto não mostra que o slide 7 estourou a caixa. Confira:

- O big number é pelo menos 10 vezes maior que o texto ao lado dele
- Nenhum slide tem barra de rolagem interna
- Setas e Espaço navegam, os dots funcionam
- Fonte do DS carregou de verdade (olhe o título, não o corpo)
- Slide claro não tem accent que sumiu no fundo claro
- O deck parece a marca dela, não um tema genérico
- Todo número na parede tem origem que você sabe dizer em voz alta

Erro é pra corrigir agora, com o arquivo aberto, não pra anotar como ressalva na entrega.

---

## Regras invioláveis

1. **Um herói por slide.** O big number domina, o resto encolhe. Slide sem hierarquia brutal é slide que ninguém olha. Detalhe em [referencias/gramatica-slide.md](./referencias/gramatica-slide.md).

2. **Metade do slide vazia é o certo.** Respiração é design, não desperdício. Quem enche o slide está com medo de o slide parecer vazio, e entrega um que parece dashboard projetado.

3. **Número sem procedência não sobe pra parede.** Veio de planilha, passa pela `/analisar`. Veio de fora, leva a fonte embaixo. Não tem nem um nem outro, ou vira estimativa rotulada como tal, ou sai do deck.

4. **Nada de marca fixa no canto.** O handle aparece na capa e no fechamento. Num pitch, todo slide já é sobre a marca, martelar logo em cada um é redundância.

5. **A escala tipográfica não se altera.** Ela é de slide, não de site. Tamanho de site num deck projetado deixa tudo do mesmo tamanho, e o slide perde o foco.

6. **O deck fica.** Ele mora em `producao/apresentacoes/` e é editável mês que vem, sem começar do zero. A pessoa não ganhou um arquivo, ganhou um formato que ela repete.

---

## Entregar

Ao terminar, mostre:

1. O caminho do `index.html`, pra ela abrir
2. Qual slide carrega o peso, e por quê
3. De onde veio cada número que virou herói
4. Que design system foi usado
5. Como exportar o PDF: `node export-pdf-slides.js` na pasta

E diga o que ficou fraco, se ficou. Deck com um slide morno que você identificou vale mais que deck entregue como perfeito e descoberto morno no meio da reunião.

---

## Quando dá errado

- **O deck ficou com cara genérica:** provavelmente o DS não foi injetado, só os placeholders default do esqueleto ficaram. Confira se o `:root` ainda tem `/* DS_TOKEN */` com os valores de exemplo.
- **O texto estourou a caixa em um slide:** conteúdo demais pra um slide só. Divida em dois. Nunca reduza a fonte pra caber, isso quebra a hierarquia do deck inteiro.
- **A fonte não carregou:** falta o `<link>` no lugar do `<!-- FONTS_PLACEHOLDER -->`, ou a máquina está sem internet. Google Fonts precisa de rede na primeira abertura.
- **O Write falhou sem explicar:** arquivo grande demais. Vá de Edit incremental.
- **Pediram formato de post ou carrossel:** esta skill faz widescreen 16:9, pra projetar. Formato vertical de rede social é outra coisa, com outra gramática.

---

## Referências

- **Como um slide deve funcionar** → [referencias/gramatica-slide.md](./referencias/gramatica-slide.md)
- **Como o HTML funciona por dentro** → [referencias/motor-html.md](./referencias/motor-html.md)
- **DS sóbrio de reserva** → [referencias/ds-sobrio.md](./referencias/ds-sobrio.md)
- **Esqueleto copiável** → [templates/esqueleto.html](./templates/esqueleto.html)
- **Exportador de PDF** → [templates/export-pdf-slides.js](./templates/export-pdf-slides.js)
