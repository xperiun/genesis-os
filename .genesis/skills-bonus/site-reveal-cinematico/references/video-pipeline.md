# Vídeo — pipeline do asset-herói

O vídeo scrubbed é o coração do site. Duas coisas importam: (1) ele **precisa ser all-keyframe**, (2) tem que ser **leve**.

## Por que all-keyframe

Pra fazer scrub suave (pular pra qualquer `currentTime` sem travar), todo frame precisa ser keyframe (I-frame). Vídeo normal usa P/B-frames pra comprimir e "treme"/trava no scrub, porque o browser tem que decodificar do keyframe anterior. Forçar GOP 1 = todo frame independente = scrub liso.

Custo: arquivo maior que o normal. Compensa com resolução/CRF (câmera fixa + fundo preto comprimem muito bem mesmo all-keyframe).

## Re-encode (obrigatório antes de servir)

```bash
# rodar da raiz do projeto
ffmpeg -y -i "FONTE.mp4" \
  -an -vf "scale=1280:-2" \
  -c:v libx264 -crf 30 -preset slow \
  -g 1 -keyint_min 1 -sc_threshold 0 \
  -pix_fmt yuv420p -movflags +faststart \
  "public/bg.mp4"
```

- `-g 1 -keyint_min 1 -sc_threshold 0` → **todo frame vira keyframe**.
- `-an` → sem áudio (o vídeo é `muted`).
- `scale=1280` + `crf 30` → alvo ~2-4MB. Subir CRF (menos qualidade) ou baixar resolução se precisar mais leve.
- Gerar também o poster (1º frame): `ffmpeg -i public/bg.mp4 -frames:v 1 -q:v 2 public/poster.jpg`

**Validar all-keyframe** (P/B tem que dar 0):
```bash
ffprobe -v error -select_streams v -show_entries frame=pict_type -of csv=p=0 public/bg.mp4 | grep -cE "P|B"
```

`*.mp4` é gitignored no repo (vídeos são pesados). Guardar o **vídeo-fonte** junto do projeto pra regenerar o `bg.mp4` em cada clone.

## Gerar o vídeo do zero com IA (Higgsfield + Seedance)

Se não tem render/gravação, dá pra gerar o reveal inteiro por IA. Técnica decupada da referência ABYSSAL (ver `referencias-visuais.md`):

1. **Imagem-herói de referência.** Gera UMA imagem do produto/asset no Higgsfield (ex: Nano Banana Pro, 16:9). Ex de prompt: *"Cinematic hero shot of [PRODUTO], [descrição do material/forma], suspended in dark [ambiente], single glowing [cor] accent, cinematic lighting, deep black background, 16:9."*

2. **Clipes encadeados.** Gera ~5 clipes Seedance 2.0 (std, 1080p, ~8-10s, sem áudio) passando a imagem-herói como **referência em todos**, pro asset ser idêntico em todos os clipes.

3. **Truque central (continuidade sem emenda):** usa o **frame final de cada clipe como frame inicial do próximo** (`start_image` / `end_image` do Seedance). Assim os 5 clipes viram **um vídeo contínuo** — descida, órbita, montagem, sem corte. É o que dá o reveal liso pro scrub.

   **Fluxo concreto do encadeamento (validado no v3, sequencial):**
   1. `generate_video` clipe 1 com `start_image` = a imagem-herói (ou uma imagem de início). Aguarda com `job_status(sync:true)`, baixa o `.mp4`.
   2. Extrai o **último frame**: `ffmpeg -sseof -0.15 -i clipN.mp4 -frames:v 1 -q:v 2 clipN-last.jpg`.
   3. **Sobe esse frame pro Higgsfield** (é o passo que falta na maioria): `media_upload{filename}` → devolve `upload_url` + `media_id` → `curl -X PUT --data-binary @clipN-last.jpg "<upload_url>"` → `media_confirm{type:"image", media_id}`.
   4. `generate_video` clipe N+1 com `start_image` = esse `media_id`. Pra manter o look, passar também `image_references` = a imagem-herói. No último clipe, `end_image` = a imagem-herói do destino pra pousar limpo.
   5. Repete. Depois **concatena** (`ffmpeg -f concat -safe 0 -i list.txt -c:v libx264 -crf 18 -an journey-full.mp4`) e confere a emenda (último frame do clipe N ≈ primeiro do N+1).
   6. Pro **canvas frame-sequence** (v3), extrai o `journey-full.mp4` em frames (`fps=8`), não precisa do re-encode all-keyframe. Pro `<video>` scrub (v1/v2), re-encoda all-keyframe.

4. **Estrutura de takes** (adaptar ao asset): HERO ORBIT (câmera orbita o produto) → MACRO FLYTHROUGH (entra no detalhe) → EXPLODED ASSEMBLY (componentes se montam). Pra um notebook: fechado → tampa abrindo → tela acendendo → dashboard montando.

5. **Câmera fixa vs em movimento:** câmera fixa (produto se abre no lugar) é limpa e legível. Câmera em movimento (descida/órbita contínua) dá mais "jornada" mas exige o encadeamento do passo 3. Escolher pelo tema.

Depois de gerar/baixar, **sempre passar pelo re-encode all-keyframe** acima antes de servir.

## Prompt Higgsfield via MCP

Fazer direto pelo **Higgsfield MCP** (conversando, sem skill): `mcp__claude_ai_Higgsfield__generate_image` pra a imagem-herói, `mcp__claude_ai_Higgsfield__generate_video` (Seedance) pros clipes com `start_image`/`end_image`. Requer o connector Higgsfield autenticado na sessão (`/mcp`).

### Quirks confirmados (build Marina Vhilar, 2026-07-13)

- **`model` E `prompt` vão DENTRO de `params`** (não só no top-level). Sem isso: `"prompt is required"` / `"expected string, received undefined"`. Ex: `params:{model:"seedance_2_0", prompt:"...", aspect_ratio:"16:9", duration:8, resolution:"1080p", mode:"std", generate_audio:false}`.
- **Preset recomendado bloqueia a geração literal.** Se voltar `notice.preset_recommendation` (ex "IN THE DARK") sem `results`, refazer com `declined_preset_id: "<id>"` DENTRO de `params` **e** suavizar o prompt (tirar as palavras que casam com o preset, ex trocar "deep black background/in the dark" por "warm amber light").
- **`job_id` da imagem serve direto como `start_image`** (`medias:[{role:"start_image", value:"<image-job-id>"}]`), não precisa re-upload.
- **Encadear clipes (continuidade sem emenda):** `ffmpeg -sseof -0.1 -i clipN.mp4 -frames:v 1 -q:v 2 last.jpg` → `media_upload{filename}` (devolve `upload_url`+`media_id`) → `curl -X PUT --data-binary @last.jpg "<upload_url>"` → `media_confirm{type:"image", media_id}` → usar esse `media_id` como `start_image` do próximo. Um 502 no `media_confirm` é transitório, retentar.
- **Consistência de identidade (retrato):** passar um retrato anterior como `medias:[{role:"image", value:"<job-id>"}]` no `soul_2` mantém a mesma pessoa em enquadramento novo.
- **Modelos usados:** `nano_banana_pro` (imagem-herói, `resolution:"4k"`), `soul_2` (retrato editorial, `quality:"2k"`), `seedance_2_0` (clipes, `resolution:"1080p"`, `mode:"std"`, `generate_audio:false`). 2 clipes de 8s → concat → all-keyframe = ~6.6MB / 16s.
