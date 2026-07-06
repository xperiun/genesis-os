"""Motor do Genesis Studio: o Claude conduz a entrevista de onboarding e projeta o
time sob medida do comprador. Inventa os especialistas certos pro caso dela e o Claude
Code dela pesquisa na web e escreve cada um do zero. É o coração do produto.

Contrato com o frontend (genesis.html):
  passo(historico) -> dict
    historico: [{"role":"x"|"voce","texto":str}, ...] (a conversa até agora)
    devolve UMA de duas formas:
      {"done": False, "pergunta": str, "candidato": {ic,nome,time}|None}
      {"done": True, "recomendacao": {entendi[], times[], skills[], nums{}, fonte{}}}

Seams de produto:
- ADAPTA ao perfil (analista técnico × novato só pela IA): a 1ª resposta calibra o tom.
- HONESTO: recomenda do catálogo que existe + skills que dá pra criar; nunca promete
  dado/venda que o comprador não tem. "Conecte sua realidade" é passo real, não fake.
- FALLBACK: se o Claude cair (sem chave, erro, JSON ruim), devolve um caminho digno em
  vez de travar o onboarding (a venda do produto não pode depender do caminho feliz).

Sem chave paga e sem catálogo fixo: o cérebro é o Claude Code do comprador (na assinatura
dele, R$ 0). Ordem: (1) Claude Code via `claude -p`; (2) entrevista determinística, pra
nunca travar. Sem dependência do loop de voz do X (persona diferente: aqui o X é um
entrevistador de onboarding, não o assistente do founder)."""
import json
import re
import shutil
import subprocess
import time
import unicodedata
from pathlib import Path

_SYSTEM = """Você é o X, o entrevistador de onboarding do OS do comprador. Sua missão nesta
conversa: CONHECER a pessoa que acabou de instalar o OS dela e, no fim, PROJETAR o time
de IA sob medida pra ela: especialistas feitos pro caso dela + skills que valha criar.

Quem responde é o COMPRADOR (não é o dono do produto). Pode ser um analista de dados (vá
mais fundo, técnico), um profissional de qualquer área (dentista, advogado, gestor) ou
alguém que veio só aprender IA/Claude (guie, sem jargão). A PRIMEIRA resposta calibra:
ajuste profundidade e linguagem.

Tom: direto, caloroso, brasileiro, afiado. Zero corporativês. Perguntas CURTAS, UMA de
cada vez (nunca empilhe várias numa frase). Nada de "Ótima pergunta"/"Perfeito"/"Vamos lá".

A PRIMEIRA pergunta é curta, aberta e acolhedora, e NÃO assume que a pessoa tem negócio ou
vende algo (ela pode ser funcionária, autônoma, estudante). Abra simples pelo que ela faz,
tipo "Pra começar, me conta: o que você faz no dia a dia?". Depois vá fundo pelas respostas.

Português do Brasil com TODOS os acentos. NUNCA use travessão (o traço "—") em lugar
nenhum: nem na pergunta, nem em NENHUM campo do JSON (entendi, por, desc, sub). Use
vírgula, ponto ou dois pontos. Travessão em prosa é vício de robô e queima a marca.
NUNCA escreva "canon" nem "canônico" (jargão de produção): use "de referência",
"principal" ou "padrão". O comprador lê isso e não pode parecer bug.

Faça de 4 a 6 perguntas boas (o que a pessoa faz, o que consome o tempo dela, o que ela
produz, meta pessoal/carreira, e se ela já tem algum DADO/fonte na mão ou começa do
zero). Quando tiver entendido o suficiente, MONTE o time.

Os agentes são SOB MEDIDA: você INVENTA os especialistas certos pro caso da pessoa (um
papel claro, não um nome de celebridade). Ex: "Analista de Varejo", "Narrador de Dados",
"Estrategista de LinkedIn". Depois da entrevista, o Claude Code do comprador vai
PESQUISAR na web e ESCREVER cada um a fundo. Você só define QUEM entra e POR QUÊ.

REGRAS DE HONESTIDADE (invioláveis):
- Cada agente é um papel real e útil pro caso dela. Nada genérico de enfeite.
- Skills são automações NOVAS a criar; descreva o payoff concreto.
- Sobre dado: se a pessoa TEM fonte, o "fonte" reflete isso; se NÃO tem, oriente a
  começar simples (uma planilha, um objetivo) sem prometer número que ela não tem.
- Nunca invente resultado, venda ou métrica.
- OBRIGATÓRIO: o time SEMPRE inclui um agente de Design System (slug design-system), que
  extrai o design system de uma referência e cria/mantém o do OS. Consistência visual é
  inegociável, então ele entra sempre, mesmo sem a pessoa pedir.

FORMATO DE RESPOSTA (responda SEMPRE com UM objeto JSON, e NADA além dele):
Pra continuar a entrevista:
{"acao":"perguntar","pergunta":"<sua pergunta curta>","candidato":{"ic":"<emoji>","nome":"<um especialista sob medida que já dá pra intuir>","papel":"<o que ele faz>"}}
(o "candidato" é opcional: inclua quando já der pra intuir um especialista que serve,
pra ele "se candidatar" na caixa de entrada. Omita ou null se ainda cedo.)

Pra montar o time no fim:
{"acao":"montar","recomendacao":{
  "entendi":["<3-4 frases curtas do que você entendeu, pode usar <b>negrito</b>>"],
  "agentes":[{"slug":"<kebab-case>","nome":"<nome do especialista>","ic":"<emoji>","tag":"Essencial|Recomendado|Opcional","por":"<1-2 frases: POR QUE esse especialista, amarrado ao que a pessoa disse, pode usar <b>>"}],
  "skills":[{"slug":"<kebab-case>","nome":"<nome curto>","ic":"<emoji>","cmd":"</comando>","desc":"<o que faz + payoff, pode usar <b>>"}],
  "fonte":{"titulo":"<a fonte/realidade a conectar>","sub":"<1-2 frases orientando>"}
}}

Recomende de 3 a 5 agentes e 2 a 4 skills. Priorize o que resolve a dor principal dela."""


