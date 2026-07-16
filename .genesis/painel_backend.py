"""Backend das views do painel do OS do comprador (além do /api/painel, que já mora no
genesis_motor). Fase A: detalhe de um agente + chat com ele. Fases seguintes acrescentam
catálogo (contexto/skills) e board de tasks.

Tudo LOCAL, na máquina do comprador, na assinatura DELE (claude -p headless, R$ 0, sem
chave paga). Reusa o genesis_motor pros helpers (claude -p, ler frontmatter, slug). Guard
de path em toda leitura/escrita: nunca sai de dentro do repo do comprador."""
import ipaddress
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from pathlib import Path
from urllib.parse import urlsplit

import genesis_motor as gm


def abrir(base, rel):
    """Abre um arquivo/pasta do OS na máquina do comprador (botão 'abrir' do resultado da
    task). Guard de path: só dentro do repo do comprador.

    No Windows, `os.startfile` sozinho NÃO basta: quando a associação do tipo resolve pra
    um ProgId que o ShellExecute não materializa a partir deste processo (caso real: .md
    associado a 'Applications\\notepad++.exe'), ele retorna SUCESSO e nada abre. Por isso
    arquivo tenta o VS Code primeiro (`code`, que o comprador tem: o produto roda dentro
    dele) e cai pro Explorer com o arquivo selecionado, que sempre revela algo visível."""
    rel = (rel or "").strip().lstrip("/\\")
    if not rel:   # path vazio resolve pra base e abriria o repo inteiro no Explorer
        return {"ok": False, "erro": "caminho vazio"}
    p = _dentro(Path(base), rel)
    if not p or not p.exists() or p == Path(base).resolve():
        return {"ok": False, "erro": "não encontrado"}
    try:
        if os.name == "nt":
            if p.is_file():
                code = shutil.which("code")
                if code:
                    # `code` é um .cmd: precisa do cmd.exe por trás (shell). Paths validados.
                    subprocess.Popen(f'"{code}" "{p}"', shell=True,
                                     creationflags=0x08000000)
                    return {"ok": True, "abriu": rel, "via": "vscode"}
                # sem VS Code no PATH: Explorer com o arquivo selecionado (sempre aparece)
                subprocess.Popen(["explorer", "/select,", str(p)])
                return {"ok": True, "abriu": rel, "via": "explorer"}
            os.startfile(str(p))          # pasta: Explorer direto, confiável
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(p)])
        else:
            subprocess.Popen(["xdg-open", str(p)])
        return {"ok": True, "abriu": rel}
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


# A GAIOLA DO CHAT, dita com todas as letras (caso real 2026-07-16: o agente oferecia
# "quer que eu rode /titulos?" sem ter como executar skill nenhuma, e a tentativa dava
# erro). O conserto NÃO é dar mais poder ao chat (reabriria o risco todo): é o agente
# admitir a própria gaiola e apontar o caminho real (build ou o /comando no Claude Code).
_GAIOLA = (
    "SUA GAIOLA (seja honesto sobre ela): neste chat você SÓ LÊ. Você NÃO executa skills "
    "(/comandos), NÃO escreve arquivo, NÃO roda comando nenhum. NUNCA ofereça 'quer que eu "
    "rode /skill?' nem prometa disparar qualquer coisa: você não consegue, e prometer é "
    "mentir. Quando o pedido exigir executar ou produzir (rodar uma skill, gravar um "
    "lançamento, gerar um arquivo), aponte o caminho real: ele clica em 'põe pra trabalhar' "
    "(o build, que tem as ferramentas de escrita), ou roda a skill direto no Claude Code "
    "dele (digitando o /comando lá)."
)


def persona_chat(base, slug):
    """A persona completa pro 1º turno do chat (SDK ou single-shot): o corpo do .agent.md
    + o contexto do OS (perfil, fonte, knowledge base). Vai por stdin, sem limite de argv."""
    det = agente_detalhe(base, slug)
    if not det:
        return None, None
    kb = _knowledge(base)
    persona = (
        f"=== SUA PERSONA (assuma isto por completo, você É {det['nome']}) ===\n"
        f"{det['nome']}\n{det['corpo']}\n"
        + (f"\n=== CONTEXTO DO DONO DO OS (quem ele é, o negócio, a fonte de dados) ===\n{kb}\n" if kb else "")
    )
    return det, persona


