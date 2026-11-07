"""Genesis Studio, servidor ENXUTO: só o criador do OS, sem o X do founder (nada de
painel de receita, voz, heartbeat, Guru). É o que o COMPRADOR roda.

Fluxo do comprador: clona o repo, abre no Claude Code (VS Code), fala "sobe o localhost".
O Claude Code roda isto e a cena do Genesis abre no navegador.

    python .genesis/servidor_genesis.py      ->  http://localhost:7799/

O cérebro da entrevista E da montagem é o CLAUDE CODE do comprador (na assinatura dele,
R$ 0, sem chave paga). O OS nasce na RAIZ do repo (base = cwd, ou a env GENESIS_BASE).
"""
import base64
import json
import os
import queue
import re
import secrets
import sys
import time
import webbrowser
from pathlib import Path
from threading import Lock, Thread, Timer

from flask import Flask, Response, jsonify, redirect, request, send_file

AQUI = Path(__file__).resolve().parent
PAGES = AQUI / "pages"  # os HTML das views moram em .genesis/pages/ (reorg 2026-07-10)
# genesis_motor viaja junto no template (mesma pasta); no layout de dev mora em ../nucleo
for cand in (AQUI, AQUI.parent / "nucleo"):
    if (cand / "genesis_motor.py").exists():
        sys.path.insert(0, str(cand))
        break
# O OS do comprador nasce na RAIZ do repo dele. Rodando `python .genesis/servidor_genesis.py`
# da raiz, cwd = raiz do repo. Dá pra forçar com a env GENESIS_BASE.
BASE = Path(os.environ.get("GENESIS_BASE", Path.cwd())).resolve()
PORTA = int(os.environ.get("GENESIS_PORTA", "7799"))
# a voz lê o .env da RAIZ do repo do comprador: fixa a base ANTES do import do pacote jarvis
os.environ.setdefault("GENESIS_BASE", str(BASE))

import chat_sdk  # noqa: E402
import genesis_motor  # noqa: E402
import painel_backend as pb  # noqa: E402
# O JARVIS (a voz) é OPCIONAL por ausência do módulo: o template pago leva `.genesis/jarvis/`
# e `pages/jarvis.html`; o repo público (a isca gratuita) sai sem os dois (publish.py
# --sem-jarvis), e aí as rotas /jarvis e /api/jarvis/* simplesmente não nascem. Nada de
# flag pra lembrar: o servidor olha o disco.
try:
    from jarvis import fillers as jarvis_fillers  # noqa: E402
    from jarvis import mouth as jarvis_mouth  # noqa: E402
    JARVIS = (PAGES / "jarvis.html").exists()
except ImportError:
    jarvis_fillers = jarvis_mouth = None
    JARVIS = False
HOME_PAINEL = "/painel#jarvis" if JARVIS else "/painel"   # a porta de entrada do OS montado

app = Flask("genesis")
_estado = {"status": "idle", "caminho": None, "erro": None}
_lock = Lock()
_HOSTS_OK = {f"localhost:{PORTA}", f"127.0.0.1:{PORTA}", f"[::1]:{PORTA}"}

# Token anti-CSRF, sorteado por processo. O bind em loopback e o guard de Host não param
# CSRF: uma página maliciosa que o comprador abra manda POST pra localhost:7799 com o Host
# certinho, e endpoints daqui escrevem arquivo e disparam build com acceptEdits no repo dele.
# O token fecha isso por dois lados: (1) header custom força preflight, que falha sem CORS;
# (2) o token viaja EMBUTIDO no HTML da página (ver _pagina), e outra origem não consegue LER
# o corpo de uma página nossa (sem CORS), então o atacante nunca o obtém.
_TOKEN = secrets.token_urlsafe(24)
_MUTA = {"POST", "PUT", "DELETE", "PATCH"}


@app.before_request
def _guarda():
    # bind em 127.0.0.1 não protege contra DNS rebinding: só aceitamos Host localhost
    if (request.host or "").lower() not in _HOSTS_OK:
        return "host não permitido", 403
    # tudo que muta estado exige o token. GET fica livre (a resposta é opaca cross-origin).
    if request.method in _MUTA and request.headers.get("X-Genesis") != _TOKEN:
        return jsonify({"erro": "token inválido, recarregue a página"}), 403