_FALLBACK_PERGUNTAS = [
    "Antes de montar teu time, me conta: o que você faz, e o que mais te consome no trabalho?",
    "Entendi. E o que você produz hoje que, se saísse mais rápido ou melhor, mudaria teu jogo?",
    "Boa. Tem alguma meta pessoal (carreira, presença, um projeto) que um time seu poderia acelerar?",
    "Última: você já tem algum dado na mão (planilha, sistema, números), ou a gente começa do zero?",
]

_FALLBACK_RECO = {
    "entendi": ["Montei um time base sólido pra você começar. Refaça a entrevista quando quiser afinar ele pro seu caso."],
    "agentes": [
        {"slug": "analista-de-dados", "nome": "Analista de Dados", "ic": "📊", "tag": "Essencial", "por": "Pra transformar teu número em decisão."},
        {"slug": "narrador-de-dados", "nome": "Narrador de Dados", "ic": "🎬", "tag": "Recomendado", "por": "Pra teu dado virar história que decide."},
        {"slug": "estrategista-de-conteudo", "nome": "Estrategista de Conteúdo", "ic": "✍️", "tag": "Opcional", "por": "Pra teu insight virar conteúdo na tua voz."},
    ],
    "skills": [{"ic": "⚡", "slug": "relatorio-executivo", "nome": "Relatório executivo", "cmd": "/relatorio-executivo", "desc": "Monta o executivo da semana num comando."}],
    "fonte": {"titulo": "sua fonte de dados", "sub": "Conecte uma planilha ou um objetivo pra o time começar a enxergar."},
}


_DEC = json.JSONDecoder()


def _extrair_json(texto):
    """Primeiro objeto JSON válido do texto (o Claude às vezes embrulha em prosa).
    Usa raw_decode, que respeita strings e escapes. Contar chaves na mão quebrava
    quando o modelo escrevia um } dentro de um valor de texto, e caía no fallback."""
    i = 0
    while True:
        i = texto.find("{", i)
        if i < 0:
            return None
        try:
            obj, _ = _DEC.raw_decode(texto[i:])
            return obj
        except json.JSONDecodeError:
            i += 1


def _sem_traves(s):
    """Mata travessão (vício de IA banido no projeto): vira vírgula. O prompt sozinho
    vaza travessão na prosa e no que fica gravado no CLAUDE.md do comprador, então
    limpo a saída também."""
    return re.sub(r"\s*[—–―]\s*", ", ", str(s or ""))


def _sem_canon(s):
    """Mata 'canon'/'canônico' (jargão de produção banido em material que o comprador
    vê). O comprador abre o `.claude/agents/*.md` e o `CLAUDE.md`, então esses termos
    não podem vazar. Substitui pelo sentido neutro."""
    s = re.sub(r"(?i)can[oô]nic[oa]s?", "de referência", str(s or ""))
    return re.sub(r"(?i)\bcanons?\b", "padrão", s)