def chat(base, slug, mensagens):
    """Conversa com um agente do time (caminho single-shot, o FALLBACK do streaming via
    SDK): a persona é o corpo do .agent.md dele, mais o contexto do OS por cima. Roda na
    assinatura do comprador (claude -p, R$ 0), turno a turno, reenvia a conversa inteira.
    Devolve {ok, resposta} ou {ok:False, erro}."""
    det, persona = persona_chat(base, slug)
    if not det:
        return {"ok": False, "erro": "agente não encontrado"}
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
        "é direto pra você, FAÇA, não empurre pra outro. Nunca invente número ou fato; se não "
        "achar nem lendo, diga que não achou.\n" + _GAIOLA
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
        persona
        + "\n=== CONVERSA (responda a última fala do Comprador, como " + det["nome"] + ") ===\n"
        + "\n".join(linhas) + f"\n\n{det['nome']}:"
    )
    # erro com CAUSA, não chute: "o claude está no PATH?" quando o problema era timeout
    # mandava o comprador caçar o problema errado (caso real com /titulos).
    if not shutil.which("claude"):
        return {"ok": False, "erro": "o comando 'claude' não está no PATH. Instale o Claude Code."}
    # tools de leitura + cwd no repo do aluno: o agente LÊ os arquivos do comprador (producao/,
    # contexto/) pra responder com dado real. Só leitura (Read/Grep/Glob); escrita é no build.
    texto = gm._claude_cli(prompt, system, tools="Read Grep Glob", cwd=base)
    if texto is None:
        return {"ok": False, "erro": "não consegui responder agora (o turno falhou ou demorou "
                                     "demais). Tenta de novo em alguns segundos."}
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
    rel = f.relative_to(base).as_posix()
    return {"rel": rel, "nome": f.name,
            "pasta": (f.parent.relative_to(base).as_posix() if f.parent != base else ""),
            "kb": round(f.stat().st_size / 1024, 1),
            # `editavel` reflete a regra de ESCRITA real (_permitido): antes todo .md abria
            # com botão Editar, mas um CLAUDE.md aninhado não é gravável pelo painel, então
            # a pessoa editava, via "salvo ✓" e o gravar descartava tudo calado.
            "editavel": f.suffix.lower() == ".md" and _permitido(rel, escrita=True)}


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
    """Contexto navegável: os mapas CLAUDE.md do repo + o vault contexto/. O README do
    template (contexto/referencia/README.md) fica de fora: é instrução NOSSA pro comprador,
    não conhecimento dele (mesma regra do _eh_doc da cena de abastecimento)."""
    base = Path(base)
    itens = [_item_ctx(base, f) for f in sorted(_mapas_claude(base))]
    cdir = base / "contexto"
    if cdir.is_dir():
        for f in sorted(cdir.rglob("*")):
            if (f.is_file() and f.suffix.lower() in _EXT_VAULT and ".git" not in f.parts
                    and not (f.name.lower() == "readme.md" and f.parent.name == "referencia")):
                itens.append(_item_ctx(base, f))
    return itens


def _permitido(rel_posix, escrita=False):
    """LEITURA: um CLAUDE.md em qualquer lugar (o vault lista os mapas espalhados), ou algo em
    contexto/. ESCRITA é mais estrita: só o CLAUDE.md RAIZ (o cérebro do OS) ou contexto/. Um
    CLAUDE.md aninhado (producao/sub/CLAUDE.md) é lido, mas não gravável pelo painel: senão o
    endpoint vira via de plantar instrução que o build roda com acceptEdits."""
    if rel_posix == "contexto" or rel_posix.startswith("contexto/"):
        return True
    if escrita:
        return rel_posix == "CLAUDE.md"          # só o cérebro raiz
    return rel_posix.rsplit("/", 1)[-1] == "CLAUDE.md"


def _resolve_ctx(base, rel, escrita=False):
    rel = (rel or "").strip().lstrip("/\\")
    baseR = Path(base).resolve()
    try:
        alvo = (baseR / rel).resolve()
        relp = alvo.relative_to(baseR).as_posix()   # guard de path traversal
    except (ValueError, OSError):
        return None
    return alvo if _permitido(relp, escrita) else None


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
    """Grava só .md permitido (CLAUDE.md RAIZ ou contexto/*.md). Escrita atômica."""
    f = _resolve_ctx(base, rel, escrita=True)
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


