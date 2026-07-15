"""Genesis Studio, servidor ENXUTO: só o criador do OS, sem o X do founder (nada de
painel de receita, voz, heartbeat, Guru). É o que o COMPRADOR roda.

Fluxo do comprador: clona o repo, abre no Claude Code (VS Code), fala "sobe o localhost".
O Claude Code roda isto e a cena do Genesis abre no navegador.

    python .genesis/servidor_genesis.py      ->  http://localhost:7799/

O cérebro da entrevista E da montagem é o CLAUDE CODE do comprador (na assinatura dele,
R$ 0, sem chave paga). O OS nasce na RAIZ do repo (base = cwd, ou a env GENESIS_BASE).
"""
import json
import os
import secrets
import sys
import webbrowser
from pathlib import Path
from threading import Lock, Thread, Timer

from flask import Flask, Response, jsonify, request, send_file

AQUI = Path(__file__).resolve().parent
PAGES = AQUI / "pages"  # os HTML das views moram em .genesis/pages/ (reorg 2026-07-10)
# genesis_motor viaja junto no template (mesma pasta); no layout de dev mora em ../nucleo
for cand in (AQUI, AQUI.parent / "nucleo"):
    if (cand / "genesis_motor.py").exists():
        sys.path.insert(0, str(cand))
        break
import genesis_motor  # noqa: E402
import painel_backend as pb  # noqa: E402

# O OS do comprador nasce na RAIZ do repo dele. Rodando `python .genesis/servidor_genesis.py`
# da raiz, cwd = raiz do repo. Dá pra forçar com a env GENESIS_BASE.
BASE = Path(os.environ.get("GENESIS_BASE", Path.cwd())).resolve()
PORTA = int(os.environ.get("GENESIS_PORTA", "7799"))

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


@app.get("/")
def home():
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


# --- APIs do painel: detalhe do agente, chat, layout do canvas -------------------

@app.get("/api/agente/<slug>")
def api_agente(slug):
    d = pb.agente_detalhe(BASE, slug)
    return jsonify(d) if d else (jsonify({"erro": "não encontrado"}), 404)


@app.post("/api/agente/<slug>/chat")
def api_agente_chat(slug):
    """Conversa com um agente do time (persona = .agent.md dele, na assinatura do comprador)."""
    corpo = request.get_json(silent=True) or {}
    return jsonify(pb.chat(BASE, slug, corpo.get("mensagens") or []))


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
    """Ativa uma ideia: dispara o build no repo do comprador; o card acompanha o build."""
    card = pb.task_obter(BASE, cid)
    if not card:
        return jsonify({"erro": "card não encontrado"}), 404
    tarefa = card["titulo"] + (("\n\n" + card["detalhe"]) if card.get("detalhe") else "")
    if card.get("agente"):
        tarefa = f"Use o agente {card['agente']} do time. " + tarefa
    pb.task_atualizar(BASE, cid, status="doing", ativo=True)
    return jsonify({"ok": True, "build": pb.build_iniciar(BASE, tarefa, origem=card.get("origem"))})


@app.get("/api/build")
def api_build():
    return jsonify(pb.build_status())


@app.post("/api/build/iniciar")
def api_build_iniciar():
    c = request.get_json(silent=True) or {}
    tarefa = (c.get("tarefa") or "").strip()
    if not tarefa:
        return jsonify({"erro": "tarefa vazia"}), 400
    return jsonify(pb.build_iniciar(BASE, tarefa))


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
    return jsonify(genesis_motor.passo(corpo.get("historico") or [], BASE,
                                       bool(corpo.get("montar_agora"))))


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
    print(f"Genesis Studio no ar: http://localhost:{PORTA}/")
    print(f"O seu OS vai nascer em: {BASE}")
    Timer(1.0, lambda: webbrowser.open(f"http://localhost:{PORTA}/")).start()
    app.run(host="127.0.0.1", port=PORTA, debug=False)
