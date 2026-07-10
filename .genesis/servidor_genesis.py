"""Genesis Studio, servidor ENXUTO: só o criador do OS, sem o X do founder (nada de
painel de receita, voz, heartbeat, Guru). É o que o COMPRADOR roda.

Fluxo do comprador: clona o repo, abre no Claude Code (VS Code), fala "sobe o localhost".
O Claude Code roda isto e a cena do Genesis abre no navegador.

    python .genesis/servidor_genesis.py      ->  http://localhost:7799/

O cérebro da entrevista E da montagem é o CLAUDE CODE do comprador (na assinatura dele,
R$ 0, sem chave paga). O OS nasce na RAIZ do repo (base = cwd, ou a env GENESIS_BASE).
"""
import os
import sys
import webbrowser
from pathlib import Path
from threading import Lock, Thread, Timer

from flask import Flask, jsonify, request, send_file

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


@app.before_request
def _guarda_host():
    # bind em 127.0.0.1 não protege contra DNS rebinding: só aceitamos Host localhost
    if (request.host or "").lower() not in _HOSTS_OK:
        return "host não permitido", 403


@app.get("/")
def home():
    return send_file(PAGES / "genesis.html")


@app.get("/pronto")
def pronto():
    return send_file(PAGES / "pronto.html")


@app.get("/painel")
def painel():
    """A superfície VISUALIZAR: o OS do comprador como agência viva (time real + pulso)."""
    return send_file(PAGES / "painel.html")


@app.get("/api/painel")
def api_painel():
    return jsonify(genesis_motor.painel_dados(BASE))


# --- Views do shell (cada uma é um HTML self-contained num iframe) ---------------

@app.get("/dashboard")
def v_dashboard():
    return send_file(PAGES / "dashboard.html")


@app.get("/agentes")
def v_agentes():
    return send_file(PAGES / "agentes.html")


@app.get("/tasks")
def v_tasks():
    return send_file(PAGES / "tasks.html")


@app.get("/contextos")
def v_contextos():
    return send_file(PAGES / "contextos.html")


@app.get("/skills")
def v_skills():
    return send_file(PAGES / "skills.html")


@app.get("/integracoes")
def v_integracoes():
    return send_file(PAGES / "integracoes.html")


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
    return jsonify(genesis_motor.passo(corpo.get("historico") or []))


@app.post("/api/genesis/instalar")
def instalar():
    """Dispara a montagem em background (a geração leva minutos). O OS nasce em BASE."""
    corpo = request.get_json(silent=True) or {}
    reco = corpo.get("recomendacao") or {}
    if not isinstance(reco, dict) or not (reco.get("agentes") or reco.get("entendi")):
        return jsonify({"ok": False, "erro": "recomendação vazia"}), 400
    with _lock:
        if _estado["status"] == "gerando":
            return jsonify({"ok": True, "status": "gerando"})
        _estado.update({"status": "gerando", "caminho": None, "erro": None})

    def rodar():
        try:
            genesis_motor.instalar(reco, BASE)
            # conta o time REAL no disco (o que de fato saiu), pra o finale mostrar ESSE
            # número, nunca o do modelo (que pode divergir se a geração cortar algum slug).
            n_ag = len(list((BASE / ".claude" / "agents").glob("*.md")))
            n_sk = len([x for x in (BASE / ".claude" / "skills").glob("*") if x.is_dir()])
            with _lock:
                _estado.update({"status": "pronto", "caminho": str(BASE),
                                "agentes": n_ag, "skills": n_sk})
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