_ERRO_INTERNO = ("esse link aponta pra um endereço interno, use o site público da sua empresa")


def _url_publica(url):
    """Anti-SSRF: a URL que o comprador cola vai pro WebFetch, que roda server-side na máquina
    dele. Devolve None se pode seguir, ou a mensagem de erro.

    Duas decisões que a versão anterior errou, e por isso estão explícitas aqui:

    1) PARSE com urlsplit, nunca regex na mão. `urlsplit` descarta o userinfo, então
       `https://evil.com@169.254.169.254/` devolve hostname='169.254.169.254' e é barrado. O
       split manual em '/' e ':' via host='evil.com@169.254.169.254', que não casa nenhum
       prefixo e passava direto pro metadata da cloud.

    2) RESOLVE o nome e testa TODOS os IPs, nunca regex de prefixo no texto do host. É o
       único jeito de pegar os dois casos que texto nenhum revela: o IP escrito em hex/octal
       (`0x7f.0.0.1` e `0177.0.0.1` resolvem 127.0.0.1) e o domínio público que aponta pra
       dentro (`interno.exemplo.com` -> 10.0.0.5), que é o SSRF clássico.

    Sobra o DNS rebinding (o nome pode responder outro IP quando o WebFetch resolver de novo,
    depois da nossa checagem). Fechar isso exigiria fixar o IP e controlar o fetch, que não é
    nosso, é do Claude Code. Fica o teto conhecido: o custo é o comprador conseguir apontar
    pro próprio LAN dele, na máquina dele, com um domínio que ele mesmo controla."""
    try:
        p = urlsplit(url)
        porta = p.port or (443 if p.scheme.lower() == "https" else 80)
    except ValueError:            # porta lixo, colchete IPv6 torto
        return "link inválido"
    if p.scheme.lower() not in ("http", "https"):
        return "link inválido"
    host = (p.hostname or "").strip().rstrip(".")     # hostname já vem sem userinfo e minúsculo
    if not host:
        return "link inválido"
    try:
        infos = socket.getaddrinfo(host, porta, proto=socket.IPPROTO_TCP)
    except (OSError, UnicodeError, ValueError):
        return "não consegui resolver esse endereço, confere o link"
    ips = {i[4][0].split("%")[0] for i in infos}      # tira o scope id do IPv6 (fe80::1%eth0)
    if not ips:
        return "não consegui resolver esse endereço, confere o link"
    for bruto in ips:
        try:
            ip = ipaddress.ip_address(bruto)
        except ValueError:        # não soube ler o IP: nega, não adivinha
            return _ERRO_INTERNO
        # is_global cobre privado/loopback/link-local/reservado/multicast num teste só, e sabe
        # das faixas que a gente esqueceria na mão (100.64/10 CGNAT, 198.18/15 bench, IPv6).
        if not ip.is_global:
            return _ERRO_INTERNO
    return None


def puxar_site(base, url):
    """O comprador cola o LINK da empresa dele; o Claude Code DELE lê o site (WebFetch) e
    escreve um brief do negócio em contexto/referencia/<dominio>.md, que a montagem e o chat
    passam a usar como knowledge base. Roda na assinatura dele (R$ 0). Devolve
    {ok, arquivo, titulo, resumo} ou {ok:False, erro}. Guard: só grava dentro de referencia."""
    url = (url or "").strip()
    if not re.match(r"^https?://", url, re.I):
        url = "https://" + url
    erro = _url_publica(url)
    if erro:
        return {"ok": False, "erro": erro}
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


# ---------- Referência: o knowledge base que o comprador conecta na cena ---------
# A cena de abastecimento (antes da entrevista) grava aqui pelos 3 caminhos: soltar arquivo,
# colar o link do site (puxar_site, acima) e colar texto de outro assistente. É a mesma pasta
# que `gm._ler_referencia` lê na entrevista e na montagem, então o que entra aqui vira time.

_EXT_REF = (".md", ".txt", ".csv")


def _ref_dir(base):
    d = Path(base) / "contexto" / "referencia"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _eh_doc(f):
    """O que conta como doc CONECTADO pelo comprador. Um predicado só pros três usos (listar,
    contar no cap, remover): quando cada um decidia por conta, o listar escondia o README do
    template (é instrução nossa) e o remover apagava ele, porque '.md' está em _EXT_REF."""
    return (f.is_file() and f.suffix.lower() in _EXT_REF
            and f.name.lower() != "readme.md")