def _scrub(obj):
    """Aplica _sem_traves + _sem_canon recursivamente em toda string do objeto (defesa
    em profundidade: o prompt sozinho vaza esses vícios, então limpo a saída também)."""
    if isinstance(obj, str):
        return _sem_canon(_sem_traves(obj))
    if isinstance(obj, list):
        return [_scrub(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _scrub(v) for k, v in obj.items()}
    return obj


def _normalizar(obj, historico):
    """Traduz a resposta do Claude pro contrato do front, com defaults seguros.
    Tolerante a variação de esquema (o modelo às vezes larga o campo 'acao' ou manda
    a recomendação solta no topo em vez de embrulhada): reconhece pergunta e montagem
    pela forma, não só pelo 'acao'."""
    if not isinstance(obj, dict):
        return _fallback(historico)
    # tolera drift de nome de chave que o modelo às vezes inventa
    if "pergunta" not in obj:
        for k in ("next_question", "question", "proxima_pergunta"):
            if obj.get(k):
                obj["pergunta"] = obj[k]
                break
    reco = obj.get("recomendacao") if isinstance(obj.get("recomendacao"), dict) else None
    if reco is None and isinstance(obj.get("recommendation"), dict):
        reco = obj["recommendation"]
    if reco is None and (obj.get("agentes") or obj.get("times") or obj.get("entendi")):
        reco = obj  # veio solta no topo, sem 'recomendacao'
    # PERGUNTAR: tem pergunta e claramente não é uma montagem
    if obj.get("pergunta") and reco is None and obj.get("acao") != "montar":
        cand = obj.get("candidato")
        cand = _scrub(cand) if isinstance(cand, dict) and cand.get("nome") else None
        return {"done": False, "pergunta": _sem_traves(obj["pergunta"]), "candidato": cand}
    # MONTAR: 'acao' explícito OU veio uma recomendação (embrulhada ou solta)
    if obj.get("acao") == "montar" or reco is not None:
        r = _scrub(reco or {})
        r.setdefault("entendi", [])
        if not r.get("agentes") and r.get("times"):  # aceita o nome antigo 'times'
            r["agentes"] = r.pop("times")
        r.setdefault("agentes", [])
        r.setdefault("skills", [])
        r.setdefault("fonte", {"titulo": "sua realidade", "sub": ""})
        for a in r["agentes"]:  # garante slug estável em cada agente
            if isinstance(a, dict):
                a["slug"] = _slug(a.get("slug") or a.get("nome"))
        for s in r["skills"]:
            if isinstance(s, dict):
                s["slug"] = _slug(s.get("slug") or s.get("cmd") or s.get("nome"))
        _garantir_ds(r)  # o agente de Design System é obrigatório em todo OS
        return {"done": True, "recomendacao": r}
    return _fallback(historico)


def _fallback(historico):
    """Sem Claude ou erro: conduz uma entrevista base determinística, depois monta."""
    perguntas_feitas = sum(1 for m in historico if m.get("role") == "x")
    if perguntas_feitas < len(_FALLBACK_PERGUNTAS):
        return {"done": False, "pergunta": _FALLBACK_PERGUNTAS[perguntas_feitas], "candidato": None}
    return {"done": True, "recomendacao": _garantir_ds(json.loads(json.dumps(_FALLBACK_RECO)))}


def _montar_prompt(historico):
    """Renderiza a conversa como texto pra um turno headless do Claude Code."""
    linhas = ["Conversa até agora (X = você, o entrevistador; Comprador = quem acabou "
              "de instalar o OS):", ""]
    tem = False
    for m in historico:
        quem = "X" if m.get("role") == "x" else "Comprador"
        txt = str(m.get("texto", "")).strip()
        if txt:
            linhas.append(f"{quem}: {txt}")
            tem = True
    if not tem:
        linhas.append("(a conversa ainda não começou: faça a PRIMEIRA pergunta)")
    linhas += ["",
        "Sua vez. Responda com UM objeto JSON e NADA além dele (sem crase, sem texto "
        "fora). Não use ferramentas, não leia arquivos. Use EXATAMENTE um destes dois "
        "formatos, com ESTAS chaves. NÃO invente chaves (nada de next_question, "
        "reasoning, phase, campo, tipo):",
        "",
        'Pra continuar a entrevista: {"acao":"perguntar","pergunta":"<pergunta curta, '
        'UMA frase, sem saudação>","candidato":{"ic":"<emoji>","nome":"<um especialista '
        'sob medida>","papel":"<o que ele faz>"}}  (candidato pode ser null)',
        "",
        'Pra fechar (só depois de 4 a 6 perguntas boas): {"acao":"montar","recomendacao":'
        '{"entendi":["<3-4 frases do que você entendeu>"],"agentes":[{"slug":"<kebab>",'
        '"nome":"<nome do especialista>","ic":"<emoji>","tag":"Essencial|Recomendado|'
        'Opcional","por":"<por que esse especialista>"}],"skills":[{"slug":"<kebab>",'
        '"nome":"<nome>","ic":"<emoji>","cmd":"/<comando>","desc":"<o que faz>"}],'
        '"fonte":{"titulo":"<a fonte a conectar>","sub":"<orientação>"}}}',
        "",
        "Os agentes são especialistas SOB MEDIDA que você inventa pro caso (papel claro, "
        "slug em kebab-case), não celebridades. As skills são automações NOVAS a criar "
        "(invente /comandos como /relatorio, /post), nunca comandos que já existem. "
        "Recomende de 3 a 5 agentes e 2 a 4 skills."]
    return "\n".join(linhas)


def _claude_cli(prompt, system):
    """O cérebro do produto: roda um turno pelo Claude Code do COMPRADOR (a assinatura
    dele, R$ 0, sem chave paga), headless via `claude -p`. Devolve o texto do modelo,
    ou None se o CLI não existe / falha (aí o passo cai no próximo cérebro)."""
    exe = shutil.which("claude")
    if not exe:
        return None
    import tempfile
    try:
        proc = subprocess.run(
            # --system-prompt (override total, persona limpa de entrevistador, sem o
            # prompt de agente-de-código por baixo) + --tools "" (só conversa, sem ler
            # arquivo do repo do comprador). cwd neutro pra não puxar CLAUDE.md nenhum.
            # SEM --bare: --bare forçaria ANTHROPIC_API_KEY e mataria a assinatura.
            [exe, "-p", "--output-format", "json", "--system-prompt", system, "--tools", ""],
            input=prompt, capture_output=True, text=True,
            encoding="utf-8", errors="ignore", timeout=180,
            cwd=tempfile.gettempdir())
    except Exception:
        return None
    if proc.returncode != 0 or not (proc.stdout or "").strip():
        return None
    try:
        env = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None
    if env.get("is_error"):
        return None
    return env.get("result") or ""


def passo(historico):
    """Um passo da entrevista. `historico` = lista [{role:'x'|'voce', texto}].
    Cérebro: o Claude Code do COMPRADOR (na assinatura dele, R$ 0, via `claude -p`). Se o
    `claude` não estiver disponível, cai numa entrevista determinística, pra nunca travar."""
    historico = historico or []

    # a PRIMEIRA pergunta é FIXA: curta, aberta, acolhedora, sem assumir que a pessoa tem
    # negócio ou vende algo. Deixado pro modelo, ele abre com "qual seu negócio, o que você
    # vende", que exclui quem não vende (funcionário, analista, estudante). Do 2º turno em
    # diante o modelo conduz, adaptando pelas respostas.
    if not any(m.get("role") == "voce" for m in historico):
        return {"done": False,
                "pergunta": "Pra começar simples: o que você faz no dia a dia?",
                "candidato": None}

    system = _SYSTEM
    # o Claude Code do comprador conduz a entrevista, na assinatura dele
    prompt = _montar_prompt(historico)
    texto = _claude_cli(prompt, system)
    if texto is not None:
        obj = _extrair_json(texto)
        if obj is None:  # embrulhou/cortou: re-pede enxuto uma vez antes de degradar
            texto = _claude_cli(
                prompt + "\n\nResponda SÓ com o JSON, completo, começando em '{' e "
                "terminando em '}'.", system)
            obj = _extrair_json(texto or "")
        return _normalizar(obj, historico)

    # sem o Claude Code disponível: entrevista determinística (nunca trava)
    return _fallback(historico)


# --- Instalação: materializa o OS do comprador (pasta mãe + subpastas = um mini OS) ---

# Agente de Design System: OBRIGATÓRIO em todo OS (decisão founder). Extrai + cria.
_DS_AGENTE_MD = """---
name: design-system
description: >-
  Use SEMPRE que o OS for gerar ou revisar qualquer coisa visual (dashboard, landing
  page, slide, carrossel, app, mockup, relatório). Extrai o design system de uma
  referência (HTML, URL, imagem) e cria/mantém o design system do OS, pra todo
  entregável sair coeso.
---

# Design System, extrator + criador (agente obrigatório do OS)

Você é o guardião do design system deste OS. Duas missões, sempre:

## 1. EXTRAIR
Dada uma referência (um HTML, uma URL, um print, um site que a pessoa admira), extraia
o design system dela: tokens de cor (hex exatos), tipografia (famílias, escala, pesos),
espaçamento, radius, sombras, e os componentes/padrões estruturais. Nunca chute cor:
leia a referência e tire o valor real.

## 2. CRIAR e MANTER
Crie e mantenha o design system deste OS num arquivo de referência. Todo entregável visual
do OS ancora nos tokens desse DS. Se falta um componente, crie seguindo os tokens
existentes (paleta, radius, sombras); nunca invente cor nova nem gradient fora da paleta.

## Regras
- Um DS é ~20% tokens e ~80% padrões que vivem juntos. Leia os padrões, não só os tokens.
- Antes de dar um entregável como pronto, confira contra o DS: cores, tipografia,
  espaçamento, coerência entre páginas.
- Extraiu de uma referência? Registre a origem. Criou do zero? Documente as decisões.

Consistência visual é o que separa output profissional de amador. Por isso este agente
é obrigatório em qualquer OS.
"""

_RE_FM = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)


