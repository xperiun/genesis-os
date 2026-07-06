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
# genesis_motor viaja junto no template (mesma pasta); no layout de dev mora em ../nucleo
for cand in (AQUI, AQUI.parent / "nucleo"):
    if (cand / "genesis_motor.py").exists():
        sys.path.insert(0, str(cand))
        break
import genesis_motor  # noqa: E402

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
    return send_file(AQUI / "genesis.html")


@app.get("/pronto")
def pronto():
    return send_file(AQUI / "pronto.html")


@app.get("/painel")
def painel():
    """A superfície VISUALIZAR: o OS do comprador como agência viva (time real + pulso)."""
    return send_file(AQUI / "painel.html")


@app.get("/api/painel")
def api_painel():
    return jsonify(genesis_motor.painel_dados(BASE))


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
            with _lock:
                _estado.update({"status": "pronto", "caminho": str(BASE)})
        except Exception as e:
            with _lock:
                _estado.update({"status": "erro", "erro": str(e)[:200]})

    Thread(target=rodar, daemon=True).start()
    return jsonify({"ok": True, "status": "gerando"})


@app.get("/api/genesis/status")
def status():
    with _lock:
        return jsonify(dict(_estado))


if __name__ == "__main__":
    print(f"Genesis Studio no ar: http://localhost:{PORTA}/")
    print(f"O seu OS vai nascer em: {BASE}")
    Timer(1.0, lambda: webbrowser.open(f"http://localhost:{PORTA}/")).start()
    app.run(host="127.0.0.1", port=PORTA, debug=False)