# O token é injetado no HTML no serve, e o shim embrulha o `fetch` pra carimbar o header
# sozinho. É o mecanismo INTEIRO num lugar só, e a razão é dura: exigir que cada página se
# lembre de mandar o header é um contrato que o autor da próxima página quebra calado (foi o
# que aconteceu: o guard entrou, só a cena foi adaptada, e tasks/agentes/contextos/skills
# passaram a levar 403 em TODA ação, mudas, porque os fetch() delas estão em catch vazio).
# Com o shim, `fetch('/api/tasks',{method:'POST'})` cru já sai autenticado e página nova
# nasce coberta. Só carimba same-origin: o token nunca vaza pra host de fora.
_SHIM = """<script>
(function(){
  var T=__TOKEN__, MUTA={POST:1,PUT:1,DELETE:1,PATCH:1}, f=window.fetch;
  window.fetch=function(u,o){
    o=o||{};
    var alvo=(typeof u==='string'||u instanceof URL)?String(u):(u&&u.url)||'';
    var mesma=false;
    try{ mesma=new URL(alvo,location.href).origin===location.origin; }catch(e){}
    if(MUTA[String(o.method||'GET').toUpperCase()]&&mesma){
      var h=new Headers(o.headers||(u&&u.headers)||{}); h.set('X-Genesis',T);
      o=Object.assign({},o,{headers:h});
    }
    return f.call(this,u,o);
  };
})();
</script>"""


def _pagina(nome):
    """Serve uma página com o token anti-CSRF embutido (ver _SHIM). Injeta logo depois do
    <head> pra o shim existir antes de qualquer script da página poder chamar fetch.

    Embutir em vez de servir por um GET /token evita duas coisas: a corrida de boot (a página
    podia postar antes do token chegar) e um endpoint a mais exposto pra outra origem."""
    html = (PAGES / nome).read_text(encoding="utf-8")
    if "<head>" not in html:   # invariante: sem <head> o shim não entra e a página quebraria
        raise RuntimeError(f"{nome} não tem <head>: o shim do token não tem onde entrar")
    shim = _SHIM.replace("__TOKEN__", json.dumps(_TOKEN))
    return Response(html.replace("<head>", "<head>" + shim, 1), mimetype="text/html")


def _os_montado():
    """True se o OS já foi montado (tem agentes em .claude/agents/). É o que decide se o `/`
    manda pra cena (entrevista) ou direto pro painel: quem já montou não quer re-entrevistar."""
    return any((BASE / ".claude" / "agents").glob("*.md"))


@app.get("/")
def home():
    # OS montado -> painel direto (reabrir o localhost não pode cair na entrevista de novo).
    # Ainda não montado -> a cena. Pra FORÇAR a cena num OS já montado (remontar), use /montar.
    # A porta de entrada do OS montado é /painel#jarvis: o JARVIS com o shell em volta
    # (sidebar, nav, as outras views a um clique). O /jarvis cru é a página NUA, que existe
    # só pra ser o src do iframe e o "abrir em tela cheia". Não se entra por ele.
    if _os_montado():
        return redirect(HOME_PAINEL, code=302)
    return _pagina("genesis.html")


@app.get("/montar")
def montar():
    """A cena (entrevista/reveal/montagem) SEMPRE, mesmo com OS já montado. É por aqui que o
    /setup entra, pra remontar não ser sequestrado pelo redirect do `/`."""
    return _pagina("genesis.html")


@app.get("/pronto")
def pronto():
    return _pagina("pronto.html")


@app.get("/painel")
def painel():
    """A superfície VISUALIZAR: o OS do comprador como agência viva (time real + pulso)."""
    return _pagina("painel.html")


@app.get("/api/painel")
def api_painel():
    return jsonify(genesis_motor.painel_dados(BASE))


# --- Views do shell (cada uma é um HTML self-contained num iframe) ---------------

@app.get("/dashboard")
def v_dashboard():
    return _pagina("dashboard.html")


@app.get("/agentes")
def v_agentes():
    return _pagina("agentes.html")


@app.get("/tasks")
def v_tasks():
    return _pagina("tasks.html")


@app.get("/contextos")
def v_contextos():
    return _pagina("contextos.html")


@app.get("/skills")
def v_skills():
    return _pagina("skills.html")


@app.get("/integracoes")
def v_integracoes():
    return _pagina("integracoes.html")


# --- JARVIS: a superfície de VOZ (o dono fala, o OS responde falando) -------------
# A view é a home do painel. Ela OUVE no navegador (Web Speech, grátis e local) e FALA pelo
# ElevenLabs (o seam em jarvis/mouth.py) com a voz do próprio navegador como fuga. O
# cérebro é o mesmo do chat de agente (SDK na assinatura do comprador, leitura read-only do
# repo), com persona própria: JARVIS não é um especialista do time, é a porta de voz pro
# OS inteiro, e responde CURTO porque a resposta vai ser LIDA EM VOZ ALTA.
# Este servidor NÃO sabe o que é ElevenLabs: ele pede mp3 ao mouth e repassa.

_JARVIS_SLUG = "__jarvis__"   # sessão própria no chat_sdk; não é um agente do time

