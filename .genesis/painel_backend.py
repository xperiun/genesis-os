"""Backend das views do painel do OS do comprador (além do /api/painel, que já mora no
genesis_motor). Fase A: detalhe de um agente + chat com ele. Fases seguintes acrescentam
catálogo (contexto/skills) e board de tasks.

Tudo LOCAL, na máquina do comprador, na assinatura DELE (claude -p headless, R$ 0, sem
chave paga). Reusa o genesis_motor pros helpers (claude -p, ler frontmatter, slug). Guard
de path em toda leitura/escrita: nunca sai de dentro do repo do comprador."""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from pathlib import Path

import genesis_motor as gm


def abrir(base, rel):
    """Abre um arquivo/pasta do OS no app padrão do sistema (botão 'abrir' do resultado da
    task). Guard de path: só dentro do repo do comprador. Local: abre no VS Code/Explorer dele."""
    p = _dentro(Path(base), (rel or "").strip().lstrip("/\\"))
    if not p or not p.exists():
        return {"ok": False, "erro": "não encontrado"}
    try:
        if os.name == "nt":
            os.startfile(str(p))          # caminho já validado dentro do repo
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(p)])
        else:
            subprocess.Popen(["xdg-open", str(p)])
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "erro": str(e)[:120]}


# ---------- Agente: detalhe + chat ----------------------------------------------

def _agente_path(base, slug):
    """Resolve o .agent.md do slug, com guard de path (só dentro de .claude/agents)."""
    adir = (Path(base) / ".claude" / "agents").resolve()
    try:
        p = (adir / f"{gm._slug(slug)}.md").resolve()
        p.relative_to(adir)
    except (ValueError, OSError):
        return None
    return p if p.exists() else None


def agente_detalhe(base, slug):
    """Nome, descrição e corpo do .agent.md, pra a gaveta de detalhe/chat do canvas."""
    p = _agente_path(base, slug)
    if not p:
        return None
    txt = p.read_text(encoding="utf-8", errors="ignore")
    nome, desc = gm._ler_fm(p)
    m = gm._RE_FM.match(txt)
    corpo = m.group(2).strip() if m else txt
    return {"slug": p.stem, "nome": nome or p.stem, "descricao": desc, "corpo": corpo}


def _knowledge(base):
    """Contexto compartilhado do OS (o 'second brain'): perfil + fonte + o knowledge base
    que o comprador deixou em contexto/referencia/ (os docs reais do negócio dele). Todo
    agente responde sabendo quem é o comprador e do negócio, sem precisar abrir arquivo."""
    partes = []
    for rel in ("contexto/perfil.md", "contexto/fonte.md"):
        f = Path(base) / rel
        if f.exists():
            try:
                partes.append(f.read_text(encoding="utf-8", errors="ignore")[:4000])
            except OSError:
                pass
    ref = gm._ler_referencia(base)  # os docs do negócio (contexto/referencia/), o mesmo que a montagem usa
    if ref:
        partes.append("Documentos do negócio do comprador (contexto/referencia/), use como verdade:\n" + ref[:8000])
    return "\n\n".join(partes)


