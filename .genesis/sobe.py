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


def main():
    faltando = [m for m in ("flask",) if not _tem(m)]
    if faltando:
        print("Preparando o ambiente (uma vez só):", ", ".join(faltando))
        subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", *faltando], check=False)
    # o servidor enxuto herda o cwd (a raiz do repo) como base: o OS nasce aqui.
    subprocess.run([sys.executable, str(AQUI / "servidor_genesis.py")])


if __name__ == "__main__":
    main()
