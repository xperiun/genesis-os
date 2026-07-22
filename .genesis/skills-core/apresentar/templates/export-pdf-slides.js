// Exportador PDF do /apresentar (widescreen 16:9, DS-agnostic)
//
// Lê `index.html` (ou outro HTML passado como argumento) da pasta da apresentação,
// navega slide por slide via JS (não scroll nativo, pra evitar conflito com scroll-snap),
// tira um screenshot de cada .slide num viewport 1920x1080, e monta um PDF único.
//
// Uso: copiar este arquivo pra pasta da apresentação (producao/apresentacoes/AAAA-MM/AAAA-MM-DD-nome/)
// e rodar:
//     node export-pdf-slides.js                 # usa index.html, output = apresentacao-<pasta>.pdf
//     node export-pdf-slides.js meu-deck.html   # usa meu-deck.html
//     node export-pdf-slides.js --compact       # 1280x720 em vez de 1920x1080 (PDF menor)
//
// Pré-requisitos:
// - index.html (ou arquivo passado) existe na pasta
// - Imagens referenciadas existem em paths relativos
// - Playwright instalado (`npx playwright install chromium`)
//
// Output:
// - apresentacao-<nome-da-pasta>.pdf (1920x1080 por página, N páginas = N slides)
//
// Este é o template mantido em .claude/skills/apresentar/templates/.
// NÃO editar a cópia local — fazer ajustes aqui e copiar.

const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");

async function main() {
  const dir = __dirname;
  const args = process.argv.slice(2);

  // Parse args: arquivo HTML + flags
  const compact = args.includes("--compact");
  const htmlArg = args.find((a) => !a.startsWith("--"));
  const htmlFile = htmlArg || "index.html";
  const htmlPath = path.join(dir, htmlFile);

  if (!fs.existsSync(htmlPath)) {
    console.error(`❌ Arquivo não encontrado: ${htmlFile}`);
    console.error(`   Esperado em: ${htmlPath}`);
    process.exit(1);
  }

  const width = compact ? 1280 : 1920;
  const height = compact ? 720 : 1080;

  console.log(`\nExportando apresentação → PDF...`);
  console.log(`  HTML:     ${htmlFile}`);
  console.log(`  Viewport: ${width}x${height}${compact ? " (compact)" : ""}\n`);

  const browser = await chromium.launch();
  const ctx = await browser.newContext({
    viewport: { width, height },
    deviceScaleFactor: 2, // 2x pra qualidade
  });
  const page = await ctx.newPage();

  // file:// com ?export=1 — o JS controller esconde UI (progress, nav dots, counter)
  const fileUrl = `file://${htmlPath.replace(/\\/g, "/")}?export=1`;
  await page.goto(fileUrl, { waitUntil: "networkidle" });

  // Espera fontes carregarem (2-4 famílias do DS escolhido — timeout suficiente pra Google Fonts)
  await page.waitForTimeout(2500);

  // Desabilitar scroll-snap + liberar overflow + height fixo nos slides
  // (evita bug onde html/body com height:100% limita scroll a 1 viewport)
  await page.addStyleTag({
    content: `
      html, body {
        height: auto !important;
        min-height: auto !important;
        overflow-y: visible !important;
        overflow-x: hidden !important;
        scroll-snap-type: none !important;
      }
      .slide {
        height: ${height}px !important;
        min-height: ${height}px !important;
        scroll-snap-align: unset !important;
      }
    `,
  });
  await page.waitForTimeout(300);

  // Descobrir quantos slides existem
  const slideCount = await page.evaluate(
    () => document.querySelectorAll(".slide").length
  );

  if (slideCount === 0) {
    console.error("❌ Nenhum .slide encontrado no HTML.");
    await browser.close();
    process.exit(1);
  }

  console.log(`${slideCount} slides detectados. Capturando...\n`);

  // Capturar cada slide como screenshot base64
  const screenshots = [];

  for (let i = 0; i < slideCount; i++) {
    // Rolar até o slide: usar idx * height (slides agora têm height fixo via addStyleTag acima)
    await page.evaluate(
      ({ idx, h }) => {
        const slides = document.querySelectorAll(".slide");
        const target = slides[idx];
        if (!target) return;
        // Scroll direto por cálculo (mais confiável que offsetTop quando há scroll-snap)
        window.scrollTo(0, idx * h);
        // Forçar classe .visible pra disparar reveal animations
        target.classList.add("visible");
      },
      { idx: i, h: height }
    );

    // Esperar animações terminarem (stagger vai até ~1s)
    await page.waitForTimeout(1200);

    // Screenshot do viewport inteiro
    const buf = await page.screenshot({
      clip: { x: 0, y: 0, width, height },
      type: "png",
    });

    screenshots.push(`data:image/png;base64,${buf.toString("base64")}`);
    console.log(`  ✓ slide ${i + 1}/${slideCount}`);
  }

  await page.close();

  // Montar HTML único com os screenshots empilhados, cada um numa página
  console.log(`\nMontando PDF...`);

  const slidesHTML = screenshots
    .map(
      (dataUrl) =>
        `<div class="page-break"><img src="${dataUrl}" style="width:${width}px;height:${height}px;display:block;" /></div>`
    )
    .join("");

  const fullHTML = `<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<style>
*,*::before,*::after{margin:0;padding:0;box-sizing:border-box;}
@media print {
  @page {
    size: ${width}px ${height}px;
    margin: 0;
  }
  body { margin: 0; }
  .page-break {
    page-break-after: always;
    width: ${width}px;
    height: ${height}px;
    overflow: hidden;
  }
  .page-break:last-child {
    page-break-after: avoid;
  }
}
.page-break {
  width: ${width}px;
  height: ${height}px;
  overflow: hidden;
}
</style>
</head>
<body>${slidesHTML}</body>
</html>`;

  const pdfPage = await ctx.newPage();
  await pdfPage.setContent(fullHTML, { waitUntil: "networkidle" });
  await pdfPage.waitForTimeout(500);

  const folderName = path.basename(dir);
  const pdfName = `apresentacao-${folderName}${compact ? "-compact" : ""}.pdf`;
  const pdfPath = path.join(dir, pdfName);

  await pdfPage.pdf({
    path: pdfPath,
    width: `${width}px`,
    height: `${height}px`,
    margin: { top: 0, right: 0, bottom: 0, left: 0 },
    printBackground: true,
  });

  const sizeMB = (fs.statSync(pdfPath).size / 1024 / 1024).toFixed(1);
  console.log(`\n✓ PDF gerado: ${pdfName} (${sizeMB} MB, ${slideCount} páginas)`);

  await browser.close();
}

main().catch((err) => {
  console.error("Erro:", err);
  process.exit(1);
});