def chat(base, slug, mensagens):
    """Conversa com um agente do time: a persona é o corpo do .agent.md dele, mais o
    contexto do OS por cima (o comprador não precisa reexplicar quem é). Roda na assinatura
    do comprador (claude -p, R$ 0). Turno a turno (sem streaming, json single-shot). Devolve
    {ok, resposta} ou {ok:False, erro}."""
    det = agente_detalhe(base, slug)
    if not det:
        return {"ok": False, "erro": "agente não encontrado"}
    kb = _knowledge(base)
    # system CURTO no argv (o claude no Windows é um .cmd, ~8KB de limite de linha de comando):
    # a persona e o knowledge base, que podem ser grandes, vão no STDIN (o prompt), sem limite.
    system = (
        "Você é um especialista de um time de IA pessoal. Assuma POR COMPLETO a persona "
        "descrita no início da mensagem e responda como ELA: pela lente e método dela, "
        "direto, caloroso, brasileiro, sem corporativês. Português do Brasil com acentos, "
        "sem travessão em prosa. Útil e específico.\n"
        "Você TEM LEITURA do repositório do comprador (ferramentas Read/Grep/Glob): contexto/, "
        "producao/, CLAUDE.md, os arquivos do projeto dele. Quando ele pedir análise ou leitura "
        "de algo que está no repo (ex: 'analisa producao/...'), ABRA E LEIA você mesmo e responda "
        "com o dado real na mão; NUNCA peça pra ele colar o que já está no disco, e quando o pedido "
        "é direto pra você, FAÇA, não empurre pra outro. Você só NÃO ESCREVE arquivo aqui: pra "
        "produzir a peça/entregável final ele te aciona pelo build ('põe pra trabalhar'). Nunca "
        "invente número ou fato; se não achar nem lendo, diga que não achou."
    )
    linhas = []
    for m in (mensagens or []):
        quem = det["nome"] if m.get("role") == "agente" else "Comprador"
        txt = str(m.get("texto", "")).strip()
        if txt:
            linhas.append(f"{quem}: {txt}")
    if not linhas:
        return {"ok": False, "erro": "mensagem vazia"}
    prompt = (
        f"=== SUA PERSONA (assuma isto por completo, você É {det['nome']}) ===\n"
        f"{det['nome']}\n{det['corpo']}\n\n"
        + (f"=== CONTEXTO DO COMPRADOR (quem ele é, o negócio, a fonte de dados) ===\n{kb}\n\n" if kb else "")
        + "=== CONVERSA (responda a última fala do Comprador, como " + det["nome"] + ") ===\n"
        + "\n".join(linhas) + f"\n\n{det['nome']}:"
    )
    # tools de leitura + cwd no repo do aluno: o agente LÊ os arquivos do comprador (producao/,
    # contexto/) pra responder com dado real. Só leitura (Read/Grep/Glob); escrita é no build.
    texto = gm._claude_cli(prompt, system, tools="Read Grep Glob", cwd=base)
    if texto is None:
        return {"ok": False, "erro": "o Claude Code não respondeu. O comando 'claude' está no PATH?"}
    return {"ok": True, "resposta": gm._sem_canon(gm._sem_traves(texto.strip()))}


# ---------- Catálogo: contexto + skills (ler / editar) --------------------------

def _dentro(basedir, rel):
    """Resolve rel dentro de basedir com guard de path traversal. None se escapar."""
    try:
        p = (Path(basedir) / rel).resolve()
        p.relative_to(Path(basedir).resolve())
        return p
    except (ValueError, OSError):
        return None


# O contexto do OS são DUAS coisas, não só a pasta contexto/:
#  1) os mapas CLAUDE.md espalhados (do mapa raiz aos de sub-área) — o cérebro do OS
#  2) o vault contexto/ (perfil, fonte, referencia, etc.)
# Poda fronteira de OS ANINHADO: não desce em subpasta que tenha .claude/ próprio (é um
# subprojeto/produto à parte, cérebro dele, não o nosso). E .genesis/ (o motor) fica fora.
_IGNORAR = {".git", "node_modules", ".scratch", ".venv", "__pycache__", "_pages", ".genesis"}
_EXT_VAULT = (".md", ".csv", ".txt", ".xlsx")


def _item_ctx(base, f):
    return {"rel": f.relative_to(base).as_posix(), "nome": f.name,
            "pasta": (f.parent.relative_to(base).as_posix() if f.parent != base else ""),
            "kb": round(f.stat().st_size / 1024, 1), "editavel": f.suffix.lower() == ".md"}


def _mapas_claude(base):
    """Todo CLAUDE.md do repo, podando ruído (.git, node_modules...) e fronteiras de OS
    aninhado (subpasta com .claude/ própria = outro cérebro, não desce)."""
    achados = []
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames
                       if d not in _IGNORAR and not (Path(dirpath) / d / ".claude").is_dir()]
        if "CLAUDE.md" in filenames:
            achados.append(Path(dirpath) / "CLAUDE.md")
    return achados


def contextos(base):
    """Contexto navegável: os mapas CLAUDE.md do repo + o vault contexto/. Só .md editável."""
    base = Path(base)
    itens = [_item_ctx(base, f) for f in sorted(_mapas_claude(base))]
    cdir = base / "contexto"
    if cdir.is_dir():
        for f in sorted(cdir.rglob("*")):
            if f.is_file() and f.suffix.lower() in _EXT_VAULT and ".git" not in f.parts:
                itens.append(_item_ctx(base, f))
    return itens