def _sem_html(s):
    return re.sub(r"<[^>]+>", "", str(s or "")).strip()


def _slug(s):
    # tira acento (NFKD) ANTES de slugar, pra o slug do agente ficar estável e casar
    # com o nome do arquivo no disco ('André' vira andre) em qualquer sistema de arquivos.
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-") or "agente"


def _garantir_ds(reco):
    """Enforce: todo OS SEMPRE tem o agente de Design System (obrigatório, founder).
    Injeta na lista de agentes se não estiver lá, e recalcula os números."""
    ags = reco.setdefault("agentes", [])
    if not any(_slug(a.get("slug") or a.get("nome")) == "design-system"
               for a in ags if isinstance(a, dict)):
        ags.append({"slug": "design-system", "nome": "Design System", "ic": "🎨",
                    "tag": "Obrigatório",
                    "por": "Todo OS precisa de consistência visual. Esse agente <b>extrai</b> o design system de uma referência e <b>cria/mantém</b> o seu, pra todo entregável sair coeso."})
    nums = reco.setdefault("nums", {})
    nums["agentes"] = len(ags)
    nums["skills"] = len(reco.get("skills") or [])
    return reco


def _subagent_md(nome_id, description, body):
    desc = " ".join(str(description).split())  # 1 linha, sem quebrar o YAML
    return f"---\nname: {nome_id}\ndescription: >-\n  {desc}\n---\n\n{body.strip()}\n"


# ---- Gerador: o Claude Code do comprador PESQUISA e ESCREVE o time do zero ----