_JARVIS_PERSONA_BASE = """=== SUA PERSONA (assuma isto por completo) ===
Você é o JARVIS deste OS: a interface de VOZ do dono. Não é um especialista do time dele,
é a porta de entrada falada pro OS inteiro (contexto, produção, o que o time já montou).

Como você fala (isto é lei, a sua resposta vai ser LIDA EM VOZ ALTA por um sintetizador):
- CURTO. Duas a quatro frases na maioria das vezes. Se a resposta é um número, comece por
  ele. Nunca despeje lista longa: fale o essencial e ofereça o resto ("quer o detalhe?").
- A PRIMEIRA FRASE tem no máximo doze palavras. Frase curta fecha antes, a voz entra antes.
- Texto corrido, sem markdown: nada de asterisco, hashtag, bullet, tabela ou emoji. Nada
  disso soa em voz alta, só vira ruído.
- Número falado por extenso quando ajuda ("um vírgula dois milhão"), sem sigla críptica.
- Português do Brasil, direto e caloroso, sem corporativês, sem travessão em prosa, sem
  abertura de chatbot ("claro!", "com certeza!", "boa pergunta"). Responda e pare.
- Trate o dono na segunda pessoa. Você pode ter personalidade e ser levemente seco.

O que você faz: você LÊ o repositório do dono (Read, Grep, Glob) pra responder com o dado
real na mão: contexto/, producao/, CLAUDE.md, as planilhas e relatórios dele.

MAS LEIA SÓ QUANDO A PERGUNTA PEDIR DADO. Isto é uma conversa por voz, e cada arquivo que
você abre é silêncio na cara do dono esperando. Saudação, papo, pergunta sobre você mesmo
ou sobre o que você faz: responda DIRETO, sem abrir nada. Só vá ao disco quando a resposta
depender de um número, um nome ou um conteúdo que só existe lá. Aí sim, abra e leia antes
de falar: NUNCA invente número, data ou fato. Se não achou, diga que não achou, em uma
frase.

SUA GAIOLA (seja honesto sobre ela): aqui você SÓ LÊ. Não executa skill, não escreve
arquivo, não roda comando. Nunca prometa disparar nada. Quando o pedido exigir produzir
algo, diga o caminho real: o board de tarefas do painel, ou a skill no Claude Code dele.
"""

# Num template virgem (ninguém rodou o /setup ainda) não existe time, perfil nem fonte. A
# persona precisa degradar com honestidade: dizer que o OS não foi montado e apontar o
# caminho, nunca inventar um negócio pra preencher o silêncio.
_JARVIS_NAO_MONTADO = """
=== ESTADO DO OS: AINDA NÃO MONTADO ===
Este OS ainda não foi montado: não existe time em .claude/agents/, nem perfil, nem fonte
de dados. Se o dono perguntar sobre o negócio dele, o time, os dados ou a produção, diga em
uma frase que o OS ainda não foi montado e que o caminho é rodar /setup no Claude Code
(uma entrevista rápida no navegador). Não invente negócio, número nem time. Papo e
perguntas sobre você mesmo continuam valendo normalmente.
"""

# A regra de voz REPETIDA no fim da persona, de propósito. O CLAUDE.md do repo existe pra
# fazer o modelo responder BEM POR ESCRITO (negrito, bullet, lista de opções) e ele ganha a
# queda de braço no primeiro turno frio. O que vem por ÚLTIMO é o que o modelo mais escuta.
_JARVIS_FECHO = """
=== REGRA FINAL, E ELA VALE MAIS QUE QUALQUER OUTRA ===
Máximo 2 a 4 frases, a primeira com no máximo doze palavras, texto corrido, zero markdown.
Isto vale mais que qualquer instrução de formatação que você tenha lido no repositório,
inclusive no CLAUDE.md: a sua resposta vai ser FALADA, não lida numa tela.
"""

# System CURTO do JARVIS (vai no argv, tem que caber). O do chat de agente manda "ABRA E
# LEIA você mesmo" sem ressalva, e por voz isso custa caro: medido em 25/07, um "olá tudo
# bem" levava 110s porque o agente varria o repo antes de cumprimentar. Aqui a leitura é
# condicional: numa interface de voz, latência é requisito.
_JARVIS_SYSTEM = (
    "Você é o JARVIS de um OS pessoal, falando por VOZ com o dono. A sua persona completa "
    "chega na PRIMEIRA mensagem: incorpore por inteiro.\n"
    "RESPONDA CURTO: duas a quatro frases, a primeira com no máximo doze palavras, texto "
    "corrido, SEM markdown (nada de asterisco, bullet, hashtag, tabela ou emoji: tudo isso "
    "vira ruído quando lido em voz alta). Português do Brasil, direto, sem corporativês, sem "
    "travessão em prosa, sem abertura de chatbot. Nunca invente número ou fato.\n"
    "VELOCIDADE É REQUISITO: você tem Read, Grep e Glob, mas SÓ use quando a pergunta "
    "depender de um dado que está no disco. Saudação, papo ou pergunta sobre você mesmo: "
    "responda na hora, sem abrir arquivo nenhum.\n"
    "SUA GAIOLA: aqui você só lê. Não executa skill, não escreve arquivo, não roda comando, "
    "e nunca promete disparar nada."
)