def _permitido(rel_posix):
    """Listável/legível/gravável: um CLAUDE.md em qualquer lugar, ou algo em contexto/."""
    return rel_posix.rsplit("/", 1)[-1] == "CLAUDE.md" \
        or rel_posix == "contexto" or rel_posix.startswith("contexto/")


def _resolve_ctx(base, rel):
    rel = (rel or "").strip().lstrip("/\\")
    baseR = Path(base).resolve()
    try:
        alvo = (baseR / rel).resolve()
        relp = alvo.relative_to(baseR).as_posix()   # guard de path traversal
    except (ValueError, OSError):
        return None
    return alvo if _permitido(relp) else None


def ler_contexto(base, rel):
    f = _resolve_ctx(base, rel)
    if not (f and f.is_file()):
        return None
    if f.suffix.lower() == ".xlsx":
        return "(planilha binária, abrir no Excel. Aqui é só referência, não editável.)"
    try:
        return f.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None


def gravar_contexto(base, rel, conteudo):
    """Grava só .md permitido (CLAUDE.md do repo ou contexto/*.md). Escrita atômica."""
    f = _resolve_ctx(base, rel)
    if not f or f.suffix.lower() != ".md":
        return False
    try:
        f.parent.mkdir(parents=True, exist_ok=True)
        tmp = f.with_suffix(f.suffix + ".tmp")
        tmp.write_text(conteudo, encoding="utf-8")
        tmp.replace(f)
        return True
    except OSError:
        return False


def puxar_site(base, url):
    """O comprador cola o LINK da empresa dele; o Claude Code DELE lê o site (WebFetch) e
    escreve um brief do negócio em contexto/referencia/<dominio>.md, que a montagem e o chat
    passam a usar como knowledge base. Roda na assinatura dele (R$ 0). Devolve
    {ok, arquivo, titulo, resumo} ou {ok:False, erro}. Guard: só grava dentro de referencia."""
    url = (url or "").strip()
    if not re.match(r"^https?://", url, re.I):
        url = "https://" + url
    if not re.match(r"^https?://[\w.-]+\.\w", url, re.I):
        return {"ok": False, "erro": "link inválido"}
    exe = shutil.which("claude")
    if not exe:
        return {"ok": False, "erro": "o comando 'claude' não está no PATH"}
    prompt = (
        f"Leia o site {url} e as páginas-chave que ele linkar (sobre, produtos ou serviços, "
        "preços, casos, contato). Extraia um BRIEF do negócio, em português do Brasil, sem "
        "travessão em prosa: quem é a empresa, o que ela vende, para quem, o tom de voz, e os "
        "números e casos que aparecerem. Markdown conciso (600 a 1200 palavras). Comece com um "
        "título '# ' e o nome da empresa. Devolva SÓ o markdown, nada além, sem cercar em crase.")
    try:
        proc = subprocess.run(
            [exe, "-p", "--output-format", "json", "--allowedTools", "WebFetch WebSearch"],
            input=prompt, capture_output=True, text=True, encoding="utf-8", errors="ignore",
            timeout=240, cwd=tempfile.gettempdir())
    except Exception as e:
        return {"ok": False, "erro": "não consegui ler o site: " + str(e)[:80]}
    if proc.returncode != 0 or not (proc.stdout or "").strip():
        return {"ok": False, "erro": "o Claude Code não conseguiu ler o site (link certo? offline?)"}
    try:
        env = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {"ok": False, "erro": "resposta inesperada do Claude Code"}
    texto = (env.get("result") or "").strip()
    if env.get("is_error") or not texto:
        return {"ok": False, "erro": "o site não deu pra ler (bloqueio? conteúdo dinâmico?)"}
    texto = gm._sem_canon(gm._sem_traves(texto))
    dominio = re.sub(r"^https?://(www\.)?", "", url, flags=re.I).split("/")[0]
    slug = gm._slug(dominio) or "site"
    ref = Path(base) / "contexto" / "referencia"
    ref.mkdir(parents=True, exist_ok=True)
    (ref / f"{slug}.md").write_text(texto.strip() + "\n", encoding="utf-8")
    return {"ok": True, "arquivo": f"contexto/referencia/{slug}.md", "titulo": slug,
            "resumo": gm._sem_html(texto)[:180]}