def _slug_doc(nome):
    """Slug pra NOME DE ARQUIVO. Não reusa gm._slug de propósito: aquele nasceu pra nomear
    AGENTE e cai em 'agente' quando não sobra nada, então um doc chamado '文档.md' (nada de
    ascii) viraria 'agente.md' na pasta de referência, parecendo um membro do time. Aqui o
    default é 'doc'. Trunca em 80: nome de 500 chars estoura o MAX_PATH do Windows, e aí o
    OSError vaza o path absoluto do servidor na mensagem de erro (info disclosure)."""
    s = re.sub(r"[^a-z0-9]+", "-", gm._sem_acento(nome)).strip("-")[:80].strip("-")
    return s or "doc"


def referencia_listar(base):
    """O que já está conectado (pra cena mostrar em vez de pedir de novo)."""
    d = Path(base) / "contexto" / "referencia"
    if not d.is_dir():
        return []
    return [{"nome": f.name, "rel": f.relative_to(d).as_posix(),
             "kb": round(f.stat().st_size / 1024, 1)}
            for f in sorted(d.rglob("*")) if _eh_doc(f)]


_REF_MAX_DOCS = 60          # cap de contagem: sem isto, um cliente local enche o disco
_REF_MAX_TOTAL = 8_000_000  # cap de soma da pasta (~8 MB de texto é mais que o time lê)
# Serializa cap + escolha do nome + gravação. O Flask atende em thread, e a cena manda um
# POST por arquivo solto: sem isto, dois uploads concorrentes leem o mesmo contador e escolhem
# o mesmo path livre, e o segundo sobrescreve o primeiro CALADO (o comprador vê os dois itens
# pintados na lista e o time nasce sem um dos documentos).
_REF_LOCK = threading.Lock()


def referencia_gravar(base, nome, conteudo):
    """Grava um doc do comprador em contexto/referencia/. Guard: nome saneado (nunca sai da
    pasta), só extensão de texto (é o que a montagem sabe ler, prometer .xlsx seria mentira),
    teto por arquivo E cap de contagem/soma da pasta (senão um cliente local enche o disco)."""
    conteudo = str(conteudo or "")
    if not conteudo.strip():
        return {"ok": False, "erro": "conteúdo vazio"}
    if len(conteudo) > 400_000:
        return {"ok": False, "erro": "arquivo grande demais (limite de 400 KB de texto)"}
    nome = (str(nome or "").strip() or "colado.md").replace("\\", "/").split("/")[-1]
    caule, ponto, ext = nome.rpartition(".")
    ext = ("." + ext.lower()) if ponto else ""
    if ext and ext not in _EXT_REF:
        # binário salvo como texto vira lixo no prompt e o time nasce lendo ruído. Recusar
        # é mais honesto que aceitar e fingir, e a mensagem já entrega a saída.
        return {"ok": False, "erro": f"não consigo ler {ext} como texto. "
                "Planilha, exporte em CSV. Documento, salve como .txt ou .md."}
    if not ext:
        caule, ext = (caule or nome), ".md"   # sem extensão, é texto colado: vira .md
    slug = _slug_doc(caule)
    d = _ref_dir(base)
    with _REF_LOCK:
        # cap da pasta inteira: nº de docs e soma de bytes. Protege contra disk-fill por
        # gravação repetida (a chamada é gated pelo token, mas um cliente local não pode
        # encher o disco). Contar e gravar dentro do MESMO lock: separados, dois uploads
        # simultâneos leem o contador antes de qualquer um gravar e os dois passam.
        docs = [f for f in d.rglob("*") if _eh_doc(f)]
        if len(docs) >= _REF_MAX_DOCS:
            return {"ok": False, "erro": f"você já conectou {_REF_MAX_DOCS} documentos, o "
                    "limite. Tire algum antes de adicionar mais."}
        if sum(f.stat().st_size for f in docs) + len(conteudo.encode("utf-8")) > _REF_MAX_TOTAL:
            return {"ok": False, "erro": "a pasta de referência já está no limite de tamanho. "
                    "Tire algum documento antes de adicionar mais."}
        # 'x' = O_EXCL: quem cria, cria. Nunca sobrescreve o que o comprador já conectou,
        # mesmo se o lock não existisse (era exists() + write, e entre um e outro cabia a
        # requisição vizinha escolher o mesmo path).
        f = None
        for n in range(1, _REF_MAX_DOCS + 2):
            alvo = d / (f"{slug}{ext}" if n == 1 else f"{slug}-{n}{ext}")
            try:
                with open(alvo, "x", encoding="utf-8") as fh:
                    fh.write(conteudo)
                f = alvo
                break
            except FileExistsError:
                continue
            except OSError:
                # genérica: o str(OSError) carrega o path absoluto do servidor (info disclosure)
                return {"ok": False, "erro": "não consegui gravar o arquivo"}
        if f is None:
            return {"ok": False, "erro": "já tem documentos demais com esse nome, "
                    "renomeie o arquivo antes de conectar."}
    return {"ok": True, "nome": f.name, "rel": f.name,
            "kb": round(f.stat().st_size / 1024, 1)}