def _prompt_gerador(perfil, agentes, skills):
    lista_ag = "\n".join(
        f"- slug `{a.get('slug')}` ({a.get('nome', '')}): {_sem_html(a.get('por', ''))}"
        for a in agentes) or "- (você decide de 3 a 5 especialistas pelo perfil)"
    lista_sk = "\n".join(
        f"- slug `{s.get('slug')}` ({s.get('nome', '')}, comando {s.get('cmd', '')}): {_sem_html(s.get('desc', ''))}"
        for s in skills) or "- (você decide de 2 a 4 automações pelo perfil)"
    return (
        "Você é o motor de criação do OS do comprador. Você PESQUISA na web e ESCREVE, do zero, "
        "os agentes e skills sob medida pra pessoa. Cada um é um especialista real e "
        "funcional, nada genérico de enfeite.\n\n"
        f"PERFIL (da entrevista):\n{perfil}\n\n"
        f"AGENTES a criar (um arquivo por slug, EXATAMENTE estes):\n{lista_ag}\n\n"
        f"SKILLS a criar (um arquivo por slug, EXATAMENTE estas):\n{lista_sk}\n\n"
        "TAREFA:\n"
        "1) PESQUISE na web (WebSearch, de 3 a 6 buscas) substância real do domínio: "
        "frameworks, métodos e boas práticas, com nome e autor.\n"
        "2) Pra CADA agente: frontmatter YAML válido (name = o slug; description de 1 a 2 "
        "frases de quando invocar) e corpo DENSO e FUNCIONAL (papel, método passo a passo, "
        "frameworks reais com fonte, o que fazer e o que evitar). Especialista de verdade.\n"
        "3) Pra CADA skill: frontmatter válido (name = o slug; description) + input, processo "
        "passo a passo (o que o Claude Code executa, com código quando fizer sentido) e "
        "output. Automação que RODA de verdade, não placeholder.\n"
        "4) Português do Brasil com acentos, SEM travessão (o traço longo) em prosa e "
        "SEM as palavras 'canon'/'canônico' (jargão de produção). Não cerque o arquivo "
        "com crase.\n\n"
        "DEVOLVA só os arquivos, cada um num bloco EXATAMENTE assim (marcadores em linha "
        "própria), começando o conteúdo pelo frontmatter ---, e NADA além disso:\n\n"
        "===ARQUIVO:.claude/agents/SLUG.md===\n...\n===FIM===\n\n"
        "===ARQUIVO:.claude/skills/SLUG/SKILL.md===\n...\n===FIM===\n\n"
        "Use os slugs exatos das listas acima."
    )


def _parse_blocos(texto):
    """Extrai os arquivos gerados dos blocos ===ARQUIVO:path=== ... ===FIM===.
    Trava de segurança: só aceita caminhos dentro de .claude/, sem subir de pasta."""
    out = []
    for m in re.finditer(r"===ARQUIVO:(.+?)===\s*\n(.*?)\n===FIM===", texto, re.DOTALL):
        path = m.group(1).strip().lstrip("/").replace("\\", "/")
        body = m.group(2).strip()
        # tira cerca de código que o modelo às vezes envolve o arquivo inteiro (```md ...
        # ```): sem isso o frontmatter não fica no topo e o Claude Code não carrega o agente
        body = re.sub(r"^```[a-zA-Z]*\s*\n", "", body)
        body = re.sub(r"\n```\s*$", "", body).strip()
        if not (body and path.startswith(".claude/") and ".." not in path):
            continue
        # skill: o arquivo TEM que se chamar SKILL.md (o Claude Code exige), mas o modelo
        # às vezes nomeia <slug>.md. Normaliza qualquer .md dentro de skills/<slug>/.
        ms = re.match(r"(\.claude/skills/[^/]+)/[^/]+\.md$", path)
        if ms:
            path = ms.group(1) + "/SKILL.md"
        out.append((path, body))
    return out


def _slugs_de(blocos):
    """Slugs de agente e de skill presentes nos blocos gerados (pra medir completude)."""
    ag, sk = set(), set()
    for rel, _ in blocos:
        m = re.match(r"\.claude/agents/(.+)\.md$", rel)
        if m:
            ag.add(m.group(1))
        ms = re.match(r"\.claude/skills/([^/]+)/", rel)
        if ms:
            sk.add(ms.group(1))
    return ag, sk


def _gerar_rodada(exe, prompt):
    """Uma rodada de geração via Claude Code do comprador (WebSearch/WebFetch). cwd
    neutro (tempdir) pra a geração NÃO herdar o CLAUDE.md 'não montado' do repo do
    comprador (que manda rodar /config-os primeiro), igual a entrevista faz."""
    import tempfile
    try:
        proc = subprocess.run(
            [exe, "-p", "--allowedTools", "WebSearch WebFetch", "--output-format", "json"],
            input=prompt, capture_output=True, text=True,
            encoding="utf-8", errors="ignore", timeout=600,
            cwd=tempfile.gettempdir())
    except Exception:
        return []
    if proc.returncode != 0 or not (proc.stdout or "").strip():
        return []
    try:
        env = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return []
    if env.get("is_error"):
        return []
    return _parse_blocos(env.get("result") or "")


def gerar_time(reco):
    """A montagem de verdade: o Claude Code do COMPRADOR pesquisa na web e ESCREVE o time
    (agentes + skills) do zero, sob medida. Devolve [(caminho_rel, conteudo)]. [] se o CLI
    não existe ou falha (aí instalar cai nos esboços válidos da entrevista)."""
    exe = shutil.which("claude")
    if not exe:
        return []
    perfil = "\n".join(f"- {_sem_html(e)}" for e in (reco.get("entendi") or [])) or "(sem perfil)"
    agentes = [a for a in (reco.get("agentes") or []) if isinstance(a, dict)
               and _slug(a.get("slug") or a.get("nome")) != "design-system"]
    skills = [s for s in (reco.get("skills") or []) if isinstance(s, dict)]
    blocos = _gerar_rodada(exe, _prompt_gerador(perfil, agentes, skills))
    if not blocos:
        return []
    # completude: se a resposta cortou e faltou algum slug pedido, re-pede SÓ os que
    # faltaram (uma vez), pra o time entregue bater com o que o reveal prometeu.
    req_ag = {_slug(a.get("slug") or a.get("nome")) for a in agentes}
    req_sk = {_slug(s.get("slug") or s.get("cmd") or s.get("nome")) for s in skills}
    tem_ag, tem_sk = _slugs_de(blocos)
    falta_ag = [a for a in agentes if _slug(a.get("slug") or a.get("nome")) not in tem_ag]
    falta_sk = [s for s in skills if _slug(s.get("slug") or s.get("cmd") or s.get("nome")) not in tem_sk]
    if falta_ag or falta_sk:
        extra = _gerar_rodada(exe, _prompt_gerador(perfil, falta_ag, falta_sk))
        vistos = {rel for rel, _ in blocos}
        blocos += [(rel, body) for rel, body in extra if rel not in vistos]
    return blocos


