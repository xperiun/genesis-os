"""PostToolUse hook do Xperiun OS: grava o pulso do time em `.genesis-atividade.jsonl`.

Cada vez que o comprador delega pra um subagente (ferramenta Task), registra QUEM agiu
(o slug do agente) e O QUÊ (a descrição da tarefa). É o que faz o painel do OS mostrar o
time VIVO de verdade, não teatro: todo ponto do pulso aponta pra uma delegação que
aconteceu mesmo.

Materializado por `genesis_motor.instalar()` via `.claude/settings.json`. Roda com cwd =
raiz do repo do comprador. NUNCA falha (um hook não pode travar o Claude Code): qualquer
erro sai silencioso, sempre com exit 0.
"""
import json
import os
import sys
import time


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return
    if payload.get("tool_name") != "Task":
        return  # só delegação a subagente é pulso real; o resto é ruído
    ti = payload.get("tool_input") or {}
    agente = str(ti.get("subagent_type") or "").strip()
    if not agente:
        return
    acao = str(ti.get("description") or "trabalhando").strip()[:120]
    base = os.environ.get("CLAUDE_PROJECT_DIR") or payload.get("cwd") or os.getcwd()
    linha = json.dumps({"ts": time.time(), "agente": agente, "acao": acao},
                       ensure_ascii=False)
    try:
        f = os.path.join(base, ".genesis-atividade.jsonl")
        linhas = []
        if os.path.exists(f):
            with open(f, encoding="utf-8", errors="ignore") as fh:
                linhas = fh.read().splitlines()[-199:]  # mantém o arquivo enxuto
        linhas.append(linha)
        with open(f, "w", encoding="utf-8") as fh:
            fh.write("\n".join(linhas) + "\n")
    except Exception:
        return


if __name__ == "__main__":
    main()