def referencia_remover(base, rel):
    """Tira um doc conectado (o comprador soltou o arquivo errado). Guard de path traversal,
    e _eh_doc pra não apagar o README do template (que o listar nem mostra)."""
    d = _ref_dir(base)
    p = _dentro(d, (rel or "").strip().lstrip("/\\"))
    if not p or not _eh_doc(p):
        return False
    try:
        p.unlink()
        return True
    except OSError:
        return False


def _bonus_slugs():
    """Slugs das skills-brinde (fixas, nossas), lidas do manifesto .genesis/bonus-skills.json.
    São as skills que já vêm prontas no template (ex: /site-reveal-cinematico), separadas das
    sob medida que o Genesis escreve na entrevista."""
    f = Path(__file__).resolve().parent / "bonus-skills.json"
    try:
        return {s.get("slug") for s in json.loads(f.read_text(encoding="utf-8"))}
    except Exception:
        return set()


def skills(base):
    """Skills do OS (.claude/skills/*/SKILL.md), nome+desc do frontmatter. Marca `bonus` nas
    skills-brinde (manifesto) pra o catálogo mostrá-las separadas das sob medida."""
    sdir = Path(base) / ".claude" / "skills"
    bonus = _bonus_slugs()
    out = []
    if sdir.is_dir():
        for d in sorted(x for x in sdir.glob("*") if x.is_dir()):
            nome, desc = gm._ler_fm(d / "SKILL.md") if (d / "SKILL.md").exists() else ("", "")
            out.append({"slug": d.name, "nome": nome or d.name, "desc": desc,
                        "cmd": "/" + d.name, "obrigatoria": d.name == "extrair-design-system",
                        "bonus": d.name in bonus})
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
    # HONESTIDADE do status da fonte: o `titulo` vem do meu-os.json, que é a RECOMENDAÇÃO
    # da entrevista ("o que você deveria conectar"), não uma conexão. Marcar "conectado" só
    # porque a sugestão existe era mentira na cara do comprador (caso real: "Planilha
    # financeira do LUKK · CONECTADO" com o próprio sub pedindo pra conectar). Conectada de
    # verdade = flag explícita `fonte.conectada` no meu-os.json OU dado real no vault
    # (algum .csv/.xlsx em contexto/, fora o template).
    tem_dado = any(f.suffix.lower() in (".csv", ".xlsx")
                   for f in (base / "contexto").rglob("*") if f.is_file()) \
        if (base / "contexto").is_dir() else False
    fonte_ok = bool(fonte.get("conectada")) or tem_dado
    return {"conexoes": [
        {"chave": "cerebro", "ic": "🧠", "ok": bool(shutil.which("claude")), "nome": "Claude Code",
         "sub": "O motor do chat e dos builds do time. Roda na SUA assinatura, R$ 0 de token de API."},
        {"chave": "fonte", "ic": "🗄️", "ok": fonte_ok,
         "pendente": bool(fonte.get("titulo")) and not fonte_ok,
         "nome": fonte.get("titulo") or "sua fonte de dados",
         "sub": (fonte.get("sub") or "Conecte uma planilha, um banco ou uma API pro time enxergar seu número.")
         if fonte_ok or not fonte.get("titulo") else
         "Ainda não conectada. Solte um export (.csv) em contexto/ ou descreva o acesso em contexto/fonte.md, e o time passa a enxergar seu número."},
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
# 5 estados, os mesmos do painel do founder: `revisar` = o build entregou ARQUIVO e o dono
# confere antes de fechar; `falhou` = coluna própria (falha que voltava pro backlog se
# disfarçava de ideia nova e ninguém via). Cards antigos com os 3 estados seguem válidos.
_ST = ("backlog", "doing", "revisar", "done", "falhou")


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
                   origem=None, fonte="painel", resultado=None, saida=None, falhou=None):
    """Cria (ou atualiza, se `origem` já existe) um card. `detalhe` = descrição do dono,
    `resultado` = saída do build (nunca sobrescreve a descrição). `falhou` = o build deu
    ruim: o card volta pro backlog COM a marca, em vez de se disfarçar de ideia nova."""
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
                    if falhou is not None:
                        c["falhou"] = bool(falhou)
                    if ativo:
                        c["ativo"] = True
                    _tasks_gravar(base, cards)
                    return c["id"]
        cid = uuid.uuid4().hex[:10]
        cards.append({"id": cid, "titulo": titulo, "agente": agente, "fonte": fonte,
                      "status": status, "ativo": bool(ativo), "detalhe": detalhe,
                      "resultado": resultado or "", "saida": saida or [], "falhou": bool(falhou),
                      "origem": origem or f"task:{cid}", "criado": _agora(), "atualizado": _agora()})
        del cards[:-300]
        _tasks_gravar(base, cards)
        return cid


def task_atualizar(base, cid, **campos):
    perm = {"titulo", "status", "ativo", "detalhe", "agente", "resultado", "saida", "falhou"}
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

_BUILD = {"ativo": False, "tarefa": "", "eventos": [], "iniciado": 0.0, "origem": "",
          "agente": "", "proc": None, "parado": False, "ult_pulso": 0.0}
_TIMEOUT_BUILD = 15 * 60
_RE_SAIDA_B = re.compile(r"(?:producao|contexto|\.claude)[/\\][\w\-./\\]+")


def _pulso(base, agente, acao):
    """Grava um evento no pulso do OS (`.genesis-atividade.jsonl`, o mesmo arquivo do hook
    PostToolUse). Sem isto, o caminho PRINCIPAL de trabalho (o build do painel) nunca acendia
    o time: o hook só registra a tool Task, e o prompt do build proíbe subagente, então
    build nenhum gerava pulso e o dashboard vivia em 'repouso' com build rodando."""
    try:
        with (Path(base) / ".genesis-atividade.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"ts": time.time(), "agente": agente or "",
                                 "acao": str(acao or "")[:120]}, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _bev(tipo, detalhe, base=None):
    _BUILD["eventos"].append({"tipo": tipo, "detalhe": str(detalhe)[:200]})
    del _BUILD["eventos"][:-200]
    # alimenta o pulso com throttle (1 evento a cada ~40s basta pra manter o agente 'vivo'
    # no canvas/dashboard sem inflar o feed)
    if base and tipo == "tool" and time.time() - _BUILD["ult_pulso"] > 40:
        _BUILD["ult_pulso"] = time.time()
        _pulso(base, _BUILD.get("agente"), detalhe)


def build_status():
    with _TASKS_LOCK:
        return {"ativo": _BUILD["ativo"], "tarefa": _BUILD["tarefa"],
                "eventos": _BUILD["eventos"][-40:], "origem": _BUILD["origem"],
                "segundos": int(time.time() - _BUILD["iniciado"]) if _BUILD["ativo"] else 0}


def build_iniciar(base, tarefa, origem=None, contexto="", agente=""):
    """`contexto` = a transcrição da conversa do chat que gerou o pedido (o build parte
    sabendo O QUE foi combinado, não cego). `agente` = slug do agente do time, pro pulso."""
    tarefa = (tarefa or "").strip()
    if not tarefa:
        return {"erro": "tarefa vazia"}
    with _TASKS_LOCK:
        if _BUILD["ativo"]:
            return {"erro": f"já tem um build rodando ({_BUILD['tarefa'][:50]}). Espera ele terminar."}
        og = origem or ("build:" + uuid.uuid4().hex[:8])
        _BUILD.update({"ativo": True, "tarefa": tarefa, "eventos": [],
                       "iniciado": time.time(), "origem": og,
                       "agente": agente or "", "proc": None, "parado": False, "ult_pulso": 0.0})
    threading.Thread(target=_build_rodar, args=(base, tarefa, og, contexto), daemon=True).start()
    return {"ok": True}


def build_parar(base):
    """Encerra o build em andamento (botão '■ Encerrar' do detalhe da task). Antes o botão
    existia na tela e não fazia NADA (não havia endpoint): o único fim possível era o
    watchdog de 15min. Mata a árvore do processo (o claude no Windows é um shim cmd.exe,
    matar só o pai deixa o filho vivo)."""
    with _TASKS_LOCK:
        if not _BUILD["ativo"]:
            return {"ok": False, "erro": "não tem build rodando"}
        _BUILD["parado"] = True
        proc = _BUILD.get("proc")
    if proc and proc.poll() is None:
        try:
            if os.name == "nt":
                subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True)
            else:
                proc.kill()
        except Exception:
            pass
    _bev("erro", "encerrado pelo dono")
    return {"ok": True}