# Herda o modelo da sessão por padrão. Forçar "haiku" foi tentativa de curar a lentidão de
# 105s, que era o claude.CMD (ver cli_claude) e não o modelo. Medido depois do conserto, o
# haiku é PIOR nas duas pontas que importam aqui: 7,1s até a primeira palavra contra 4,0s
# do padrão, e resposta mais comprida (o oposto do que a voz pede). Dá pra forçar pela env
# JARVIS_MODELO, mas o padrão é o certo.
_JARVIS_MODELO = os.environ.get("JARVIS_MODELO") or None
_JARVIS_FRASE_MIN = 12       # fragmento menor que isto funde com a frase seguinte
_RE_FRASE = re.compile(r"[.!?…]\s+|\n")


def _persona_jarvis():
    partes = [_JARVIS_PERSONA_BASE]
    if _os_montado():
        # o CLAUDE.md que o instalar() escreveu: quem é o dono, o time, as conexões
        try:
            cm = (BASE / "CLAUDE.md").read_text(encoding="utf-8", errors="ignore")[:5000]
            if cm.strip():
                partes.append("\n=== O CLAUDE.md DO OS (o cérebro escrito na montagem) ===\n" + cm + "\n")
        except OSError:
            pass
        kb = pb._knowledge(BASE)
        if kb:
            partes.append("\n=== CONTEXTO DO DONO DO OS (quem ele é, o negócio, a fonte de dados) ===\n" + kb + "\n")
    else:
        partes.append(_JARVIS_NAO_MONTADO)
    partes.append(_JARVIS_FECHO)
    return "".join(partes)


def _aquecer_jarvis():
    """Pré-aquecimento dos dois órgãos, sem bloquear o serve: o cérebro (sessão do SDK) e a
    boca (cache de acenos). Falhar aqui é inofensivo: a fala cria a sessão normalmente, e
    sem cache o aceno sai pela voz do navegador."""
    chat_sdk.aquecer(_JARVIS_SLUG, BASE, _JARVIS_SYSTEM, _JARVIS_MODELO)

    def preparar():
        try:
            jarvis_fillers.preparar()
        except Exception:   # noqa: BLE001 (ElevenLabs fora: o aceno cai na fuga)
            pass
    Thread(target=preparar, daemon=True, name="jarvis-fillers").start()