def _ler_fm(path):
    """Lê (name, description) do frontmatter de um .md. Trata description folded (>-)."""
    try:
        txt = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return "", ""
    m = _RE_FM.match(txt)
    if not m:
        return "", ""
    fm = m.group(1)
    nm = re.search(r"^name:\s*(.+?)\s*$", fm, re.MULTILINE)
    name = nm.group(1).strip().strip('"') if nm else ""
    dm = re.search(r"^description:\s*(.*?)\s*$", fm, re.MULTILINE)
    desc = dm.group(1).strip() if dm else ""
    if desc in (">-", ">", "|", "|-", ""):  # bloco: junta as linhas indentadas seguintes
        linhas = fm.splitlines()
        for i, ln in enumerate(linhas):
            if ln.startswith("description:"):
                buf = []
                for nxt in linhas[i + 1:]:
                    if re.match(r"^\s+\S", nxt):
                        buf.append(nxt.strip())
                    else:
                        break
                desc = " ".join(buf).strip()
                break
    return name, desc.strip('"')


def _corta(s, n=130):
    s = _sem_html(s)
    return (s[:n - 3].rstrip() + "...") if len(s) > n else s


def _claude_md(reco, base):
    """O CLAUDE.md do OS: o arquivo que o Claude Code LÊ toda sessão. É o recheio VIVO.
    O time e as skills são LIDOS do disco (o que foi de fato gerado/instalado), pra o
    CLAUDE.md nunca prometer um agente que não existe."""
    entendi = reco.get("entendi", []) or []
    fonte = reco.get("fonte", {}) or {}
    agents_dir = base / ".claude" / "agents"
    skills_dir = base / ".claude" / "skills"
    L = ["# Meu OS", "",
         "Sistema operacional pessoal montado pelo Genesis Studio. Este arquivo",
         "é lido pelo Claude Code em TODA sessão: é o que faz o seu time entender VOCÊ.", "",
         "## Quem sou eu", "", "Detalhe em `contexto/perfil.md`. Resumo:"]
    L += [f"- {_sem_html(e)}" for e in entendi]
    L += ["", "## Meu time (subagents reais em `.claude/agents/`)", "",
          "Delegue pra eles quando a tarefa pedir a especialidade de cada um:"]
    ds_line = None
    for p in sorted(agents_dir.glob("*.md")):
        nome, desc = _ler_fm(p)
        if p.stem == "design-system":
            ds_line = f"- `design-system`: **OBRIGATÓRIO**. {_corta(desc) or 'Extrai o design system de uma referência e cria/mantém o do OS.'}"
        else:
            L.append(f"- `{p.stem}`: {_corta(desc) or nome or p.stem}")
    L.append(ds_line or "- `design-system`: **OBRIGATÓRIO**. Extrai o design system de uma referência e cria/mantém o do OS.")
    L += ["", "## Minhas skills (`.claude/skills/`)", ""]
    sk = []
    for d in sorted(x for x in skills_dir.glob("*") if x.is_dir()):
        nome, desc = _ler_fm(d / "SKILL.md") if (d / "SKILL.md").exists() else ("", "")
        sk.append(f"- `/{d.name}`: {_corta(desc) or nome or d.name}")
    L += sk or ["(nenhuma ainda)"]
    L += ["", "## Minha fonte de dados", "",
          f"**{_sem_html(fonte.get('titulo', 'sua fonte'))}**: {_sem_html(fonte.get('sub', ''))} "
          "(detalhe em `contexto/fonte.md`)", "",
          "## Como meu OS trabalha", "",
          "- Português do Brasil, direto e honesto. Nunca invente número ou dado que você não tem.",
          "- As entregas do time caem em `producao/`.",
          "- Consistência visual é inegociável: todo entregável visual passa pelo agente `design-system`.", ""]
    return "\n".join(L)


# Guarda-corpo do OS: o PostToolUse hook grava o pulso (quem o comprador delega, o quê),
# pra o painel mostrar o time VIVO de verdade, não teatro. cwd do hook = raiz do repo, e
# `atividade_hook.py` resolve o caminho por CLAUDE_PROJECT_DIR/cwd (sem depender de shell).
_SETTINGS = {
    "hooks": {
        "PostToolUse": [
            {"matcher": "Task",
             "hooks": [{"type": "command",
                        "command": "python .genesis/atividade_hook.py"}]}
        ]
    }
}


def _ler_gerados(base):
    """Manifesto do que O GENESIS gerou na última instalação (slugs de agente e skill).
    É a chave pra reinstalar preservando o que o comprador escreveu à mão."""
    try:
        d = json.loads((base / ".claude" / ".genesis-gerados.json").read_text(encoding="utf-8"))
        return list(d.get("agentes") or []), list(d.get("skills") or [])
    except Exception:
        return [], []


def _limpar_gerados(base):
    """Reinstalar = apaga SÓ o que o Genesis gerou antes (pelo manifesto), preservando
    agentes/skills autorais do comprador. Sem manifesto (1ª instalação), não apaga nada.
    NUNCA toca producao/ (entregas do comprador)."""
    import shutil as _sh
    ag, sk = _ler_gerados(base)
    for slug in ag:
        p = base / ".claude" / "agents" / f"{slug}.md"
        if p.exists():
            p.unlink()
    for slug in sk:
        d = base / ".claude" / "skills" / slug
        if d.is_dir():
            _sh.rmtree(d, ignore_errors=True)


