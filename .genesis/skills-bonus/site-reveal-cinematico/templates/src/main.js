import './style.css';
import './glass.css';
import './enhance.css';
import Lenis from 'lenis';
import gsap from 'gsap';
import ScrollTrigger from 'gsap/ScrollTrigger';

gsap.registerPlugin(ScrollTrigger);

const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
const fine = matchMedia('(pointer:fine)').matches;
const clamp = (v, a = 0, b = 1) => Math.min(Math.max(v, a), b);
/* ramp 0→1 entre inA..inB, segura em 1, cai 1→0 entre outA..outB (opcionais) */
function seg(p, inA, inB, outA, outB) {
  if (p < inA) return 0;
  if (p < inB) return (p - inA) / (inB - inA);
  if (outA == null) return 1;
  if (p < outA) return 1;
  if (p < outB) return 1 - (p - outA) / (outB - outA);
  return 0;
}

/* ---------- Lenis smooth scroll (desligado sob prefers-reduced-motion) ---------- */
let lenis = null;
if (!reduce) {
  lenis = new Lenis({ duration: 1.1, smoothWheel: true });
  window.__lenis = lenis;
  lenis.on('scroll', ScrollTrigger.update);
  gsap.ticker.add((t) => lenis.raf(t * 1000));
  gsap.ticker.lagSmoothing(0);
}
const scrollToId = (id) => {
  if (lenis) lenis.scrollTo(id, { offset: 0 });
  else document.querySelector(id)?.scrollIntoView({ behavior: 'auto' });
};

/* ---------- background video (scrubbed apenas no pin do hero) ---------- */
const bgv = document.getElementById('bgv');
window.__bgv = bgv;
let videoReady = false, lastT = -1;

function seek(p) {
  if (!videoReady || !bgv.duration) return;
  const t = clamp(p, 0, 1) * (bgv.duration - 0.05);
  if (Math.abs(t - lastT) > 0.008) { try { bgv.currentTime = t; lastT = t; } catch (e) {} }
}

function onVideoReady() {
  if (videoReady) return;
  videoReady = true;
  try { bgv.pause(); } catch (e) {}
  seek(0);
  hidePreloader();
}
// revela no primeiro frame disponível (vídeo leve all-keyframe carrega rápido); segue bufferizando
bgv.addEventListener('loadeddata', () => { if (bgv.readyState >= 2) onVideoReady(); });
bgv.addEventListener('canplay', onVideoReady);
bgv.addEventListener('canplaythrough', onVideoReady);
setTimeout(() => { if (!videoReady) { videoReady = !!bgv.duration; seek(0); hidePreloader(); } }, 2500);

/* ---------- preloader ---------- */
const preloader = document.getElementById('preloader');
let hidden = false;
function hidePreloader() {
  if (hidden) return; hidden = true;
  preloader.classList.add('done');
  document.body.style.removeProperty('overflow');
  startHero();
  ScrollTrigger.refresh();
}

/* ---------- nav ---------- */
const nav = document.getElementById('nav');
const setNav = () => nav.classList.toggle('scrolled', window.scrollY > 40);
setNav(); window.addEventListener('scroll', setNav, { passive: true });
const burger = document.getElementById('burger'), navlinks = document.getElementById('navlinks');
burger.addEventListener('click', () => { burger.classList.toggle('x'); navlinks.classList.toggle('open'); });
navlinks.querySelectorAll('a').forEach(a => a.addEventListener('click', (e) => {
  burger.classList.remove('x'); navlinks.classList.remove('open');
  const id = a.getAttribute('href');
  if (id && id.startsWith('#')) { e.preventDefault(); scrollToId(id); }
}));

/* ---------- custom cursor ---------- */
if (fine && !reduce) {
  const cur = document.getElementById('cursor');
  let cx = 0, cy = 0, tx = 0, ty = 0, shown = false;
  addEventListener('mousemove', (e) => { tx = e.clientX; ty = e.clientY; if (!shown) { shown = true; cur.classList.add('on'); } });
  const loop = () => { cx += (tx - cx) * .2; cy += (ty - cy) * .2; cur.style.left = cx + 'px'; cur.style.top = cy + 'px'; requestAnimationFrame(loop); };
  loop();
  document.querySelectorAll('a,button,[data-h]').forEach(el => {
    el.addEventListener('mouseenter', () => cur.classList.add('hover'));
    el.addEventListener('mouseleave', () => cur.classList.remove('hover'));
  });
}

/* ---------- hero intro (fade suave da copy inicial) ---------- */
function startHero() {
  const copy = document.querySelector('.rhero__copy');
  if (copy) copy.classList.add('ready');
}