def _registrar_jarvis():
    """As rotas da voz, registradas só quando o módulo existe (ver JARVIS acima)."""
    @app.get("/jarvis")
    def v_jarvis():
        """Serve a view E JÁ SOBE a sessão: quem abriu o JARVIS vai falar em segundos, e é
        melhor pagar o boot agora, enquanto ele ainda está lendo a tela, do que na primeira
        fala (pré-aquecimento paga cerca de 70% da primeira fala, medido)."""
        _aquecer_jarvis()
        return _pagina("jarvis.html")


    @app.post("/api/jarvis/chat")
    def api_jarvis_chat():
        """NDJSON com DOIS canais, e a página não cruza os dois (senão sai tudo dobrado):
            {"tipo":"texto","delta":"..."}                   -> só pra TELA
            {"tipo":"fala","texto":"...","audio_b64":"..."}  -> só pra FALAR (b64 vazio = fuga)
            {"tipo":"fim","primeiro_texto_ms","primeiro_audio_ms","total_ms","custo_voz_usd"}
        O corte de frases mora AQUI (é onde está a chave): frase fechada é a única unidade que
        dá pra sintetizar, e a síntese roda num worker SERIAL (uma fila, uma thread), de
        propósito: em paralelo os clipes voltam fora de ordem, e áudio fora de ordem é o pior
        defeito possível numa resposta falada. É o serial também que permite passar a frase
        anterior como previous_text."""
        corpo = request.get_json(silent=True) or {}
        mensagem = (corpo.get("mensagem") or "").strip()[:8000]
        if not mensagem:
            return jsonify({"erro": "mensagem vazia"}), 400
        novo = bool(corpo.get("novo"))
        persona = _persona_jarvis()

        fila = queue.Queue()          # o que sai pro cliente
        frases = queue.Queue()        # o que vai pro worker de síntese
        t0 = time.perf_counter()
        marcas = {"texto": None, "audio": None, "n": 0}
        buf = {"s": ""}

        def ms():
            return int((time.perf_counter() - t0) * 1000)

        def emitir(delta):
            if marcas["texto"] is None:
                marcas["texto"] = ms()
            marcas["n"] += 1
            fila.put(("texto", delta))
            buf["s"] += delta
            _cortar()

        def _cortar(final=False):
            s = buf["s"]
            while True:
                m = _RE_FRASE.search(s)
                if not m:
                    break
                frase, s = s[:m.end()].strip(), s[m.end():]
                if frase and len(frase) < _JARVIS_FRASE_MIN and not final:
                    s = frase + " " + s      # curta demais pra virar clipe: funde com a próxima
                    break
                if frase:
                    frases.put(frase)
            if final and s.strip():
                frases.put(s.strip())
                s = ""
            buf["s"] = s

        def sintetizar():
            anterior = None
            while True:
                frase = frases.get()
                if frase is None:
                    return
                audio = jarvis_mouth.sintetizar_mp3(frase, anterior)
                anterior = frase
                if marcas["audio"] is None:
                    marcas["audio"] = ms()
                fila.put(("fala", {"texto": frase,
                                   "audio_b64": base64.b64encode(audio).decode("ascii") if audio else ""}))

        worker = Thread(target=sintetizar, daemon=True, name="jarvis-tts")
        worker.start()

        def rodar():
            try:
                if chat_sdk.disponivel():
                    chat_sdk.responder(_JARVIS_SLUG, persona, mensagem, str(BASE),
                                       novo=novo, ao_texto=emitir,
                                       sistema=_JARVIS_SYSTEM, modelo=_JARVIS_MODELO, teto=120)
                else:
                    raise RuntimeError("SDK indisponível")
            except Exception:
                if marcas["n"] == 0:   # nada saiu ainda: o single-shot assume sem duplicar
                    txt = genesis_motor._claude_cli(
                        persona + "\n\n=== PERGUNTA DO DONO (responda em voz, curto) ===\n" + mensagem,
                        "Você é o JARVIS de um OS pessoal, respondendo por VOZ: curto, texto "
                        "corrido, sem markdown, português do Brasil. Nunca invente dado.",
                        tools="Read Grep Glob", cwd=BASE)
                    if txt:
                        emitir(genesis_motor._sem_traves(txt.strip()))
                    else:
                        fila.put(("erro", "não consegui pensar agora, tenta de novo"))
            finally:
                _cortar(final=True)        # o rabo do buffer (sem pontuação final) também fala
                frases.put(None)           # drena o worker e SÓ ENTÃO emite o fim
                worker.join(timeout=90)
                fila.put(("fim", {"primeiro_texto_ms": marcas["texto"],
                                  "primeiro_audio_ms": marcas["audio"],
                                  "total_ms": ms(),
                                  "custo_voz_usd": jarvis_mouth.custo_usd()}))

        Thread(target=rodar, daemon=True).start()

        def gen():
            while True:
                tipo, d = fila.get()
                if tipo == "fim":
                    yield (json.dumps({"tipo": "fim", **(d or {})}) + "\n").encode("utf-8")
                    return
                if tipo == "erro":
                    yield (json.dumps({"tipo": "erro", "erro": d}, ensure_ascii=False) + "\n").encode("utf-8")
                    continue
                if tipo == "fala":
                    yield (json.dumps({"tipo": "fala", **d}, ensure_ascii=False) + "\n").encode("utf-8")
                    continue
                yield (json.dumps({"tipo": "texto", "delta": d}, ensure_ascii=False) + "\n").encode("utf-8")

        return Response(gen(), mimetype="application/x-ndjson", direct_passthrough=True)


    @app.get("/api/jarvis/filler")
    def api_jarvis_filler():
        """Um aceno do cache (mp3 em disco, milissegundos). 204 sem cache: não é erro, é o
        sinal pra página falar o aceno ela mesma, pela voz do navegador."""
        r = jarvis_fillers.sortear(request.args.get("dica") or "neutro")
        if not r:
            return Response(status=204)
        frase, audio = r
        resp = Response(audio, mimetype="audio/mpeg")
        resp.headers["X-Jarvis-Frase"] = base64.b64encode(frase.encode("utf-8")).decode("ascii")
        resp.headers["Cache-Control"] = "no-store"
        return resp


    @app.post("/api/jarvis/falar")
    def api_jarvis_falar():
        """Testa a voz sem o pipeline inteiro. audio_b64 vazio é a fuga, não é erro."""
        corpo = request.get_json(silent=True) or {}
        texto = (corpo.get("texto") or "").strip()[:600]
        if not texto:
            return jsonify({"erro": "texto vazio"}), 400
        audio = jarvis_mouth.sintetizar_mp3(texto)
        return jsonify({"audio_b64": base64.b64encode(audio).decode("ascii") if audio else "",
                        "voz": jarvis_mouth.voz_atual(), "custo_usd": jarvis_mouth.custo_usd()})


    @app.get("/api/jarvis/estado")
    def api_jarvis_estado():
        """O diagnóstico num GET (e NUNCA a chave). A página o consulta pra MOSTRAR se está no
        ElevenLabs ou na fuga; a auditoria o usa como primeiro sinal de vida."""
        est = jarvis_mouth.estado()
        est["acenos"] = jarvis_fillers.contagem()
        est["sessao_quente"] = chat_sdk.sessao_viva(_JARVIS_SLUG)
        est["cerebro"] = "sdk" if chat_sdk.disponivel() else "single-shot"
        est["os_montado"] = _os_montado()
        return jsonify(est)