def skills(base):
    """Skills do OS (.claude/skills/*/SKILL.md), nome+desc do frontmatter."""
    sdir = Path(base) / ".claude" / "skills"
    out = []
    if sdir.is_dir():
        for d in sorted(x for x in sdir.glob("*") if x.is_dir()):
            nome, desc = gm._ler_fm(d / "SKILL.md") if (d / "SKILL.md").exists() else ("", "")
            out.append({"slug": d.name, "nome": nome or d.name, "desc": desc,
                        "cmd": "/" + d.name, "obrigatoria": d.name == "extrair-design-system"})
    return out


def integracoes(base):
    """Status das conexões do OS: o cérebro (Claude Code na assinatura do comprador), a
    fonte de dados dele, o knowledge base e o time. Nunca expõe segredo, só ok/faltando."""
    base = Path(base)
    reco = {}
    mj = base / "meu-os.json"
    if mj.exists():
        try:
            reco = json.loads(mj.read_text(encoding="utf-8"))
        except Exception:
            reco = {}
    fonte = reco.get("fonte") or {}
    ref = base / "contexto" / "referencia"
    ndocs = len([f for f in ref.rglob("*") if f.is_file() and f.suffix.lower() in (".md", ".txt", ".csv")
                 and f.name.lower() != "readme.md"]) if ref.is_dir() else 0
    adir, sdir = base / ".claude" / "agents", base / ".claude" / "skills"
    nag = len(list(adir.glob("*.md"))) if adir.is_dir() else 0
    nsk = len([x for x in sdir.glob("*") if x.is_dir()]) if sdir.is_dir() else 0
    return {"conexoes": [
        {"chave": "cerebro", "ic": "🧠", "ok": bool(shutil.which("claude")), "nome": "Claude Code",
         "sub": "O motor do chat e dos builds do time. Roda na SUA assinatura, R$ 0 de token de API."},
        {"chave": "fonte", "ic": "🗄️", "ok": bool(fonte.get("titulo")),
         "nome": fonte.get("titulo") or "sua fonte de dados",
         "sub": fonte.get("sub") or "Conecte uma planilha, um banco ou uma API pro time enxergar seu número."},
        {"chave": "knowledge", "ic": "📚", "ok": ndocs > 0,
         "nome": f"Knowledge base ({ndocs} doc" + ("s" if ndocs != 1 else "") + ")",
         "sub": "Os documentos do seu negócio em contexto/referencia/. O time e o chat usam como verdade."},
        {"chave": "time", "ic": "❖", "ok": nag > 0, "nome": f"{nag} agentes · {nsk} skills",
         "sub": "Seu time montado pelo Genesis, invocável de verdade no Claude Code."},
    ]}


def ler_skill(base, slug):
    p = _dentro(Path(base) / ".claude" / "skills", f"{gm._slug(slug)}/SKILL.md")
    if not p or not p.is_file():
        return None
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None


def gravar_skill(base, slug, conteudo):
    p = _dentro(Path(base) / ".claude" / "skills", f"{gm._slug(slug)}/SKILL.md")
    if not p:
        return False
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(conteudo, encoding="utf-8")
        return True
    except OSError:
        return False


# ---------- Board de tasks + build (claude -p na assinatura do comprador) --------
# Mesma disciplina do painel do founder: estado DECLARADO por fonte (manual, chat, build),
# arquivo único .genesis-tasks.json, escrita atômica. Uma IDEIA é um card backlog+ativo=False;
# ao ATIVAR, dispara build.iniciar no repo do comprador e o card acompanha backlog->doing->done.

_TASKS_LOCK = threading.Lock()
_ST = ("backlog", "doing", "done")


def _agora():
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def _tasks_arq(base):
    return Path(base) / ".genesis-tasks.json"


def tasks_listar(base):
    try:
        d = json.loads(_tasks_arq(base).read_text(encoding="utf-8"))
        return d if isinstance(d, list) else []
    except (OSError, ValueError):
        return []


