// Preflight: checa os pré-requisitos do site reveal-cinematográfico e diz o que falta.
// Rodar: `npm run preflight`  (ou `node scripts/preflight.mjs`)
// Não instala nada sozinho — só reporta o estado e o comando de correção por SO.
import { execSync } from 'node:child_process';
import { existsSync } from 'node:fs';
import os from 'node:os';

const plat = os.platform(); // 'win32' | 'darwin' | 'linux'
const ok = (m) => console.log(`  \x1b[32m✓\x1b[0m ${m}`);
const miss = (m) => console.log(`  \x1b[31m✗\x1b[0m ${m}`);
const hint = (m) => console.log(`      → ${m}`);

function has(cmd) {
  try { execSync(cmd, { stdio: 'ignore' }); return true; } catch { return false; }
}

const ffmpegInstall = {
  win32: 'winget install Gyan.FFmpeg   (ou: choco install ffmpeg)',
  darwin: 'brew install ffmpeg',
  linux: 'sudo apt install ffmpeg   (ou o gerenciador da sua distro)',
};

console.log('\n\x1b[1mPreflight — site reveal cinematográfico\x1b[0m\n');

// 1. Node
const nodeMajor = parseInt(process.versions.node.split('.')[0], 10);
if (nodeMajor >= 18) ok(`Node ${process.versions.node}`);
else { miss(`Node ${process.versions.node} (precisa >= 18)`); hint('instale a versão LTS em https://nodejs.org'); }

// 2. Dependências npm instaladas
if (existsSync(new URL('../node_modules/vite/package.json', import.meta.url))) ok('Dependências npm (vite, gsap, lenis)');
else { miss('Dependências npm não instaladas'); hint('rode: npm install'); }

// 3. ffmpeg (necessário pra re-encodar o vídeo all-keyframe e extrair frames)
if (has('ffmpeg -version')) ok('ffmpeg');
else { miss('ffmpeg não encontrado (necessário pro vídeo do reveal)'); hint(ffmpegInstall[plat] || ffmpegInstall.linux); }

// 4. Playwright chromium (opcional — só pro verification loop de screenshots)
const pwInstalled = existsSync(new URL('../node_modules/playwright/package.json', import.meta.url));
if (pwInstalled && has('npx playwright --version')) {
  ok('Playwright (verification loop)');
  hint('se os screenshots falharem por falta de browser: npx playwright install chromium');
} else {
  miss('Playwright não pronto (opcional — só pro verification loop)');
  hint('rode: npm install  e depois  npx playwright install chromium');
}

console.log('\n\x1b[2mHiggsfield (gerar o vídeo por IA) é opcional e configurado à parte via MCP no Claude Code — ver COMECE-AQUI.md.\x1b[0m\n');