if JARVIS:
    _registrar_jarvis()


# --- APIs do painel: detalhe do agente, chat, layout do canvas -------------------

@app.get("/api/agente/<slug>")
def api_agente(slug):
    d = pb.agente_detalhe(BASE, slug)
    return jsonify(d) if d else (jsonify({"erro": "não encontrado"}), 404)


@app.post("/api/agente/<slug>/chat")
def api_agente_chat(slug):
    """Conversa com um agente do time, em STREAMING NDJSON (uma linha JSON por evento:
    {tipo:'texto',delta} ... {tipo:'fim'}), na assinatura do comprador.

    Caminho principal: claude-agent-sdk com sessão QUENTE por agente (o agente lembra do
    papo; `novo:true` na 1ª mensagem da conversa recicla). Fallback: o single-shot
    `pb.chat` (claude -p por turno, reenvia o histórico), que emite o texto inteiro de uma
    vez, só se NADA foi streamado ainda (pra não duplicar). Mesmo contrato do agentic-os."""
    corpo = request.get_json(silent=True) or {}
    mensagens = corpo.get("mensagens") or []
    novo = bool(corpo.get("novo"))
    mensagem = (corpo.get("mensagem") or "").strip()[:8000]
    if not mensagem:   # compat: extrai a última fala do comprador do histórico
        for m in reversed(mensagens):
            if m.get("role") in ("voce", "user"):
                mensagem = str(m.get("texto") or m.get("content") or "").strip()[:8000]
                break
    if not mensagem:
        return jsonify({"erro": "mensagem vazia"}), 400
    det, persona = pb.persona_chat(BASE, slug)
    if not det:
        return jsonify({"erro": "agente não encontrado"}), 404

    fila = queue.Queue()
    emitido = {"n": 0}

    def emitir(delta):
        emitido["n"] += 1
        fila.put(("texto", delta))

    def rodar():
        try:
            if chat_sdk.disponivel():
                chat_sdk.responder(slug, persona, mensagem, str(BASE),
                                   novo=novo, ao_texto=emitir)
            else:
                raise RuntimeError("SDK indisponível")
        except Exception:
            if emitido["n"] == 0:   # nada saiu ainda: o single-shot assume sem duplicar
                r = pb.chat(BASE, slug, mensagens or [{"role": "voce", "texto": mensagem}])
                if r.get("ok"):
                    emitir(r["resposta"])
                else:
                    fila.put(("erro", r.get("erro") or "não consegui responder agora"))
        finally:
            fila.put(("fim", None))

    Thread(target=rodar, daemon=True).start()

    def gen():
        # bytes, não str: com direct_passthrough o werkzeug exige bytes e um yield de
        # string mata o stream no primeiro evento ("applications must write bytes")
        while True:
            tipo, d = fila.get()
            if tipo == "fim":
                yield (json.dumps({"tipo": "fim"}) + "\n").encode("utf-8")
                return
            if tipo == "erro":
                yield (json.dumps({"tipo": "erro", "erro": d}, ensure_ascii=False) + "\n").encode("utf-8")
                continue
            yield (json.dumps({"tipo": "texto", "delta": d}, ensure_ascii=False) + "\n").encode("utf-8")

    return Response(gen(), mimetype="application/x-ndjson", direct_passthrough=True)


@app.get("/api/painel/layout")
def api_layout_get():
    return jsonify(pb.layout_ler(BASE))


@app.post("/api/painel/layout")
def api_layout_set():
    corpo = request.get_json(silent=True) or {}
    return jsonify({"ok": pb.layout_gravar(BASE, corpo.get("posicoes") or {})})


# --- Contexto (knowledge vault: ler/editar + puxar do site) ----------------------

@app.get("/api/contexto")
def api_contexto_listar():
    return jsonify({"arquivos": pb.contextos(BASE)})


@app.post("/api/contexto/puxar-site")
def api_puxar_site():
    """O comprador cola o link da empresa; o Claude Code dele lê o site e escreve o brief."""
    corpo = request.get_json(silent=True) or {}
    return jsonify(pb.puxar_site(BASE, corpo.get("url", "")))


@app.get("/api/contexto/<path:rel>")
def api_contexto_ler(rel):
    txt = pb.ler_contexto(BASE, rel)
    return jsonify({"rel": rel, "conteudo": txt}) if txt is not None else (jsonify({"erro": "não encontrado"}), 404)


@app.put("/api/contexto/<path:rel>")
def api_contexto_gravar(rel):
    corpo = request.get_json(silent=True) or {}
    return jsonify({"ok": pb.gravar_contexto(BASE, rel, corpo.get("conteudo", ""))})