def instalar(reco, base):
    """Materializa o OS do comprador em `base` (a pasta MÃE), a estrutura do OS:
    - `.claude/agents/` — o TIME como SUBAGENTS REAIS do Claude Code (invocáveis), escritos
      sob medida pelo Claude Code do comprador + o `design-system` OBRIGATÓRIO (extrai + cria).
    - `.claude/settings.json` — o guarda-corpo: o hook que grava o pulso do time pro painel.
    - `contexto/` — quem o comprador é (o recheio) + a fonte a conectar.
    - `.claude/skills/` — as skills sob medida.
    - `producao/` — onde as entregas do time caem.
    - `meu-os.json` — o manifesto do reveal. Idempotente. base = raiz do repo do comprador."""
    from pathlib import Path as _P
    base = _P(base)
    reco = _scrub(reco) if isinstance(reco, dict) else {}  # travessão/canon fora do que grava
    _garantir_ds(reco)  # DS obrigatório ANTES de materializar
    for sub in ("contexto", "producao", ".claude/agents", ".claude/skills"):
        (base / sub).mkdir(parents=True, exist_ok=True)
    agents_dir = base / ".claude" / "agents"
    skills_dir = base / ".claude" / "skills"
    # re-instalar (refazer a entrevista): apaga SÓ o que o Genesis gerou antes (manifesto),
    # preservando agentes/skills que o comprador escreveu à mão. NUNCA toca producao/.
    _limpar_gerados(base)
    agentes = reco.get("agentes", []) or []
    skills = reco.get("skills", []) or []
    entendi = reco.get("entendi", []) or []
    fonte = reco.get("fonte", {}) or {}
    ger_ag, ger_sk = set(), set()  # o que ESTA instalação gerou (vira o manifesto)

    # MONTAGEM: o Claude Code do comprador PESQUISA na web e ESCREVE o time do zero, sob
    # medida (o produto). Fallback: sem CLI (ou geração falha), escreve esboços VÁLIDOS
    # dos agentes/skills recomendados, pra nunca travar o onboarding.
    gerados = gerar_time(reco)
    if gerados:
        for rel, body in gerados:
            fp = base / rel
            fp.parent.mkdir(parents=True, exist_ok=True)
            fp.write_text(_sem_canon(_sem_traves(body)).rstrip() + "\n", encoding="utf-8")
            m = re.match(r"\.claude/agents/(.+)\.md$", rel)
            if m:
                ger_ag.add(m.group(1))
            ms = re.match(r"\.claude/skills/([^/]+)/", rel)
            if ms:
                ger_sk.add(ms.group(1))
    else:
        for a in agentes:
            slug = _slug(a.get("slug") or a.get("nome"))
            if slug == "design-system":
                continue
            (agents_dir / f"{slug}.md").write_text(_subagent_md(
                slug, _sem_html(a.get("por")) or f"{a.get('nome', 'Especialista')} do seu time.",
                f"# {a.get('nome', slug)}\n\nVocê é {a.get('nome', slug)}, especialista do seu OS. "
                f"{_sem_html(a.get('por', ''))}\n\nRode o Genesis com o Claude Code pra me deixar "
                "completo, com pesquisa e método a fundo."), encoding="utf-8")
            ger_ag.add(slug)
        for s in skills:
            slug = _slug(s.get("slug") or s.get("cmd") or s.get("nome"))
            d = skills_dir / slug
            d.mkdir(parents=True, exist_ok=True)
            (d / "SKILL.md").write_text(_subagent_md(
                slug, _sem_html(s.get("desc")) or f"{s.get('nome', 'skill')}.",
                f"# {s.get('nome', slug)}\n\n{_sem_html(s.get('desc', ''))}\n\n"
                "> Esboço da entrevista. Rode o Genesis com o Claude Code pra gerar a automação completa."),
                encoding="utf-8")
            ger_sk.add(slug)
    # cinto de segurança: o design-system existe SEMPRE, gerado ou não (scrub por garantia)
    if not (agents_dir / "design-system.md").exists():
        (agents_dir / "design-system.md").write_text(
            _sem_canon(_sem_traves(_DS_AGENTE_MD)), encoding="utf-8")
    ger_ag.add("design-system")

    # guarda-corpo: o hook do pulso (o painel só fica vivo de verdade com isto materializado)
    (base / ".claude" / "settings.json").write_text(
        json.dumps(_SETTINGS, ensure_ascii=False, indent=2), encoding="utf-8")
    # manifesto do que foi gerado, pra o próximo reinstall preservar o autoral
    (base / ".claude" / ".genesis-gerados.json").write_text(
        json.dumps({"agentes": sorted(ger_ag), "skills": sorted(ger_sk)},
                   ensure_ascii=False, indent=2), encoding="utf-8")

    # agora que o time está no disco, o CLAUDE.md e o README refletem o que EXISTE de fato
    (base / "CLAUDE.md").write_text(_claude_md(reco, base), encoding="utf-8")
    (base / "meu-os.json").write_text(json.dumps(reco, ensure_ascii=False, indent=2), encoding="utf-8")
    n_agentes = len(list(agents_dir.glob("*.md")))
    n_skills = len([x for x in skills_dir.glob("*") if x.is_dir()])
    (base / "README.md").write_text(
        "# Meu OS\n\nGerado pelo Genesis Studio. "
        f"{n_agentes} agentes, {n_skills} skills, feitos sob medida pra você.\n\n"
        "Estrutura do seu OS:\n"
        "- `.claude/agents/`: **o seu time, como subagents reais do Claude Code** (invocáveis)\n"
        "- `contexto/`: quem você é (o recheio: seu time entende VOCÊ)\n"
        "- `producao/`: onde as entregas do seu time caem\n"
        "- `.claude/skills/`: suas skills sob medida\n"
        "- `meu-os.json`: o manifesto do OS\n\n"
        "O agente `design-system` é obrigatório: garante que todo entregável visual saia coeso.\n",
        encoding="utf-8")

    # contexto/perfil.md — o RECHEIO
    (base / "contexto" / "perfil.md").write_text(
        "# Quem sou eu\n\n" + "\n".join(f"- {_sem_html(e)}" for e in entendi) +
        "\n\n> Este é o recheio do seu OS: é o que faz seu time entender VOCÊ. Edite à vontade.\n",
        encoding="utf-8")
    # contexto/fonte.md — a realidade a conectar
    (base / "contexto" / "fonte.md").write_text(
        "# Minha fonte de dados\n\n**" + _sem_html(fonte.get("titulo", "sua fonte")) + "**\n\n" +
        _sem_html(fonte.get("sub", "")) +
        "\n\n> Conecte aqui o que seu time deve enxergar. Sem isso, é um time bonito parado.\n",
        encoding="utf-8")

    (base / "producao" / ".gitkeep").write_text("", encoding="utf-8")
    return base


