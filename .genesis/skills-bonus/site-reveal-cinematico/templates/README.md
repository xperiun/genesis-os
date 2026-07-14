# Seu portfólio de dados — template

Um site cinematográfico pronto pra você usar como **portfólio** ou como site da **sua consultoria de dados**. Conforme a pessoa rola a página, um vídeo se monta no fundo (um notebook que abre revelando um dashboard) e o texto entra em blocos, com uma galeria dos seus dashboards, seus números e seus contatos.

Ele já vem preenchido com um exemplo (a consultoria fictícia "Cota Dados") pra você ver como fica pronto. Seu trabalho é **trocar o exemplo pelo seu**.

---

## 1. Rodar no seu computador

```bash
npm install
npm run dev
```

Abre **http://localhost:5173/**. Toda mudança que você salvar aparece no navegador na hora.

> ⚠️ **Não abra o `index.html` no Live Server nem com dois cliques.** Esse site é montado pelo Vite (o `npm run dev`). Aberto direto, ele fica sem estilo (preto e branco). Sempre use `npm run dev`.

---

## 2. O que trocar pra ficar seu (na ordem)

Abra os arquivos num editor (VS Code) e troque:

**a) Seu nome / marca** — no `index.html`, procure por `Cota Dados` e `CotaDados` e troque pelo seu nome ou o nome da sua consultoria. Aparece no topo, no rodapé e no título da aba.

**b) Sua cor** — no `src/style.css`, no comecinho, tem `--accent: #C5F82A;` (o verde-limão). Troque pelo hex da sua cor. Ela re-tinge botões, números e detalhes de uma vez só.

**c) Seus dashboards** — coloque suas imagens em `public/dashs/` (JPG ou PNG). Depois, no `index.html`, na seção de **cases**, troque os `src="/dashs/..."` pelos nomes dos seus arquivos e reescreva o título e o texto de cada um (que projeto era, o que o painel resolveu). Podem ser claros ou escuros, os dois ficam bem.

**d) Seus números** — na seção de **stats** (aqueles números grandes), troque pelos seus de verdade (quantos dashboards entregou, horas economizadas, áreas atendidas). Se não tiver número real, tire ou marque como estimativa. **Não invente.**

**e) Seus textos** — reescreva os blocos do topo, o "sobre" e o contato pra falar de você, na sua voz. Fale a dor do seu cliente e o que você resolve.

**f) Seus contatos** — procure `wa.me/5500000000000` (WhatsApp), o link do LinkedIn e o e-mail, e troque pelos seus.

**g) O vídeo do reveal (opcional)** — o site já vem com um vídeo genérico de dados se montando. Se quiser usar o seu (um render, uma gravação de tela), veja o passo abaixo.

---

## 3. Trocar o vídeo do reveal (opcional, mais técnico)

O vídeo precisa ser **"all-keyframe"** senão trava quando você rola. Com o [ffmpeg](https://ffmpeg.org) instalado, rode (troque `SEU-VIDEO.mp4`):

```bash
ffmpeg -y -i "SEU-VIDEO.mp4" -an -vf "scale=1280:-2" \
  -c:v libx264 -crf 30 -preset slow -g 1 -keyint_min 1 -sc_threshold 0 \
  -pix_fmt yuv420p -movflags +faststart "public/bg.mp4"
```

Depois gere o poster (primeiro quadro):
```bash
ffmpeg -y -i public/bg.mp4 -frames:v 1 -q:v 2 public/poster.jpg
```

Dá refresh no navegador. Se não quiser mexer nisso, é só deixar o vídeo que já vem.

---

## 4. Publicar (colocar no ar)

```bash
npm run build
```

Isso gera a pasta `dist/`, que é o site pronto pra hospedar (Cloudflare Pages, Netlify, Vercel, qualquer um). Suba a pasta `dist/` no serviço de sua preferência.

> Atenção: o vídeo (`bg.mp4`) precisa ir junto no deploy. Se seu serviço puxa do GitHub, confirme que o `.mp4` está subindo (alguns projetos ignoram vídeo por padrão).

---

## 5. Uma regra de ouro

Esse site vai te representar na frente de recrutador e cliente. **Todo número e todo case tem que ser verdade** (ou marcado como exemplo/ilustrativo). Um dado inflado que a pessoa descobre queima sua credibilidade na hora. Mostre o trabalho real, ele já é bom o suficiente.

---

*Template da Xperiun. Feito com a skill `/site-reveal-cinematico`.*