/* ---------- REVEAL HERO: pin com scrub do vídeo + copy em BEATS ---------- */
(function setupRevealHero() {
  const pin = document.querySelector('.rhero__pin');
  if (!pin) return;
  const eye = document.querySelector('.rh-eye');
  const beats = [...document.querySelectorAll('.rh-beat')];
  const sub = document.querySelector('.rh-sub');
  const cta = document.querySelector('.rh-cta');
  const cue = document.getElementById('rhCue');
  const prog = document.getElementById('rhProg');
  const steps = document.getElementById('rhSteps');
  const stepEls = steps ? [...steps.children] : [];

  // janelas de cada beat sincronizadas com o notebook: fechado → abrindo → tela acende → dashboard cheio
  // [entra_ini, entra_fim, sai_ini, sai_fim]  (último beat sem saída)
  const WIN = [
    [0.03, 0.12, 0.19, 0.27],
    [0.28, 0.37, 0.45, 0.53],
    [0.54, 0.63, 0.69, 0.75],
    [0.76, 0.85, null, null],
  ];
  const SUB = [0.87, 0.94];
  const CTA = [0.91, 0.99];

  const setLine = (el, opShow, enterP) => {
    if (!el) return;
    el.style.opacity = opShow.toFixed(3);
    el.style.pointerEvents = opShow > 0.5 ? 'auto' : 'none';
    [...el.children].forEach((s, i) => {
      const so = clamp((enterP - i * 0.16) / 0.6);
      s.style.transform = `translateY(${((1 - so) * 26).toFixed(1)}px)`;
      s.style.filter = `blur(${((1 - so) * 7).toFixed(1)}px)`;
    });
  };
  const setBlock = (el, op) => {
    if (!el) return;
    el.style.opacity = op.toFixed(3);
    el.style.transform = `translateY(${((1 - op) * 20).toFixed(1)}px)`;
    el.style.pointerEvents = op > 0.5 ? 'auto' : 'none';
  };

  const render = (p) => {
    seek(p);
    if (eye) eye.style.opacity = seg(p, 0, 0.05).toFixed(3);
    beats.forEach((el, i) => {
      const w = WIN[i] || WIN[WIN.length - 1];
      setLine(el, seg(p, w[0], w[1], w[2], w[3]), seg(p, w[0], w[1]));
    });
    setBlock(sub, seg(p, SUB[0], SUB[1]));
    setBlock(cta, seg(p, CTA[0], CTA[1]));
    if (cue) cue.style.opacity = (1 - seg(p, 0, 0.10)).toFixed(3);
    // barra de progresso do reveal (aparece durante a rolagem, some no fim)
    const chrome = seg(p, 0.02, 0.08) * (1 - seg(p, 0.92, 1));
    if (prog) {
      prog.style.transform = `scaleX(${p.toFixed(4)})`;
      prog.style.opacity = chrome.toFixed(3);
    }
    // stepper rotulado: dado bruto → modelo → painel → decisão
    if (steps) {
      steps.style.opacity = chrome.toFixed(3);
      const idx = p < 0.28 ? 0 : p < 0.53 ? 1 : p < 0.75 ? 2 : 3;
      stepEls.forEach((s, i) => s.classList.toggle('on', i === idx));
    }
  };

  if (reduce) {
    seek(1);
    if (eye) eye.style.opacity = 1;
    beats.forEach((el, i) => setLine(el, i === beats.length - 1 ? 1 : 0, 1));
    setBlock(sub, 1); setBlock(cta, 1);
    if (cue) cue.style.opacity = 0;
    if (prog) prog.style.opacity = 0;
    if (steps) steps.style.opacity = 0;
    return;
  }

  render(0);
  ScrollTrigger.create({
    trigger: '.rhero', start: 'top top',
    end: () => '+=' + (innerHeight * 5.4),
    pin: '.rhero__pin', scrub: 1, anticipatePin: 1,
    onUpdate: (self) => render(self.progress),
  });
  window.__ST = ScrollTrigger;
})();

/* ---------- BG shade: escurece o dashboard congelado atrás do conteúdo ---------- */
(function setupBgShade() {
  const shade = document.querySelector('.bg-shade');
  if (!shade) return;
  const cap = matchMedia('(max-width:900px)').matches ? 0.95 : 0.82;
  if (reduce) { shade.style.opacity = cap; return; }
  ScrollTrigger.create({
    trigger: '#impact', start: 'top bottom', end: 'top center',
    onUpdate: (s) => { shade.style.opacity = (s.progress * cap).toFixed(3); },
  });
})();