# --- Skills (catálogo + editar SKILL.md) ----------------------------------------

@app.get("/api/skills")
def api_skills_listar():
    return jsonify({"skills": pb.skills(BASE)})


@app.get("/api/skill/<slug>")
def api_skill_ler(slug):
    txt = pb.ler_skill(BASE, slug)
    return jsonify({"slug": slug, "conteudo": txt}) if txt is not None else (jsonify({"erro": "não encontrado"}), 404)


@app.put("/api/skill/<slug>")
def api_skill_gravar(slug):
    corpo = request.get_json(silent=True) or {}
    return jsonify({"ok": pb.gravar_skill(BASE, slug, corpo.get("conteudo", ""))})


# --- Board de tasks + build ------------------------------------------------------

@app.get("/api/tasks")
def api_tasks_listar():
    return jsonify({"tasks": pb.tasks_listar(BASE)})


@app.post("/api/tasks")
def api_tasks_criar():
    c = request.get_json(silent=True) or {}
    cid = pb.task_registrar(BASE, c.get("titulo", ""), agente=c.get("agente", ""),
                            status=c.get("status", "backlog"), ativo=c.get("ativo", True),
                            detalhe=c.get("detalhe", ""), fonte=c.get("fonte", "painel"))
    return jsonify({"ok": bool(cid), "id": cid})


@app.post("/api/tasks/<cid>")
def api_tasks_atualizar(cid):
    c = request.get_json(silent=True) or {}
    campos = {k: c[k] for k in ("titulo", "status", "detalhe", "agente", "ativo") if k in c}
    t = pb.task_atualizar(BASE, cid, **campos)
    return jsonify({"ok": bool(t), "task": t}) if t else (jsonify({"erro": "não achei"}), 404)


@app.delete("/api/tasks/<cid>")
def api_tasks_remover(cid):
    return jsonify({"ok": pb.task_remover(BASE, cid)})


@app.post("/api/tasks/<cid>/ativar")
def api_tasks_ativar(cid):
    """Ativa uma ideia: dispara o build no repo do comprador; o card acompanha o build.
    O status só muda DEPOIS de o build aceitar: antes, uma recusa por concorrência
    ("já tem um build rodando") deixava o card preso em 'Fazendo' pra sempre."""
    card = pb.task_obter(BASE, cid)
    if not card:
        return jsonify({"erro": "card não encontrado"}), 404
    tarefa = card["titulo"] + (("\n\n" + card["detalhe"]) if card.get("detalhe") else "")
    if card.get("agente"):
        tarefa = f"Use o agente {card['agente']} do time. " + tarefa
    r = pb.build_iniciar(BASE, tarefa, origem=card.get("origem"),
                         agente=card.get("agente") or "")
    if not r.get("ok"):
        return jsonify({"ok": False, "erro": r.get("erro") or "o build não aceitou"})
    pb.task_atualizar(BASE, cid, status="doing", ativo=True, falhou=False)
    return jsonify({"ok": True, "build": r})


@app.get("/api/build")
def api_build():
    return jsonify(pb.build_status())


@app.post("/api/build/iniciar")
def api_build_iniciar():
    c = request.get_json(silent=True) or {}
    tarefa = (c.get("tarefa") or "").strip()
    if not tarefa:
        return jsonify({"erro": "tarefa vazia"}), 400
    # `contexto` = transcrição da conversa do chat (o build parte sabendo o que foi
    # combinado); `agente` = slug do agente do time (alimenta o pulso do painel)
    return jsonify(pb.build_iniciar(BASE, tarefa,
                                    contexto=(c.get("contexto") or "").strip(),
                                    agente=(c.get("agente") or "").strip()))


@app.post("/api/build/parar")
def api_build_parar():
    """Encerra o build em andamento (o botão '■ Encerrar' era fake: trocava o rótulo e não
    chamava nada, o único fim possível era o watchdog de 15min)."""
    return jsonify(pb.build_parar(BASE))


@app.post("/api/abrir")
def api_abrir():
    """Abre um arquivo/pasta do OS no sistema do comprador (botão 'abrir' do resultado)."""
    return jsonify(pb.abrir(BASE, (request.get_json(silent=True) or {}).get("path", "")))


@app.get("/api/integracoes")
def api_integracoes():
    return jsonify(pb.integracoes(BASE))


@app.get("/favicon.svg")
def favicon():
    f = AQUI / "favicon.svg"
    return send_file(f, mimetype="image/svg+xml") if f.exists() else ("", 404)


@app.post("/api/genesis/passo")
def passo():
    corpo = request.get_json(silent=True) or {}
    # BASE = repo do comprador: o X entrevista JÁ tendo lido o que ele conectou na cena de
    # abastecimento (contexto/referencia/), em vez de perguntar o que já está escrito.
    # `candidatos` = nomes já na fila do recrutamento (a cena acumula e devolve), a memória
    # que impede o modelo de re-sugerir o mesmo papel com nome diferente a cada turno.
    return jsonify(genesis_motor.passo(corpo.get("historico") or [], BASE,
                                       bool(corpo.get("montar_agora")),
                                       corpo.get("candidatos") or []))