def _tasks_gravar(base, cards):
    arq = _tasks_arq(base)
    tmp = arq.with_suffix(".tmp")
    tmp.write_text(json.dumps(cards, ensure_ascii=False), encoding="utf-8")
    tmp.replace(arq)


def task_registrar(base, titulo, agente="", status="backlog", ativo=True, detalhe="",
                   origem=None, fonte="painel", resultado=None, saida=None):
    """Cria (ou atualiza, se `origem` já existe) um card. `detalhe` = descrição do dono,
    `resultado` = saída do build (nunca sobrescreve a descrição)."""
    titulo = (titulo or "").strip()[:200]
    if not titulo:
        return None
    if status not in _ST:
        status = "backlog"
    with _TASKS_LOCK:
        cards = tasks_listar(base)
        if origem:
            for c in cards:
                if c.get("origem") == origem:
                    c["status"] = status
                    c["atualizado"] = _agora()
                    if detalhe:
                        c["detalhe"] = detalhe
                    if resultado is not None:
                        c["resultado"] = resultado
                    if saida is not None:
                        c["saida"] = saida
                    if ativo:
                        c["ativo"] = True
                    _tasks_gravar(base, cards)
                    return c["id"]
        cid = uuid.uuid4().hex[:10]
        cards.append({"id": cid, "titulo": titulo, "agente": agente, "fonte": fonte,
                      "status": status, "ativo": bool(ativo), "detalhe": detalhe,
                      "resultado": resultado or "", "saida": saida or [],
                      "origem": origem or f"task:{cid}", "criado": _agora(), "atualizado": _agora()})
        del cards[:-300]
        _tasks_gravar(base, cards)
        return cid


def task_atualizar(base, cid, **campos):
    perm = {"titulo", "status", "ativo", "detalhe", "agente", "resultado", "saida"}
    with _TASKS_LOCK:
        cards = tasks_listar(base)
        for c in cards:
            if c.get("id") == cid:
                for k, v in campos.items():
                    if k in perm and v is not None:
                        if k == "status" and v not in _ST:
                            continue
                        c[k] = v
                c["atualizado"] = _agora()
                _tasks_gravar(base, cards)
                return dict(c)
    return None


def task_obter(base, cid):
    return next((c for c in tasks_listar(base) if c.get("id") == cid), None)


def task_remover(base, cid):
    with _TASKS_LOCK:
        cards = tasks_listar(base)
        novo = [c for c in cards if c.get("id") != cid]
        if len(novo) != len(cards):
            _tasks_gravar(base, novo)
            return True
    return False


# --- Build: delega uma tarefa pro Claude Code do comprador, no repo dele (na assinatura,
# R$ 0). Um por vez. Worklog ao vivo pro detalhe da task. Watchdog de 15min. git bloqueado
# pela instrução (o repo é do comprador, mas versionar é decisão dele, fora do build). ---

_BUILD = {"ativo": False, "tarefa": "", "eventos": [], "iniciado": 0.0, "origem": ""}
_TIMEOUT_BUILD = 15 * 60
_RE_SAIDA_B = re.compile(r"(?:producao|contexto|\.claude)[/\\][\w\-./\\]+")


def _bev(tipo, detalhe):
    _BUILD["eventos"].append({"tipo": tipo, "detalhe": str(detalhe)[:200]})
    del _BUILD["eventos"][:-200]


def build_status():
    with _TASKS_LOCK:
        return {"ativo": _BUILD["ativo"], "tarefa": _BUILD["tarefa"],
                "eventos": _BUILD["eventos"][-40:], "origem": _BUILD["origem"],
                "segundos": int(time.time() - _BUILD["iniciado"]) if _BUILD["ativo"] else 0}


def build_iniciar(base, tarefa, origem=None):
    tarefa = (tarefa or "").strip()
    if not tarefa:
        return {"erro": "tarefa vazia"}
    with _TASKS_LOCK:
        if _BUILD["ativo"]:
            return {"erro": f"já tem um build rodando ({_BUILD['tarefa'][:50]}). Espera ele terminar."}
        og = origem or ("build:" + uuid.uuid4().hex[:8])
        _BUILD.update({"ativo": True, "tarefa": tarefa, "eventos": [],
                       "iniciado": time.time(), "origem": og})
    threading.Thread(target=_build_rodar, args=(base, tarefa, og), daemon=True).start()
    return {"ok": True}


