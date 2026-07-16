"""'Sobe o localhost': o first-run do Genesis Studio.

O comprador clona o repo, abre no Claude Code (VS Code) e fala "sobe o localhost". O
Claude Code roda ISTO, que garante as dependências e sobe a cena do Genesis, sem o
comprador encostar em pip nem em terminal.

    python .genesis/sobe.py
"""
import subprocess
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent


def _tem(mod):
    try:
        __import__(mod)
        return True
    except ImportError:
        return False


# módulo importável -> pacote pip (nem sempre é o mesmo nome). O claude-agent-sdk é o
# motor do chat streaming com sessão; sem ele o chat cai no single-shot (funciona, mas
# sem streaming nem memória de conversa), então a falha de instalação NÃO trava o boot.
_DEPS = {"flask": "flask", "claude_agent_sdk": "claude-agent-sdk>=0.2,<0.3"}


def main():
    faltando = [pip for mod, pip in _DEPS.items() if not _tem(mod)]
    if faltando:
        print("Preparando o ambiente (uma vez só):", ", ".join(faltando))
        subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", *faltando], check=False)
    # o servidor enxuto herda o cwd (a raiz do repo) como base: o OS nasce aqui.
    subprocess.run([sys.executable, str(AQUI / "servidor_genesis.py")])


if __name__ == "__main__":
    main()