# --- Painel (VISUALIZAR): o OS do comprador como agência viva -------------------

def _atividade(base, agentes):
    """Lê o pulso do Claude Code do comprador (o hook grava `.genesis-atividade.jsonl`,
    uma linha JSON por evento: {ts, agente(slug), acao}). Marca quem está vivo (agiu nos
    últimos 2,5min) e monta o feed. Sem o arquivo, o painel fica em repouso."""
    f = base / ".genesis-atividade.jsonl"
    if not f.exists():
        return False, []
    slugs = {a["slug"] for a in agentes}
    nomes = {a["slug"]: a["nome"] for a in agentes}
    agora = time.time()
    eventos, vivos = [], set()
    try:
        linhas = f.read_text(encoding="utf-8", errors="ignore").splitlines()[-40:]
    except Exception:
        return False, []
    for ln in linhas:
        try:
            e = json.loads(ln)
        except Exception:
            continue
        ag = str(e.get("agente", ""))
        ts = e.get("ts", 0) or 0
        dt = agora - ts
        quando = "agora" if dt < 60 else (f"{int(dt / 60)}min" if dt < 3600 else f"{int(dt / 3600)}h")
        eventos.append({"agente": nomes.get(ag, ag), "acao": str(e.get("acao", "")), "quando": quando, "_ts": ts})
        if dt <= 150 and ag in slugs:
            vivos.add(ag)
    eventos = sorted(eventos, key=lambda x: -x["_ts"])[:10]
    for a in agentes:
        a["live"] = a["slug"] in vivos
        if a["live"]:
            r = next((e for e in eventos if e["agente"] == a["nome"]), None)
            if r:
                a["fazendo"] = r["acao"]
    for e in eventos:
        e.pop("_ts", None)
    return (len(vivos) > 0), eventos


def painel_dados(base):
    """Snapshot do OS do comprador pro /api/painel: o time REAL lido do disco (o que a
    entrevista gerou, nada inventado) + o pulso vivo do Claude Code dele."""
    base = Path(base)
    reco = {}
    mj = base / "meu-os.json"
    if mj.exists():
        try:
            reco = json.loads(mj.read_text(encoding="utf-8"))
        except Exception:
            reco = {}
    reco_ag = {a.get("slug"): a for a in (reco.get("agentes") or []) if isinstance(a, dict)}
    agentes = []
    adir = base / ".claude" / "agents"
    if adir.is_dir():
        for p in sorted(adir.glob("*.md")):
            r = reco_ag.get(p.stem, {})
            nome, desc = _ler_fm(p)
            agentes.append({"slug": p.stem, "nome": r.get("nome") or nome or p.stem,
                            "ic": r.get("ic") or "•",
                            "desc": desc or _sem_html(r.get("por", "")), "live": False})
    skills = []
    sdir = base / ".claude" / "skills"
    if sdir.is_dir():
        for d in sorted(x for x in sdir.glob("*") if x.is_dir()):
            r = next((s for s in (reco.get("skills") or [])
                      if _slug(s.get("slug") or s.get("cmd") or s.get("nome")) == d.name), {})
            nome, desc = _ler_fm(d / "SKILL.md") if (d / "SKILL.md").exists() else ("", "")
            skills.append({"slug": d.name, "nome": r.get("nome") or nome or d.name,
                           "ic": r.get("ic") or "⚡", "cmd": r.get("cmd") or ("/" + d.name),
                           "desc": desc or _sem_html(r.get("desc", ""))})
    ativo, pulso = _atividade(base, agentes)
    entendi = reco.get("entendi") or []
    return {"perfil": {"nome": (_sem_html(entendi[0])[:60] if entendi else ""), "resumo": entendi},
            "agentes": agentes, "skills": skills, "fonte": reco.get("fonte") or {},
            "pulso": pulso, "ativo": ativo}