def _detectar_saida_b(base, texto):
    achados = []
    for m in _RE_SAIDA_B.finditer(texto or ""):
        p = m.group(0).rstrip(".,;:)]}\"' ").replace("\\", "/")
        if p and p not in achados and (Path(base) / p).exists():
            achados.append(p)
    return achados[:6]


def _build_rodar(base, tarefa, origem):
    task_registrar(base, tarefa, status="doing", fonte="build", origem=origem)
    _bev("inicio", tarefa[:120])
    ok, resultado = False, ""
    exe = shutil.which("claude")
    if not exe:
        _bev("erro", "o comando claude não está no PATH")
        resultado = "o comando claude não está no PATH"
    else:
        prompt = (
            "Tarefa pedida pelo dono deste OS. Execute e entregue de VERDADE (escreva os "
            "arquivos em producao/). Faça você mesmo com Read/Write/Bash, NUNCA delegue a "
            "subagente. Confirme que o(s) arquivo(s) existem no disco antes de dizer que "
            "terminou. NUNCA rode comandos git (versionar é decisão do dono, fora do build). "
            "Ao terminar, responda em no máximo 2 frases de texto puro (sem markdown): o que "
            "fez + o caminho dos arquivos.\n\nTarefa: " + tarefa)
        proc = None

        def _matar():
            if proc and proc.poll() is None:
                _bev("erro", f"passou de {_TIMEOUT_BUILD // 60}min, abortado")
                try:
                    if os.name == "nt":
                        subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True)
                    else:
                        proc.kill()
                except Exception:
                    pass

        wd = threading.Timer(_TIMEOUT_BUILD, _matar)
        wd.daemon = True
        try:
            proc = subprocess.Popen(
                [exe, "-p", "--permission-mode", "acceptEdits", "--output-format", "stream-json", "--verbose"],
                cwd=str(base), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                text=True, encoding="utf-8", errors="ignore",
                creationflags=0x08000000 if os.name == "nt" else 0)
            wd.start()
            proc.stdin.write(prompt)
            proc.stdin.close()
            for linha in proc.stdout:
                linha = linha.strip()
                if not linha or linha[0] != "{":
                    continue
                try:
                    ev = json.loads(linha)
                except ValueError:
                    continue
                tp = ev.get("type")
                if tp == "assistant":
                    for c in (ev.get("message") or {}).get("content") or []:
                        if c.get("type") == "tool_use":
                            inp = c.get("input") or {}
                            alvo = inp.get("file_path") or inp.get("command") or inp.get("path") or ""
                            _bev("tool", f"{c.get('name', '')} {str(alvo)[:80]}".strip())
                        elif c.get("type") == "text" and c.get("text", "").strip():
                            _bev("texto", c["text"].strip()[:150])
                elif tp == "result":
                    ok = ev.get("subtype") == "success"
                    resultado = gm._sem_canon(gm._sem_traves((ev.get("result") or "").strip()))
            proc.wait(timeout=20)
        except Exception as e:
            _bev("erro", str(e)[:150])
            resultado = resultado or str(e)[:150]
        finally:
            wd.cancel()
    saida = _detectar_saida_b(base, resultado)
    task_registrar(base, tarefa, status="done" if ok else "backlog", fonte="build",
                   origem=origem, resultado=(resultado or "")[:6000], saida=saida)
    _bev("fim", "pronto" if ok else "falhou")
    with _TASKS_LOCK:
        _BUILD["ativo"] = False


# ---------- Layout do canvas (posições arrastadas dos nós) ----------------------

def _layout_arq(base):
    return Path(base) / ".genesis-canvas-layout.json"


def layout_ler(base):
    try:
        return json.loads(_layout_arq(base).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def layout_gravar(base, posicoes):
    """Grava as posições dos nós do canvas (escrita atômica). posicoes = {slug: {x,y}}."""
    if not isinstance(posicoes, dict):
        return False
    arq = _layout_arq(base)
    tmp = arq.with_suffix(".tmp")
    try:
        tmp.write_text(json.dumps(posicoes, ensure_ascii=False), encoding="utf-8")
        tmp.replace(arq)
        return True
    except OSError:
        return False