/* ---------- generic reveals ---------- */
document.querySelectorAll('.stats-sec .stat, .cap, .about-txt, .quote, .contact .lead, .contact .hero__cta, .showcase .section-head, .studio .secnum, .case-card, .cases .section-head, .stmt__line, .stmt__stage')
  .forEach(el => el.classList.add('reveal'));
const io = new IntersectionObserver((es) => {
  es.forEach((e) => { if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); } });
}, { threshold: .15, rootMargin: '0px 0px -8% 0px' });
document.querySelectorAll('.reveal').forEach(el => io.observe(el));

/* ---------- count-up ---------- */
const cio = new IntersectionObserver((es) => {
  es.forEach(e => {
    if (!e.isIntersecting) return; cio.unobserve(e.target);
    const el = e.target, end = parseFloat(el.dataset.count), dec = parseInt(el.dataset.dec || '0', 10);
    if (reduce) { el.textContent = end.toLocaleString('pt-BR', { minimumFractionDigits: dec, maximumFractionDigits: dec }); return; }
    el.textContent = '0'; let t0 = null;
    const step = (ts) => { t0 = t0 || ts; const p = Math.min((ts - t0) / 1500, 1); const v = (1 - Math.pow(1 - p, 3)) * end;
      el.textContent = v.toLocaleString('pt-BR', { minimumFractionDigits: dec, maximumFractionDigits: dec }); if (p < 1) requestAnimationFrame(step); };
    requestAnimationFrame(step);
  });
}, { threshold: .6 });
document.querySelectorAll('.cv').forEach(el => cio.observe(el));

/* ---------- IMPACT: pinned word-by-word reveal ---------- */
(function setupImpact() {
  const head = document.getElementById('impactHead');
  if (!head) return;
  const parts = [
    { t: 'A maioria das empresas ', a: 0 },
    { t: 'não tem falta de dados. ', a: 0 },
    { t: 'Tem falta de ', a: 0 },
    { t: 'alguém que faça o dado falar ', a: 1 },
    { t: 'na hora da decisão.', a: 0 },
  ];
  const words = [];
  parts.forEach(part => part.t.split(/(\s+)/).forEach(w => {
    if (w === '') return;
    const s = document.createElement('span');
    s.className = 'word' + (part.a ? ' word--accent' : '');
    s.textContent = w; head.appendChild(s);
    if (w.trim() !== '') words.push(s);
  }));
  const N = words.length;
  const render = (p) => {
    words.forEach((el, i) => {
      const o = clamp((p - (i / N) * 0.7) / 0.14);
      el.style.opacity = (0.12 + o * 0.88).toFixed(3);
      el.style.filter = `blur(${((1 - o) * 7).toFixed(2)}px)`;
      el.style.transform = `translateY(${((1 - o) * 16).toFixed(2)}px)`;
    });
  };
  render(0);
  if (reduce) { render(1); return; }
  ScrollTrigger.create({
    trigger: '#impact', start: 'top top', end: () => '+=' + (innerHeight * 1.4),
    pin: '.impact__pin', scrub: 1, onUpdate: (self) => render(self.progress),
  });
})();

/* ---------- ENHANCE: contact underline ---------- */
(function setupEnhance() {
  const buy = document.querySelector('.buy__title');
  if (buy) {
    const o = new IntersectionObserver((es) => {
      es.forEach(e => { if (e.isIntersecting) { e.target.classList.add('lit'); o.unobserve(e.target); } });
    }, { threshold: .5 });
    o.observe(buy);
  }
})();

/* ---------- NAV: marca a seção ativa ---------- */
(function setupNavActive() {
  const links = [...document.querySelectorAll('.nav-links a[href^="#"]')];
  if (!links.length) return;
  const map = new Map();
  links.forEach(a => { const el = document.querySelector(a.getAttribute('href')); if (el) map.set(el, a); });
  const obs = new IntersectionObserver((es) => {
    es.forEach(e => {
      if (!e.isIntersecting) return;
      links.forEach(l => l.classList.remove('active'));
      map.get(e.target)?.classList.add('active');
    });
  }, { rootMargin: '-45% 0px -50% 0px' });
  map.forEach((_, el) => obs.observe(el));
})();

/* ---------- CONTACT: submit demo (template ilustrativo) ---------- */
(function setupContactForm() {
  const form = document.getElementById('contactForm');
  const ok = document.getElementById('cfOk');
  if (!form) return;
  form.addEventListener('submit', (e) => {
    e.preventDefault();
    if (!form.reportValidity()) return;
    form.querySelectorAll('input, button').forEach(el => { el.disabled = true; el.style.opacity = '.5'; });
    if (ok) ok.hidden = false;
  });
})();

/* block scroll until preloader done */
document.body.style.overflow = 'hidden';
ScrollTrigger.refresh();