# --- Abastecimento: o que o comprador conecta ANTES da entrevista --------------
# Três caminhos (soltar arquivo, colar o link do site, colar texto de outro assistente), um
# destino só: contexto/referencia/, que a entrevista e a montagem leem. É o que faz o time
# nascer sabendo do negócio, e é o passo que o produto chama de "conecte a sua realidade".

@app.get("/api/genesis/contexto")
def api_ctx_listar():
    return jsonify({"arquivos": pb.referencia_listar(BASE)})


@app.post("/api/genesis/contexto")
def api_ctx_gravar():
    c = request.get_json(silent=True) or {}
    r = pb.referencia_gravar(BASE, c.get("nome", ""), c.get("conteudo", ""))
    return jsonify(r) if r.get("ok") else (jsonify(r), 400)


@app.delete("/api/genesis/contexto/<path:rel>")
def api_ctx_remover(rel):
    return jsonify({"ok": pb.referencia_remover(BASE, rel)})


@app.post("/api/genesis/instalar")
def instalar():
    """Dispara a montagem em background (a geração leva minutos). O OS nasce em BASE."""
    corpo = request.get_json(silent=True) or {}
    reco = corpo.get("recomendacao") or {}
    if not isinstance(reco, dict) or not (reco.get("agentes") or reco.get("entendi")):
        return jsonify({"ok": False, "erro": "recomendação vazia"}), 400
    # o comprador escolheu o modelo no reveal (só aparece pra quem está em Opus). Allowlist:
    # isto vira argv do `claude -p`, então nada de string livre vinda do corpo do POST.
    modelo = corpo.get("modelo") if corpo.get("modelo") in ("sonnet", "opus", "haiku") else None
    with _lock:
        if _estado["status"] == "gerando":
            return jsonify({"ok": True, "status": "gerando"})
        _estado.update({"status": "gerando", "caminho": None, "erro": None})

    def rodar():
        try:
            r = genesis_motor.instalar(reco, BASE, modelo) or {}
            # conta o time REAL no disco (o que de fato saiu), pra o finale mostrar ESSE
            # número, nunca o do modelo (que pode divergir se a geração cortar algum slug).
            n_ag = len(list((BASE / ".claude" / "agents").glob("*.md")))
            n_sk = len([x for x in (BASE / ".claude" / "skills").glob("*") if x.is_dir()])
            # `sob_medida` viaja junto do contador de propósito: o contador conta ARQUIVO, e
            # esboço também é arquivo. Sem este par, o finale comemora os dois casos igual.
            with _lock:
                _estado.update({"status": "pronto", "caminho": str(BASE),
                                "agentes": n_ag, "skills": n_sk,
                                "sob_medida": bool(r.get("sob_medida", True)),
                                "aviso": r.get("aviso") or ""})
        except Exception as e:
            with _lock:
                _estado.update({"status": "erro", "erro": str(e)[:200]})

    Thread(target=rodar, daemon=True).start()
    return jsonify({"ok": True, "status": "gerando"})


@app.get("/api/genesis/status")
def status():
    with _lock:
        est = dict(_estado)
    est["log"] = genesis_motor.montagem_log()  # o que o Claude Code faz ao vivo, pro terminal
    return jsonify(est)


if __name__ == "__main__":
    # que rota o navegador abre no boot. Default `/` (a home decide cena vs painel pelo estado
    # do OS). O /setup força `/montar` (cena sempre) e o /painel força `/painel`, via sobe.py.
    # `off` = não abre navegador nenhum (a auditoria sobe um servidor de teste e o dono, que
    # está trabalhando, não pode ganhar uma aba perdida no meio da tela).
    abrir = os.environ.get("GENESIS_ABRIR", "/")
    if abrir.strip().lower() == "off":
        abrir = "/"                  # só não abre o navegador; o endereço impresso é o normal
    if not abrir.startswith("/"):
        abrir = "/" + abrir
    if abrir.rstrip("/") == "/painel":
        abrir = HOME_PAINEL          # com o JARVIS, a porta de entrada é ele com o shell em volta
    url = f"http://127.0.0.1:{PORTA}{HOME_PAINEL if _os_montado() and abrir == '/' else abrir}"
    print(f"Genesis Studio no ar: {url}")
    print(f"O seu OS vai nascer em: {BASE}")
    if os.environ.get("GENESIS_ABRIR", "").strip().lower() != "off":
        Timer(1.0, lambda: webbrowser.open(f"http://localhost:{PORTA}{abrir}")).start()
    app.run(host="127.0.0.1", port=PORTA, debug=False, threaded=True)