def _detectar_saida_b(base, texto):
    achados = []
    for m in _RE_SAIDA_B.finditer(texto or ""):
        p = m.group(0).rstrip(".,;:)]}\"' ").replace("\\", "/")
        if p and p not in achados and (Path(base) / p).exists():
            achados.append(p)
    return achados[:6]


def _build_rodar(base, tarefa, origem, contexto=""):
    task_registrar(base, tarefa, status="doing", fonte="build", origem=origem, falhou=False)
    _bev("inicio", tarefa[:120])
    _pulso(base, _BUILD.get("agente"), "começou: " + tarefa[:90])
    ok, resultado = False, ""
    exe = shutil.which("claude")
    if not exe:
        _bev("erro", "o comando claude não está no PATH")
        resultado = "o comando claude não está no PATH"
    else:
        # a conversa do chat que gerou o pedido viaja como CONTEXTO do prompt (nunca do
        # card): o build parte sabendo o que já foi decidido, referências e formato.
        bloco_ctx = ""
        if (contexto or "").strip():
            bloco_ctx = ("\nContexto: antes de pedir isso, o dono conversou com o agente no "
                         "chat. Use a conversa abaixo pra entender EXATAMENTE o que ele quer "
                         "(o que já foi decidido, referências, formato). NÃO responda a "
                         "conversa, PRODUZA o entregável.\n--- conversa ---\n"
                         + contexto.strip()[:16000] + "\n--- fim da conversa ---\n")
        prompt = (
            "Tarefa pedida pelo dono deste OS. Execute e entregue de VERDADE (escreva os "
            "arquivos em producao/). Faça você mesmo com Read/Write/Bash, NUNCA delegue a "
            "subagente. Confirme que o(s) arquivo(s) existem no disco antes de dizer que "
            "terminou. NUNCA rode comandos git (versionar é decisão do dono, fora do build). "
            "Ao terminar, responda em no máximo 2 frases de texto puro (sem markdown): o que "
            "fez + o caminho dos arquivos.\n" + bloco_ctx + "\nTarefa: " + tarefa)
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
                env=gm._env_assinatura(),  # sem ANTHROPIC_API_KEY: billing na assinatura, não na API
                creationflags=0x08000000 if os.name == "nt" else 0)
            with _TASKS_LOCK:
                _BUILD["proc"] = proc    # o build_parar mata a árvore por aqui
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
                            _bev("tool", f"{c.get('name', '')} {str(alvo)[:80]}".strip(), base)
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
    if _BUILD.get("parado"):
        ok, resultado = False, "encerrado pelo dono antes de terminar."
    saida = _detectar_saida_b(base, resultado)
    # regra de estado do painel do founder: falhou é coluna própria; sucesso COM arquivo
    # vai pra `revisar` (o dono confere antes de fechar); sucesso sem arquivo (análise,
    # resposta) fecha direto em `done`.
    st_fim = "falhou" if not ok else ("revisar" if saida else "done")
    task_registrar(base, tarefa, status=st_fim, fonte="build",
                   origem=origem, resultado=(resultado or "")[:6000], saida=saida,
                   falhou=(not ok))
    _bev("fim", "pronto" if ok else "falhou")
    _pulso(base, _BUILD.get("agente"), "entregou" if ok else "o build falhou")
    with _TASKS_LOCK:
        _BUILD["ativo"] = False
        _BUILD["proc"] = None


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
