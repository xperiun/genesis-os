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
import os
import re
import shutil
import subprocess
import time
import unicodedata
from pathlib import Path

# ---- Modelo: quem paga a conta é a ASSINATURA do comprador, então ele escolhe -------------
# Sem isto o `claude -p` herda o default da máquina dele, e o mesmo produto consome de um
# jeito num Max e de outro num Pro, sem ninguém enxergar. Pior: o Opus tem cota PRÓPRIA e
# separada da janela de 5h (documentado), então num Pro ele acaba primeiro, a montagem falha
# e o comprador cai no time de esboço.
#
# Vazio = herda o default do comprador (o que a máquina dele já usa).
# "sonnet" = previsível e cabe no Pro. "opus" = mais fundo, mas cota apertada.
# Ver a tabela de escolha no ../docs/MODELO.md (números medidos, não chute).
MODELO = (os.environ.get("GENESIS_MODELO") or "").strip()

# O modelo que o `claude -p` do comprador DE FATO usou no último turno, lido do `modelUsage`
# do envelope. É de graça (já vem em toda resposta) e é o que permite avisar só quem precisa:
# se a entrevista rodou em Opus, o reveal oferece trocar antes da montagem, em vez de
# perguntar o plano pra todo mundo. Processo único e local: um servidor, um comprador.
_ULTIMO_MODELO = ""


def _flags_modelo(override=None):
    """Os flags de modelo pro `claude -p`. Precedência: escolha do comprador na cena
    (override) > GENESIS_MODELO > vazio (herda o default da máquina dele)."""
    m = (override or MODELO or "").strip()
    return ["--model", m] if m else []


def _env_assinatura():
    """Ambiente pros subprocessos `claude`: TUDO do processo MENOS as chaves de API. Com
    `ANTHROPIC_API_KEY` no env, o Claude Code cobra a API em vez do login OAuth do
    comprador, e a promessa 'R$ 0, roda na sua assinatura' vira mentira silenciosa numa
    máquina que tenha a chave setada (caso comum: dev que usa a API pra outra coisa)."""
    return {k: v for k, v in os.environ.items()
            if k not in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")}


def ultimo_modelo():
    """O modelo do último turno da entrevista (ex: 'claude-opus-4-8[1m]'). '' se ainda não
    rodou nenhum (a 1ª pergunta é fixa e não chama o CLI)."""
    return _ULTIMO_MODELO

_SYSTEM = """Você é o X, o entrevistador de onboarding do OS do comprador. Sua missão nesta
conversa: CONHECER a pessoa que acabou de instalar o OS dela e, no fim, PROJETAR o time
de IA sob medida pra ela: especialistas feitos pro caso dela + skills que valha criar.

Quem responde é o COMPRADOR (não é o dono do produto). Pode ser um analista de dados (vá
mais fundo, técnico), um profissional de qualquer área (dentista, advogado, gestor) ou
alguém que veio só aprender IA/Claude (guie, sem jargão). A PRIMEIRA resposta calibra:
ajuste profundidade e linguagem.

Tom: direto, caloroso, brasileiro, afiado. Zero corporativês. Perguntas CURTAS, UMA de
cada vez (nunca empilhe várias numa frase). Nada de "Ótima pergunta"/"Perfeito"/"Vamos lá".

PERGUNTA OBJETIVA COM OPÇÕES (regra de ouro): sempre que a pergunta admitir alternativas
prováveis, mande junto o campo "opcoes" com 2 a 4 respostas prontas, curtas e CONCRETAS
(nunca rótulo seco: "planilha no Google Sheets" em vez de "planilha"). A pessoa clica em
vez de redigir, e a entrevista anda 10x mais rápido. Ela sempre pode digitar outra coisa,
então as opções não precisam cobrir tudo, só os casos prováveis. Pergunta realmente
aberta (ex: a dor principal), mande sem "opcoes".

A PRIMEIRA pergunta é curta, aberta e acolhedora, e NÃO assume que a pessoa tem negócio ou
vende algo (ela pode ser funcionária, autônoma, estudante). Abra simples pelo que ela faz,
tipo "Pra começar, me conta: o que você faz no dia a dia?". Depois vá fundo pelas respostas.

QUANDO VIER UM DOSSIÊ (o material que a pessoa conectou: docs do negócio, o site dela, o
contexto importado do Claude Code dela), a regra muda e é INVIOLÁVEL: você JÁ SABE quem ela
é. NUNCA pergunte o que está escrito lá. Perguntar "o que você faz?" pra quem acabou de te
entregar o site e os documentos do negócio é o jeito mais rápido de parecer burro e queimar
a experiência.
- Sua PRIMEIRA fala então NÃO é uma pergunta de identificação. É uma frase curta mostrando
  que você leu (nomeie o negócio, a área, o que ela vende) e emenda direto na pergunta que
  o dossiê NÃO responde. Ex: "Vi que você toca a <b>Acme</b>, consultoria de RH pra indústria.
  O que mais te consome na semana hoje?"
- Use o dossiê pra pular perguntas e ir MAIS FUNDO, não pra fazer as mesmas. Com dossiê,
  2 a 4 perguntas bastam: o que falta é a DOR, a META e o DADO que ela tem na mão, que é
  o que documento nenhum conta.
- Nunca invente o que não está no dossiê. Leu pouco, pergunte o resto normalmente.

Português do Brasil com TODOS os acentos. NUNCA use travessão (o traço "—") em lugar
nenhum: nem na pergunta, nem em NENHUM campo do JSON (entendi, por, desc, sub). Use
vírgula, ponto ou dois pontos. Travessão em prosa é vício de robô e queima a marca.
NUNCA escreva "canon" nem "canônico" (jargão de produção): use "de referência",
"principal" ou "padrão". O comprador lê isso e não pode parecer bug.

Faça de 3 a 5 perguntas boas (2 a 4 quando tem dossiê), NUNCA mais que isso. A entrevista
é um CHECKLIST de 4 lacunas, e você só pergunta a lacuna que ainda está VAZIA:
(1) o que a pessoa faz e produz, (2) a DOR principal, (3) a META, (4) o DADO/fonte na mão.
O dossiê e as respostas anteriores já preenchem lacunas: preencheu as 4, PARE e MONTE.
NÃO afunde num único assunto (no máximo UMA pergunta de aprofundamento, e só se a resposta
foi vaga). Entrevista longa cansa e queima a experiência. Na dúvida entre perguntar mais
uma ou montar, MONTE.

Os agentes são SOB MEDIDA: você INVENTA os especialistas certos pro caso da pessoa (um
papel claro, não um nome de celebridade). Ex: "Analista de Varejo", "Narrador de Dados",
"Estrategista de LinkedIn". Depois da entrevista, o Claude Code do comprador vai
PESQUISAR na web e ESCREVER cada um a fundo. Você só define QUEM entra e POR QUÊ.

REGRAS DE HONESTIDADE (invioláveis):
- Cada agente é um papel real e útil pro caso dela. Nada genérico de enfeite.
- Skills são automações NOVAS a criar; descreva o payoff concreto.
- Sobre dado: se a pessoa TEM fonte, o "fonte" reflete isso; se NÃO tem, oriente a
  começar simples (uma planilha, um objetivo) sem prometer número que ela não tem.
- O "fonte" é uma fonte de dados REAL e VIVA do mundo dela (uma planilha de vendas, um
  export do CRM/ERP, uma conta de anúncios, uma base que ATUALIZA). NUNCA é um nome de
  arquivo (`empresa.md`, `posicionamento.md`, qualquer `.md`/`.txt`/`.csv` do dossiê que
  você leu): esses são o material que a pessoa te deu pra você entender quem ela é, NÃO a
  fonte que ela conecta. Se você não identificou uma fonte viva clara, o "titulo" é genérico
  e humano ("sua planilha de vendas", "seus números do mês"), nunca um filename.
- Nunca invente resultado, venda ou métrica.
- OBRIGATÓRIO: o time SEMPRE inclui um agente de Design System (slug design-system), que
  extrai o design system de uma referência e cria/mantém o do OS. Consistência visual é
  inegociável, então ele entra sempre, mesmo sem a pessoa pedir.

FORMATO DE RESPOSTA (responda SEMPRE com UM objeto JSON, e NADA além dele):
Pra continuar a entrevista:
{"acao":"perguntar","pergunta":"<sua pergunta curta>","opcoes":["<resposta pronta 1>","<resposta pronta 2>"],"candidato":{"ic":"<emoji>","nome":"<um especialista sob medida que já dá pra intuir>","papel":"<o que ele faz>"}}
("opcoes" é opcional: 2 a 4 respostas prontas e concretas quando a pergunta admite
alternativas prováveis; omita em pergunta realmente aberta.
O "candidato" é opcional: inclua quando já der pra intuir um especialista que serve,
pra ele "se candidatar" no recrutamento. Omita ou null se ainda cedo.
REGRA DURA do candidato: cada candidato é um papel NOVO. NUNCA sugira dois candidatos
pro mesmo papel, mesmo com nome diferente: "Tesoureiro", "Guardião do Caixa" e
"Escriturário" são UM papel só. Se a lista de candidatos já cobre o papel, mande null.)

Pra montar o time no fim:
{"acao":"montar","recomendacao":{
  "entendi":["<3-4 frases curtas do que você entendeu, pode usar <b>negrito</b>>"],
  "agentes":[{"slug":"<kebab-case>","nome":"<nome do especialista>","ic":"<emoji>","tag":"Essencial|Recomendado|Opcional","por":"<1-2 frases: POR QUE esse especialista, amarrado ao que a pessoa disse, pode usar <b>>"}],
  "skills":[{"slug":"<kebab-case>","nome":"<nome curto>","ic":"<emoji>","cmd":"</comando>","desc":"<o que faz + payoff, pode usar <b>>"}],
  "fonte":{"titulo":"<a fonte/realidade a conectar>","sub":"<1-2 frases orientando>"}
}}

Recomende de 3 a 5 agentes e 2 a 4 skills. Priorize o que resolve a dor principal dela.

REGRA DURA anti-sobreposição (o erro mais comum, não repita): cada agente é um papel
DISTINTO, com trabalho próprio que os outros não fazem. NÃO fragmente uma única função em
vários agentes que se sobrepõem. "Arquiteto de Pauta", "Roteirista", "Engenheiro de Hook" e
"Repurposador de Conteúdo" são facetas de UM trabalho só (criar conteúdo): isso é UM agente,
não quatro. Antes de fechar a lista, olhe par a par: se dois agentes dividiriam o mesmo
arquivo/entregável na prática, funda num só, mais denso. Prefira SEMPRE menos agentes fortes a
mais agentes rasos. Com pouco sinal (entrevista curta ou dossiê magro), monte ENXUTO (3-4),
nunca encha de papéis plausíveis pra parecer robusto: time inchado com sobreposição é pior
que time enxuto e nítido, e a pessoa percebe na hora."""


_FALLBACK_PERGUNTAS = [
    "Antes de montar teu time, me conta: o que você faz, e o que mais te consome no trabalho?",
    "Entendi. E o que você produz hoje que, se saísse mais rápido ou melhor, mudaria teu jogo?",
    "Boa. Tem alguma meta pessoal (carreira, presença, um projeto) que um time seu poderia acelerar?",
    "Última: você já tem algum dado na mão (planilha, sistema, números), ou a gente começa do zero?",
]

# Trilhas do fallback: quando o Claude Code do comprador não responde, não dá pra inventar
# especialista sob medida. O mínimo honesto é montar pelo que a pessoa DIGITOU (as palavras
# dela decidem a trilha), em vez do mesmo enlatado pra todo mundo. Cada trilha é (gatilhos,
# agentes, skills). A ordem importa: a primeira que casar entra primeiro.
#
# Gatilho se escreve SEM ACENTO e no SINGULAR: o _casa normaliza o acento dos dois lados e
# aceita o plural sozinho. Escrever "métrica" E "metrica" (como era antes) é convite a
# esquecer uma das duas, e foi o que aconteceu com o plural: a lista tinha "métrica",
# "relatório", "indicador", "vídeo" no singular e nenhum plural, então "acompanho os
# indicadores e relatórios da diretoria" (o jeito que gente de verdade escreve) não casava
# NADA e caía no piso genérico, que é exatamente o que estas trilhas existem pra evitar.
# Plural irregular (carrossel -> carrosseis, funil -> funis) não sai de regra, vai na lista.
_FALLBACK_TRILHAS = [
    (("dado", "bi", "power bi", "dashboard", "sql", "planilha", "excel", "metrica",
      "relatorio", "numero", "indicador", "kpi", "analista"),
     [{"slug": "analista-de-dados", "nome": "Analista de Dados", "ic": "📊", "tag": "Essencial",
       "por": "Você falou de dado. Ele transforma teu número em decisão."},
      {"slug": "narrador-de-dados", "nome": "Narrador de Dados", "ic": "🎬", "tag": "Recomendado",
       "por": "Pra teu dado virar história que decide, não só gráfico bonito."}],
     [{"ic": "⚡", "slug": "relatorio-executivo", "nome": "Relatório executivo",
       "cmd": "/relatorio-executivo", "desc": "Monta o executivo da semana num comando."}]),
    (("conteudo", "post", "instagram", "linkedin", "carrossel", "carrosseis", "video",
      "roteiro", "audiencia", "newsletter", "blog", "social"),
     [{"slug": "estrategista-de-conteudo", "nome": "Estrategista de Conteúdo", "ic": "✍️",
       "tag": "Essencial", "por": "Você falou de conteúdo. Ele transforma teu insight em post na tua voz."}],
     [{"ic": "📱", "slug": "post", "nome": "Post", "cmd": "/post",
       "desc": "Transforma uma ideia solta em post pronto, na tua voz."}]),
    (("venda", "cliente", "proposta", "lead", "comercial", "funil", "funis",
      "orcamento", "fechar", "prospect"),
     [{"slug": "closer", "nome": "Closer", "ic": "🎯", "tag": "Essencial",
       "por": "Você falou de venda. Ele trata objeção e escreve o que fecha."}],
     [{"ic": "📄", "slug": "proposta", "nome": "Proposta", "cmd": "/proposta",
       "desc": "Gera a proposta comercial a partir do briefing do cliente."}]),
]

# Piso do fallback: usado quando nada do que a pessoa digitou casou com uma trilha (ou quando
# ela não digitou nada). Único caso em que o time é genérico de verdade, e a copy assume isso.
_FALLBACK_PISO = {
    "agentes": [
        {"slug": "analista-de-dados", "nome": "Analista de Dados", "ic": "📊", "tag": "Essencial",
         "por": "Pra transformar teu número em decisão."},
        {"slug": "estrategista-de-conteudo", "nome": "Estrategista de Conteúdo", "ic": "✍️",
         "tag": "Recomendado", "por": "Pra teu insight virar conteúdo na tua voz."},
    ],
    "skills": [{"ic": "⚡", "slug": "relatorio-executivo", "nome": "Relatório executivo",
                "cmd": "/relatorio-executivo", "desc": "Monta o executivo da semana num comando."}],
}


# --- Log da montagem: o que o Claude Code faz AO VIVO (buscas na web, arquivos escritos).
# Lido pelo terminal do frontend via /status. Preenchido pelo streaming em _gerar_rodada. ---
_MLOG = []


def _mlog(msg):
    m = _sem_html(str(msg or "")).strip()
    if not m:
        return
    _MLOG.append(m)
    if len(_MLOG) > 160:  # segura só o rabo, o terminal não precisa do histórico todo
        del _MLOG[:-160]


def _mlog_reset():
    _MLOG.clear()


def montagem_log():
    return list(_MLOG)


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
        # opções clicáveis (respostas prontas): valida a forma, limita a 4, scrub em cada uma
        ops = obj.get("opcoes")
        ops = [_scrub(str(o))[:80] for o in ops if str(o or "").strip()][:4] \
            if isinstance(ops, list) else []
        return {"done": False, "pergunta": _sem_traves(obj["pergunta"]),
                "opcoes": ops, "candidato": cand}
    # MONTAR: 'acao' explícito OU veio uma recomendação (embrulhada ou solta)
    if obj.get("acao") == "montar" or reco is not None:
        r = _scrub(reco or {})
        r.setdefault("entendi", [])
        if not r.get("agentes") and r.get("times"):  # aceita o nome antigo 'times'
            r["agentes"] = r.pop("times")
        r.setdefault("agentes", [])
        r.setdefault("skills", [])
        r.setdefault("fonte", {"titulo": "sua realidade", "sub": ""})
        _sanear_fonte(r)  # o titulo/sub da fonte nunca pode ser um nome de arquivo do dossiê
        for a in r["agentes"]:  # garante slug estável em cada agente
            if isinstance(a, dict):
                a["slug"] = _slug(a.get("slug") or a.get("nome"))
        for s in r["skills"]:
            if isinstance(s, dict):
                s["slug"] = _slug(s.get("slug") or s.get("cmd") or s.get("nome"))
        _garantir_ds(r)  # o agente de Design System é obrigatório em todo OS
        return {"done": True, "recomendacao": r}
    return _fallback(historico)


def _sem_acento(s):
    """'métricas' -> 'metricas'. O comprador digita com e sem acento no mesmo texto, então a
    comparação acontece toda num lado só: sem acento, minúsculo."""
    return unicodedata.normalize("NFKD", str(s or "")) \
        .encode("ascii", "ignore").decode("ascii").lower()


def _casa(texto, gatilhos):
    """`texto` já vem por _sem_acento. Casa por PALAVRA INTEIRA (nunca substring: sem o \\b,
    'proposta' casaria o gatilho 'post' e quem fala de proposta comercial ganharia um
    estrategista de conteúdo do nada), aceitando o plural regular do PT-BR: 's' (metrica ->
    metricas) e 'es' (indicador -> indicadores). \\b também funciona pra gatilho de duas
    palavras ('power bi')."""
    return any(re.search(r"\b" + re.escape(g) + r"(?:s|es)?\b", texto) for g in gatilhos)


def _reco_fallback(historico):
    """Time base montado a partir do que a pessoa DIGITOU, não um enlatado igual pra todos.

    Só roda quando o Claude Code do comprador não respondeu (CLI fora do PATH, queda de rede).
    Sem modelo não dá pra inventar especialista sob medida, então a honestidade aqui é: usar
    as palavras dela pra escolher a trilha, ecoar o que ela disse no 'entendi', deixar claro
    que é um time BASE e convidar a refazer. Nunca anunciar a falha como se fosse diagnóstico
    ("o motor não respondeu" no card de 'o que eu entendi de você' é o pior lugar possível)."""
    falas = [_sem_html(m.get("texto", "")) for m in historico
             if m.get("role") == "voce" and str(m.get("texto", "")).strip()]
    texto = _sem_acento(" ".join(falas))   # os gatilhos vivem sem acento: compara num lado só
    agentes, skills, casou = [], [], False
    for gatilhos, ags, sks in _FALLBACK_TRILHAS:
        if _casa(texto, gatilhos):
            casou = True
            agentes += [dict(a) for a in ags]
            skills += [dict(s) for s in sks]
    if not casou:
        agentes = [dict(a) for a in _FALLBACK_PISO["agentes"]]
        skills = [dict(s) for s in _FALLBACK_PISO["skills"]]
    entendi = []
    if falas:
        entendi.append("Você me contou: <b>" + _corta(falas[0], 150) + "</b>")
    entendi.append("Montei um time <b>base</b> a partir disso, pra você já começar. "
                   "Refaça quando quiser: com o time sob medida, cada especialista nasce "
                   "escrito do zero pro seu caso.")
    return {"entendi": entendi, "agentes": agentes[:4], "skills": skills[:3],
            "fonte": {"titulo": "sua fonte de dados",
                      "sub": "Conecte uma planilha, um banco ou um objetivo pra o time começar a enxergar."}}


def _fallback(historico, forcar=False, kb=""):
    """Sem Claude ou erro: conduz uma entrevista base determinística, depois monta pelo que
    a pessoa digitou (ver _reco_fallback). `forcar` = ela apertou "monta agora", então monta
    na hora, sem completar o roteiro de perguntas. `kb` = ela conectou dossiê: pula a
    pergunta de identificação (perguntar "o que você faz?" pra quem entregou os documentos
    do negócio é o que o _SYSTEM proíbe; o fallback não pode violar a mesma regra)."""
    perguntas = _FALLBACK_PERGUNTAS[1:] if (kb or "").strip() else _FALLBACK_PERGUNTAS
    perguntas_feitas = sum(1 for m in historico if m.get("role") == "x")
    if not forcar and perguntas_feitas < len(perguntas):
        return {"done": False, "pergunta": perguntas[perguntas_feitas], "candidato": None}
    return {"done": True, "recomendacao": _garantir_ds(_reco_fallback(historico))}


def _montar_prompt(historico, kb="", forcar=False, candidatos=None):
    """Renderiza a conversa como texto pra um turno headless do Claude Code. `kb` é o dossiê
    que o comprador conectou (contexto/referencia/): com ele, o entrevistador abre JÁ sabendo
    quem é a pessoa, em vez de perguntar o que já está escrito. `forcar` = o comprador apertou
    "monta agora": o teto vira imediato, ele não fica refém do modelo querer perguntar mais.
    `candidatos` = nomes já na fila do recrutamento (o front acumula e devolve): sem esta
    memória, cada turno é um processo novo e o modelo re-sugere o MESMO papel com nome
    diferente (3 variações de tesoureiro na fila, caso real do founder)."""
    tem_kb = bool((kb or "").strip())
    linhas = []
    if tem_kb:
        linhas += [
            "DOSSIÊ DO COMPRADOR (o material que ELE MESMO conectou: documentos do negócio, "
            "o site dele, o contexto importado do Claude Code dele). Você JÁ LEU isto, então "
            "NÃO pergunte nada que esteja aqui. Use pra abrir mostrando que leu e ir direto "
            "no que falta (a dor, a meta, o dado na mão):",
            kb.strip()[:14000],
            "",
            "=" * 60,
            "",
        ]
    nomes_cand = [str(c or "").strip() for c in (candidatos or []) if str(c or "").strip()]
    if nomes_cand:
        linhas += [
            "CANDIDATOS JÁ NA FILA do recrutamento (você já sugeriu): "
            + "; ".join(nomes_cand[:12]) + ". NÃO repita nenhum deles nem crie variação do "
            "mesmo papel com outro nome. Candidato novo SÓ se for um papel claramente "
            "DIFERENTE dos listados; senão, mande candidato null.",
            "",
        ]
    linhas += ["Conversa até agora (X = você, o entrevistador; Comprador = quem acabou "
               "de instalar o OS):", ""]
    tem = False
    for m in historico:
        quem = "X" if m.get("role") == "x" else "Comprador"
        txt = str(m.get("texto", "")).strip()
        if txt:
            linhas.append(f"{quem}: {txt}")
            tem = True
    if not tem:
        linhas.append("(a conversa ainda não começou: faça a PRIMEIRA fala)"
                      + (" Você TEM dossiê: abra mostrando que leu, sem perguntar o que já sabe."
                         if tem_kb else " Faça a PRIMEIRA pergunta."))
    # teto DURO por contagem: o modelo ignora o "3 a 5" do system e estica a entrevista
    # (a pessoa começa a reclamar). Com dossiê o teto é MENOR (o material já preencheu
    # lacunas), coisa que a versão anterior só dizia em prosa e o modelo ignorava: o
    # número mecânico é o que ele obedece.
    n_perg = sum(1 for m in historico if m.get("role") == "x")
    corte = 4 if tem_kb else 5
    fecha = ""
    if forcar:
        fecha = ("ATENÇÃO: o comprador APERTOU o botão de montar o time agora. Ele não quer "
                 "mais responder. PARE de perguntar. Responda AGORA com acao:montar, montando "
                 "o time com o que já sabe (o dossiê e o que ele já respondeu). Fazer outra "
                 "pergunta neste ponto é ERRO e desrespeita o pedido dele.")
    elif n_perg >= corte:
        fecha = (f"ATENÇÃO: você já fez {n_perg} perguntas, é DEMAIS. PARE de perguntar. "
                 "Responda AGORA com acao:montar, montando o time com o que já sabe. "
                 "Fazer outra pergunta neste ponto é ERRO.")
    elif n_perg >= corte - 1:
        fecha = (f"Você já tem material suficiente ({n_perg} perguntas). Se AINDA falta uma "
                 "lacuna essencial (dor, meta ou dado na mão), faça no MÁXIMO mais UMA "
                 "pergunta e então MONTE. Prefira montar agora.")
    linhas += [""]
    if fecha:
        linhas += [fecha, ""]
    linhas += [
        "Sua vez. Responda com UM objeto JSON e NADA além dele (sem crase, sem texto "
        "fora). Não use ferramentas, não leia arquivos. Use EXATAMENTE um destes dois "
        "formatos, com ESTAS chaves. NÃO invente chaves (nada de next_question, "
        "reasoning, phase, campo, tipo):",
        "",
        'Pra continuar a entrevista: {"acao":"perguntar","pergunta":"<pergunta curta, '
        'UMA frase, sem saudação>","opcoes":["<resposta pronta 1>","<resposta pronta 2>"],'
        '"candidato":{"ic":"<emoji>","nome":"<um especialista '
        'sob medida>","papel":"<o que ele faz>"}}  (opcoes: 2 a 4 respostas prontas e '
        "concretas quando a pergunta admite alternativas prováveis, omita em pergunta "
        "aberta; candidato pode ser null, e NUNCA repete papel que já está na fila)",
        "",
        'Pra fechar (depois de 3 a 5 perguntas boas, nunca mais): {"acao":"montar","recomendacao":'
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


def _claude_cli(prompt, system, tools=None, cwd=None, timeout=180):
    """O cérebro do produto: roda um turno pelo Claude Code do COMPRADOR (a assinatura
    dele, R$ 0, sem chave paga), headless via `claude -p`. Devolve o texto do modelo,
    ou None se o CLI não existe / falha (aí o passo cai no próximo cérebro).

    tools: allowed tools separadas por espaço. None/"" = SÓ CONVERSA (entrevista, sem ler
      arquivo). "Read Grep Glob" = leitura read-only (o chat de agente lê o repo do aluno).
    cwd: pasta de trabalho. None = tempdir neutro (entrevista, não puxa CLAUDE.md). O repo do
      comprador pro chat, pra o agente achar os arquivos dele (producao/, contexto/, ...).
    timeout: teto desta chamada, em segundos. A entrevista passa o que SOBRA do orçamento
      dela (ver _ORCAMENTO_PASSO), pra a soma das tentativas não estourar o teto do cliente."""
    exe = shutil.which("claude")
    if not exe:
        return None
    import tempfile
    # --system-prompt = override total (persona limpa, sem o prompt de agente-de-código por
    # baixo). SEM --bare: --bare forçaria ANTHROPIC_API_KEY e mataria a assinatura.
    cmd = [exe, "-p", "--output-format", "json", "--system-prompt", system]
    cmd += _flags_modelo()   # o comprador manda no modelo (GENESIS_MODELO); vazio = default dele
    cmd += (["--allowedTools", tools] if tools else ["--tools", ""])  # tools na allowlist auto-aprovam em headless
    run_cwd = str(cwd) if cwd else tempfile.gettempdir()
    try:
        proc = subprocess.run(
            cmd, input=prompt, capture_output=True, text=True,
            encoding="utf-8", errors="ignore", timeout=timeout,
            cwd=run_cwd, env=_env_assinatura())
    except Exception:
        return None
    if proc.returncode != 0 or not (proc.stdout or "").strip():
        return None
    try:
        env = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None
    # o envelope já entrega qual modelo rodou: guarda pra a cena poder avisar quem está em
    # Opus antes da montagem (a cota do Opus é separada e é a que acaba primeiro)
    mu = env.get("modelUsage") or {}
    if mu:
        global _ULTIMO_MODELO
        _ULTIMO_MODELO = next(iter(mu), "") or _ULTIMO_MODELO
    if env.get("is_error"):
        return None
    return env.get("result") or ""


# Teto de tempo de UM passo da entrevista, somando TODAS as tentativas. Tem que ficar abaixo
# do teto do cliente (200s, no api() do genesis.html), senão o browser desiste primeiro e a
# tentativa seguinte é trabalho jogado fora: o comprador já leu "perdi a conexão" e o servidor
# segue queimando um claude -p que ninguém vai ler. Com tentativas de 180s fixos, o pior caso
# eram 3 x 180s = 540s pra uma resposta abandonada aos 200s.
_ORCAMENTO_PASSO = 170
_MIN_TENTATIVA = 20   # sobrando menos que isto, nem começa: não dá tempo de um turno voltar


def passo(historico, base=None, forcar=False, candidatos=None):
    """Um passo da entrevista. `historico` = lista [{role:'x'|'voce', texto}]. `base` = raiz
    do repo do comprador, pra ler o dossiê que ele conectou (contexto/referencia/) e o X
    entrevistar JÁ sabendo quem ele é, em vez de perguntar o que já está escrito. `forcar` =
    ele apertou "monta agora" e não quer mais responder. `candidatos` = nomes já na fila do
    recrutamento (a memória anti-duplicata: cada turno é um processo novo).

    Devolve o dict do turno + `modelo`: qual modelo o Claude Code DELE está usando. A cena
    usa isso pra, no reveal, oferecer trocar de modelo só a quem está em Opus (cota separada
    e apertada), em vez de perguntar o plano pra todo mundo.

    Cérebro: o Claude Code do COMPRADOR (na assinatura dele, R$ 0, via `claude -p`). Se o
    `claude` não estiver disponível, cai numa entrevista determinística, pra nunca travar."""
    r = _passo(historico, base, forcar, candidatos)
    r["modelo"] = _ULTIMO_MODELO
    return r


def _passo(historico, base, forcar, candidatos=None):
    historico = historico or []
    # dose menor que a da montagem: isto roda a CADA turno, e latência aqui é UX.
    kb = _ler_referencia(base, teto=14000, por_arquivo=5000) if base else ""

    tem_resposta = any(m.get("role") == "voce" for m in historico)
    # "monta agora" sem NENHUM material (nem resposta, nem dossiê) montaria um time do nada
    # (ou do CLAUDE.md global da máquina). Nesse caso ignora o forçar e abre a entrevista.
    if forcar and not tem_resposta and not kb:
        forcar = False

    # SEM dossiê, a primeira pergunta é FIXA: curta, aberta, acolhedora, sem assumir que a
    # pessoa tem negócio ou vende algo. Deixado pro modelo, ele abre com "qual seu negócio,
    # o que você vende", que exclui quem não vende (funcionário, analista, estudante).
    # COM dossiê, o modelo abre: ele já sabe quem é a pessoa e a abertura tem que provar isso
    # (perguntar "o que você faz?" pra quem acabou de entregar o site é o que queima a cena).
    if not tem_resposta and not kb and not forcar:
        return {"done": False,
                "pergunta": "Pra começar simples: o que você faz no dia a dia?",
                "candidato": None}

    system = _SYSTEM
    # o Claude Code do comprador conduz a entrevista, na assinatura dele
    prompt = _montar_prompt(historico, kb, forcar, candidatos)

    # ORÇAMENTO, não contagem de tentativas: as tentativas dividem _ORCAMENTO_PASSO entre si,
    # e quem não cabe nele não roda. Uma queda do CLI não pode custar a entrevista (um hiccup
    # viraria time genérico na hora, o colapso do clímax na frente da plateia), mas tentar de
    # novo SÓ ajuda se a resposta ainda chegar a tempo de alguém ler.
    fim = time.monotonic() + _ORCAMENTO_PASSO

    def _cli(p):
        resta = fim - time.monotonic()
        if resta < _MIN_TENTATIVA:   # o que sobra não dá pra um turno voltar: degrada já
            return None
        return _claude_cli(p, system, timeout=resta)

    texto = _cli(prompt)
    if texto is None:
        texto = _cli(prompt)
    if texto is not None:
        obj = _extrair_json(texto)
        if obj is None:  # embrulhou/cortou: re-pede enxuto uma vez antes de degradar
            texto = _cli(prompt + "\n\nResponda SÓ com o JSON, completo, começando em '{' e "
                                  "terminando em '}'.")
            obj = _extrair_json(texto or "")
        if obj is not None:
            r = _normalizar(obj, historico)
            # o comprador pediu pra montar e o modelo insistiu em perguntar: re-pede UMA vez
            # em modo "só montar" antes de degradar. Jogar fora um modelo que está no ar e
            # cair no time genérico das trilhas era desperdício (o botão é um contrato com o
            # comprador, mas o time sob medida ainda é a entrega; degradar é o último recurso).
            if forcar and not r.get("done"):
                texto2 = _cli(prompt + "\n\nATENÇÃO: responda SOMENTE com acao:montar (a "
                                       "recomendacao completa). Pergunta agora é ERRO.")
                obj2 = _extrair_json(texto2 or "")
                r2 = _normalizar(obj2, historico) if obj2 is not None else None
                if r2 and r2.get("done"):
                    return r2
                return {"done": True, "recomendacao": _garantir_ds(_reco_fallback(historico))}
            return r

    # sem o Claude Code disponível: entrevista determinística (nunca trava)
    return _fallback(historico, forcar, kb)


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

# Guardião Visual, o dono do design system do OS (agente obrigatório)

Você é o Guardião Visual deste OS. Duas missões, sempre:

## 1. EXTRAIR
Dada uma referência (um HTML, uma URL, um print, um site que a pessoa admira), extraia
o design system dela: tokens de cor (hex exatos), tipografia (famílias, escala, pesos),
espaçamento, radius, sombras, e os componentes/padrões estruturais. Nunca chute cor:
leia a referência e tire o valor real. Pra fazer isso com rigor e um entregável pronto,
rode a skill `/extrair-design-system` (ela gera o `contexto/design-system.html`).

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

# Skill OBRIGATÓRIA de extração de DS (simétrica ao agente). Self-contained: salva no OS do
# comprador (contexto/), sem nenhum path do xperiun-os. É a ferramenta REAL por trás do
# Guardião Visual (o agente para de ser só persona, ganha um processo que roda de verdade).
# (a skill obrigatória /extrair-design-system saiu daqui: agora mora versionada em
#  .genesis/skills-core/extrair-design-system/ e o instalar() a copia como as demais skills
#  de template — versão completa de 11 seções, não mais o stub inline. Ver .genesis/CLAUDE.md.)

_RE_FM = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)


def _sem_html(s):
    return re.sub(r"<[^>]+>", "", str(s or "")).strip()


def _slug(s):
    # tira acento (NFKD) ANTES de slugar, pra o slug do agente ficar estável e casar
    # com o nome do arquivo no disco ('André' vira andre) em qualquer sistema de arquivos.
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-") or "agente"


_RE_ARQUIVO_FONTE = re.compile(r"[\w\-./]+\.(?:md|txt|csv|xlsx?|json|pdf|docx?)\b", re.I)


def _sanear_fonte(reco):
    """A 'fonte a conectar' é uma fonte de dados VIVA do mundo do comprador (planilha, CRM,
    export que atualiza), NUNCA um nome de arquivo. O modelo às vezes chuta um filename do
    dossiê que leu (`empresa.md`, `posicionamento.md`): isso é o MATERIAL de contexto, não a
    fonte, e o comprador não sabe o que é `posicionamento.md`. Se o titulo cita arquivo, cai
    num genérico humano; se só o sub cita, tira a menção sem reescrever tudo. Defensivo: o
    prompt já proíbe, mas prompt vaza, então o filename nunca chega ao fonte.md nem ao card."""
    f = reco.get("fonte")
    if not isinstance(f, dict):
        return reco
    if _RE_ARQUIVO_FONTE.search(str(f.get("titulo") or "")):
        f["titulo"] = "sua fonte de dados"
        f["sub"] = ("Conecte uma fonte viva do seu dia a dia (planilha de vendas, export do "
                    "CRM ou ERP, conta de anúncios) pro seu time trabalhar com número real.")
    elif f.get("sub"):
        f["sub"] = _RE_ARQUIVO_FONTE.sub("sua fonte", str(f["sub"]))
    return reco


def _garantir_ds(reco):
    """Enforce: todo OS SEMPRE tem o Guardião Visual (agente slug design-system) E a skill
    /extrair-design-system, os dois obrigatórios (founder). Injeta o que faltar e recalcula.
    O slug do agente segue 'design-system' (id interno estável); muda só o nome de exibição."""
    ags = reco.setdefault("agentes", [])
    if not any(_slug(a.get("slug") or a.get("nome")) == "design-system"
               for a in ags if isinstance(a, dict)):
        ags.append({"slug": "design-system", "nome": "Guardião Visual", "ic": "🎨",
                    "tag": "Obrigatório",
                    "por": "Todo OS precisa de consistência visual. Ele <b>extrai</b> o design system de uma referência e <b>cria/mantém</b> o seu, pra todo entregável sair coeso."})
    # a skill /extrair-design-system é CORE (vem pronta, copiada pelo instalar() e exibida no
    # bloco "do seu OS" do reveal), então NÃO é injetada aqui: injetar punha ela na lista
    # "sob medida", mislabelando uma ferramenta fixa como se a entrevista tivesse escrito. O
    # agente Guardião Visual (acima) continua obrigatório; a skill dele mora nas CORE.
    sks = reco.setdefault("skills", [])
    nums = reco.setdefault("nums", {})
    nums["agentes"] = len(ags)
    nums["skills"] = len(sks)
    return reco


def _subagent_md(nome_id, description, body):
    desc = " ".join(str(description).split())  # 1 linha, sem quebrar o YAML
    return f"---\nname: {nome_id}\ndescription: >-\n  {desc}\n---\n\n{body.strip()}\n"


# ---- Gerador: o Claude Code do comprador PESQUISA e ESCREVE o time do zero ----

def _ler_referencia(base, teto=60000, por_arquivo=20000):
    """Lê o knowledge base que o comprador conectou em contexto/referencia/ (md/txt/csv): os
    docs que ele soltou na cena, o brief do site que o `puxar_site` escreveu, o contexto que
    o /setup importou do Claude Code dele. É o que faz o time (e a ENTREVISTA) nascerem já
    sabendo do negócio real.

    `teto`/`por_arquivo` afinam a dose: a montagem lê muito (roda uma vez, vale o prompt
    grande); a entrevista lê pouco (roda a cada turno, latência é UX). Vazio se a pasta não
    existe ou está vazia, aí o fluxo segue só pelo que a pessoa contar.

    COTA JUSTA por arquivo (não corte alfabético): antes, os primeiros na ordem comiam todo o
    teto e o doc de negócio ficava de fora INTEIRO. Pior, o `_contexto-importado.md` (o global
    genérico que o /setup puxa) começa com `_` e ordenava primeiro, comendo o orçamento antes
    do negócio real. Agora cada arquivo entra com uma fatia e o import genérico vai por último."""
    from pathlib import Path as _P
    if not base:
        return ""
    pasta = _P(base) / "contexto" / "referencia"
    if not pasta.is_dir():
        return ""
    arquivos = [f for f in pasta.rglob("*")
                if f.is_file() and f.suffix.lower() in (".md", ".txt", ".csv")
                and f.name.lower() != "readme.md"]
    if not arquivos:
        return ""
    # o import automático genérico vai por ÚLTIMO: o doc de negócio que o comprador conectou
    # importa mais que o CLAUDE.md global que o /setup puxou. Empate, ordem alfabética estável.
    arquivos.sort(key=lambda f: (f.name.startswith("_contexto-importado"), f.name.lower()))
    # teto de arquivos: um comprador com 500 docs na pasta não pode zerar a cota de cada um
    # nem estourar a memória. 40 é folgado pro caso real (2 a 10 docs).
    arquivos = arquivos[:40]
    cota = max(600, min(por_arquivo, teto // len(arquivos)))  # fatia justa, piso decente
    partes, total = [], 0
    for f in arquivos:
        if total >= teto:
            break
        try:  # lê SÓ a cota (não o arquivo todo): um .csv de vários GB não vai pra RAM
            with f.open(encoding="utf-8", errors="ignore") as fh:
                txt = fh.read(cota)
        except OSError:
            continue
        partes.append(f"### {f.relative_to(pasta).as_posix()}\n{txt}")
        total += len(txt)
    return "\n\n".join(partes)


def _prompt_gerador(perfil, agentes, skills, referencia=""):
    lista_ag = "\n".join(
        f"- slug `{a.get('slug')}` ({a.get('nome', '')}): {_sem_html(a.get('por', ''))}"
        for a in agentes) or "- (você decide de 3 a 5 especialistas pelo perfil)"
    lista_sk = "\n".join(
        f"- slug `{s.get('slug')}` ({s.get('nome', '')}, comando {s.get('cmd', '')}): {_sem_html(s.get('desc', ''))}"
        for s in skills) or "- (você decide de 2 a 4 automações pelo perfil)"
    kb = ""
    if (referencia or "").strip():
        kb = ("KNOWLEDGE BASE REAL DO COMPRADOR (documentos que ele deixou em "
              "contexto/referencia/). USE isto pra escrever um time PRECISO pro negócio dele: "
              "cite produtos, tom, público e fatos REAIS daqui quando fizer sentido, nunca "
              "invente o que não está aqui.\n" + referencia.strip()[:60000] + "\n\n")
    return (
        "Você é o motor de criação do OS do comprador. Você PESQUISA na web e ESCREVE, do zero, "
        "os agentes e skills sob medida pra pessoa. Cada um é um especialista real e "
        "funcional, nada genérico de enfeite.\n\n"
        f"PERFIL (da entrevista):\n{perfil}\n\n{kb}"
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


# Whitelist ESTRITA de onde a montagem pode gravar. NÃO basta "dentro de .claude/ sem ..":
# o dossiê é conteúdo NÃO confiável (site colado, doc de terceiro) e alimenta o prompt cuja
# saída vira arquivo no disco. Um `.claude/settings.local.json` ou `.claude/hooks/x.py` gravado
# ali roda na PRÓXIMA sessão do Claude Code do comprador = execução de comando. Só agente
# (.md solto em agents/) e skill (arquivo dentro de skills/<slug>/) passam. Nada de settings,
# hooks, commands, .py, ou qualquer coisa executável.
# O nome do arquivo de skill é SKILL.md literal, não um padrão: o _parse_blocos normaliza
# qualquer .md de skills/<slug>/ pra SKILL.md ANTES de testar aqui, então uma classe de
# caractere no lugar prometeria uma flexibilidade que não existe.
_RE_AG_OK = re.compile(r"^\.claude/agents/[a-z0-9][a-z0-9-]*\.md$")
_RE_SK_OK = re.compile(r"^\.claude/skills/[a-z0-9][a-z0-9-]*/SKILL\.md$")


def _parse_blocos(texto):
    """Extrai os arquivos gerados dos blocos ===ARQUIVO:path=== ... ===FIM===.
    Trava de segurança dura: só agente (.claude/agents/<slug>.md) ou skill markdown
    (.claude/skills/<slug>/<arquivo>.md). Qualquer outro caminho é descartado, mesmo dentro
    de .claude/ (settings/hooks/.py sob .claude/ seriam RCE latente com dossiê hostil)."""
    out = []
    for m in re.finditer(r"===ARQUIVO:(.+?)===\s*\n(.*?)\n===FIM===", texto, re.DOTALL):
        path = m.group(1).strip().lstrip("/").replace("\\", "/")
        body = m.group(2).strip()
        # tira cerca de código que o modelo às vezes envolve o arquivo inteiro (```md ...
        # ```): sem isso o frontmatter não fica no topo e o Claude Code não carrega o agente
        body = re.sub(r"^```[a-zA-Z]*\s*\n", "", body)
        body = re.sub(r"\n```\s*$", "", body).strip()
        if not body or ".." in path:
            continue
        # skill: o arquivo TEM que se chamar SKILL.md (o Claude Code exige), mas o modelo
        # às vezes nomeia <slug>.md. Normaliza qualquer .md dentro de skills/<slug>/.
        ms = re.match(r"(\.claude/skills/[^/]+)/[^/]+\.md$", path)
        if ms:
            path = ms.group(1) + "/SKILL.md"
        if not (_RE_AG_OK.match(path) or _RE_SK_OK.match(path)):
            continue  # fora da whitelist agente/skill: descarta (settings, hooks, .py, ...)
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


# Motivos de a montagem não entregar o time sob medida. O comprador vê texto diferente pra
# cada um, porque a saída dele é diferente: cota estourada se resolve esperando, CLI ausente
# se resolve instalando. "Deu erro" pra tudo não ajuda ninguém.
MOTIVO_LIMITE = "limite"     # a cota do plano dele acabou (o Opus tem cota própria e apertada)
MOTIVO_SEM_CLI = "sem-cli"   # o `claude` não está no PATH
MOTIVO_ERRO = "erro"         # qualquer outra falha do CLI
MOTIVO_VAZIO = "vazio"       # rodou, mas não veio bloco de arquivo nenhum

_RE_LIMITE = re.compile(r"limit|quota|rate.?limit|usage.*reset|too many requests", re.I)

# O que o comprador lê quando o time sob medida não saiu. Uma frase por motivo, porque a
# SAÍDA de cada um é diferente: cota se resolve esperando, CLI ausente se resolve
# instalando. Nunca "deu erro" genérico, e nunca silêncio.
_FRASE_MOTIVO = {
    MOTIVO_LIMITE: "O limite do seu plano Claude acabou no meio da montagem. Montei um time "
                   "BASE pra você começar. Quando a sua cota voltar, refaça: o time sob "
                   "medida nasce escrito do zero pro seu caso.",
    MOTIVO_SEM_CLI: "O comando 'claude' não está no PATH, então não deu pra escrever o time "
                    "sob medida. Montei um time BASE. Instale o Claude Code e refaça.",
    MOTIVO_ERRO: "O motor não conseguiu escrever o time sob medida agora. Montei um time "
                 "BASE pra você começar. Refaça mais tarde.",
    MOTIVO_VAZIO: "A montagem não devolveu o time sob medida. Montei um time BASE pra você "
                  "começar. Refaça pra tentar de novo.",
}


def _motivo(ev, rc, err):
    """Traduz a saída do CLI no PORQUÊ. O evento `result` do stream-json carrega
    `is_error`, `api_error_status` e `terminal_reason`, e o 429 é o sinal de cota. Sem
    olhar isto, estourar o limite do plano vira 'falhou' genérico e a cena mente."""
    if ev:
        if ev.get("api_error_status") == 429:
            return MOTIVO_LIMITE
        alvo = " ".join(str(ev.get(k) or "") for k in
                        ("subtype", "terminal_reason", "result", "stop_reason"))
        if ev.get("is_error") and _RE_LIMITE.search(alvo):
            return MOTIVO_LIMITE
        if ev.get("is_error"):
            return MOTIVO_ERRO
    if err and _RE_LIMITE.search(err):
        return MOTIVO_LIMITE
    return MOTIVO_ERRO if rc else MOTIVO_VAZIO


def _gerar_rodada(exe, prompt, modelo=None):
    """Uma rodada de geração via Claude Code do comprador, em STREAMING: lê os eventos ao
    vivo pra alimentar o log da montagem (buscas na web, arquivos escritos) e devolve
    `(blocos, motivo)`: motivo=None quando entregou, senão um MOTIVO_* dizendo por quê.
    `modelo` = a escolha que o comprador fez no reveal (vence o GENESIS_MODELO).

    Devolver só `[]` (como antes) apagava a diferença entre "a cota do comprador acabou" e
    "deu ruim": o instalar caía nos esboços e a cena comemorava igual, com o contador do
    finale confirmando um time que não existe. cwd neutro (tempdir) pra a geração NÃO herdar
    o CLAUDE.md 'não montado' do repo do comprador, igual a entrevista faz."""
    import tempfile
    import threading
    try:
        proc = subprocess.Popen(
            [exe, "-p"] + _flags_modelo(modelo) + ["--allowedTools", "WebSearch WebFetch",
             "--output-format", "stream-json", "--verbose"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8", errors="ignore", cwd=tempfile.gettempdir(),
            env=_env_assinatura())
    except Exception:
        return [], MOTIVO_ERRO
    watchdog = threading.Timer(600, proc.kill)  # teto duro se travar sem produzir saída
    watchdog.start()
    try:
        proc.stdin.write(prompt)
        proc.stdin.close()
    except Exception:
        pass
    texto_final, buf, vistos, ev_final = "", "", set(), None
    try:
        for linha in proc.stdout:
            linha = linha.strip()
            if not linha or linha[0] != "{":
                continue  # ignora o ruído não-JSON (saída de hooks etc.)
            try:
                ev = json.loads(linha)
            except Exception:
                continue
            tp = ev.get("type")
            if tp == "assistant":
                for c in (ev.get("message") or {}).get("content") or []:
                    ct = c.get("type")
                    if ct == "tool_use":
                        nome, inp = c.get("name", ""), (c.get("input") or {})
                        if nome == "WebSearch":
                            _mlog('Pesquisando: "%s"' % _corta(inp.get("query", ""), 66))
                        elif nome == "WebFetch":
                            _mlog("Lendo: %s" % _corta(inp.get("url", ""), 66))
                    elif ct == "text":
                        buf += c.get("text", "")
                        for m in re.finditer(r"===ARQUIVO:(.+?)===", buf):
                            p = m.group(1).strip()
                            if p not in vistos:
                                vistos.add(p)
                                _mlog("Escrevendo %s" % p)
            elif tp == "result":
                texto_final, ev_final = ev.get("result") or "", ev
    except Exception:
        pass
    finally:
        watchdog.cancel()
    err = ""
    try:
        err = proc.stderr.read() or ""     # é aqui que o CLI conta que a cota acabou
    except Exception:
        pass
    try:
        proc.wait(timeout=5)
    except Exception:
        pass
    blocos = _parse_blocos(texto_final or buf)
    if blocos:
        return blocos, None
    return [], _motivo(ev_final, proc.returncode, err)


def gerar_time(reco, referencia="", modelo=None):
    """A montagem de verdade: o Claude Code do COMPRADOR pesquisa na web e ESCREVE o time
    (agentes + skills) do zero, sob medida, JÁ informado pelo knowledge base do comprador
    (`referencia`, lido de contexto/referencia/). Devolve `(blocos, motivo)`:
    blocos = [(caminho_rel, conteudo)] e motivo=None quando entregou o time sob medida;
    [] + um MOTIVO_* quando não deu (aí instalar cai nos esboços, e o motivo é o que
    permite a cena dizer a verdade em vez de comemorar um time que não foi escrito)."""
    exe = shutil.which("claude")
    if not exe:
        return [], MOTIVO_SEM_CLI
    perfil = "\n".join(f"- {_sem_html(e)}" for e in (reco.get("entendi") or [])) or "(sem perfil)"
    agentes = [a for a in (reco.get("agentes") or []) if isinstance(a, dict)
               and _slug(a.get("slug") or a.get("nome")) != "design-system"]
    skills = [s for s in (reco.get("skills") or []) if isinstance(s, dict)
              and _slug(s.get("slug") or s.get("cmd") or s.get("nome")) != "extrair-design-system"]
    blocos, motivo = _gerar_rodada(exe, _prompt_gerador(perfil, agentes, skills, referencia), modelo)
    if not blocos:
        return [], motivo
    # completude: se a resposta cortou e faltou algum slug pedido, re-pede SÓ os que
    # faltaram (uma vez), pra o time entregue bater com o que o reveal prometeu.
    req_ag = {_slug(a.get("slug") or a.get("nome")) for a in agentes}
    req_sk = {_slug(s.get("slug") or s.get("cmd") or s.get("nome")) for s in skills}
    tem_ag, tem_sk = _slugs_de(blocos)
    falta_ag = [a for a in agentes if _slug(a.get("slug") or a.get("nome")) not in tem_ag]
    falta_sk = [s for s in skills if _slug(s.get("slug") or s.get("cmd") or s.get("nome")) not in tem_sk]
    if falta_ag or falta_sk:
        extra, _ = _gerar_rodada(exe, _prompt_gerador(perfil, falta_ag, falta_sk, referencia), modelo)
        vistos = {rel for rel, _ in blocos}
        blocos += [(rel, body) for rel, body in extra if rel not in vistos]
    return blocos, None


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
          "- Consistência visual é inegociável: todo entregável visual passa pelo agente `design-system`."]

    # Roteamento EXPLÍCITO pras skills core. Listar a skill acima não basta: medido em
    # 21/07/2026, com a skill instalada e descoberta, o modelo respondeu a "quanto a gente
    # faturou em 2025?" escrevendo o próprio script do zero, sem nunca abrir a SKILL.md.
    # E script do zero é exatamente o que erra 3x em planilha com subtotal. Regra no
    # CLAUDE.md pega porque este arquivo entra em contexto em TODA sessão.
    # Condicional ao arquivo existir no disco: este CLAUDE.md nunca promete o que não há.
    if (skills_dir / "analisar" / "SKILL.md").exists():
        L += ["- **Pergunta sobre planilha ou dado (`dados/`, `.xlsx`, `.csv`): INVOQUE a skill `analisar`.**",
              "  Invoque a skill de verdade, não reimplemente o que ela faz. Ela roda um profiler",
              "  determinístico que lê 100% das linhas e é coberto por teste de regressão. Script",
              "  escrito na hora não tem essa garantia, mesmo quando parece dar certo."]
    if (skills_dir / "conectar" / "SKILL.md").exists():
        L += ["- **Conectar ferramenta ou sistema externo: INVOQUE a skill `conectar`.**",
              "  Invoque a skill de verdade. Ela carrega o procedimento e o catálogo de receitas",
              "  verificadas, que você não tem como reproduzir de memória sem inventar endpoint."]
    L += [""]
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


def instalar(reco, base, modelo=None):
    """Materializa o OS do comprador em `base` (a pasta MÃE), a estrutura do OS:
    - `.claude/agents/` — o TIME como SUBAGENTS REAIS do Claude Code (invocáveis), escritos
      sob medida pelo Claude Code do comprador + o `design-system` OBRIGATÓRIO (extrai + cria).
    - `.claude/settings.json` — o guarda-corpo: o hook que grava o pulso do time pro painel.
    - `contexto/` — quem o comprador é (o recheio) + a fonte a conectar.
    - `.claude/skills/` — as skills sob medida.
    - `producao/` — onde as entregas do time caem.
    - `meu-os.json` — o manifesto do reveal. Idempotente. base = raiz do repo do comprador.

    `modelo` = a escolha do comprador no reveal (ex: "sonnet"), que vence o GENESIS_MODELO.
    Devolve {caminho, sob_medida, motivo, aviso}: `sob_medida=False` quer dizer que o time
    sob medida NÃO foi escrito e o que está no disco é esboço."""
    from pathlib import Path as _P
    _sanear_fonte(reco)  # defensivo: nenhum filename do dossiê vaza pro fonte.md/card/CLAUDE.md
    base = _P(base)
    _mlog_reset()
    _mlog("Organizando o time e preparando o repositório...")
    reco = _scrub(reco) if isinstance(reco, dict) else {}  # travessão/canon fora do que grava
    _garantir_ds(reco)  # DS obrigatório ANTES de materializar
    for sub in ("contexto", "contexto/referencia", "producao", ".claude/agents", ".claude/skills"):
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
    _mlog("Contratando os especialistas: pesquisa na web + escrita do zero.")
    gerados, motivo = gerar_time(reco, _ler_referencia(base), modelo)
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
        # ESBOÇO: o time sob medida NÃO foi escrito. O comprador precisa saber disso (ver o
        # `motivo` que sobe pro /status e pra cena) — o contador do finale conta arquivo no
        # disco, e esboço também é arquivo, então sem este sinal o número comemora sozinho.
        _mlog(_FRASE_MOTIVO.get(motivo) or _FRASE_MOTIVO[MOTIVO_ERRO])
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
            if slug == "extrair-design-system":
                continue  # essa é cinto canônico (abaixo), não stub da entrevista
            d = skills_dir / slug
            d.mkdir(parents=True, exist_ok=True)
            (d / "SKILL.md").write_text(_subagent_md(
                slug, _sem_html(s.get("desc")) or f"{s.get('nome', 'skill')}.",
                f"# {s.get('nome', slug)}\n\n{_sem_html(s.get('desc', ''))}\n\n"
                "> Esboço da entrevista. Rode o Genesis com o Claude Code pra gerar a automação completa."),
                encoding="utf-8")
            ger_sk.add(slug)
    # cinto de segurança: o Guardião Visual (design-system.md) existe SEMPRE, gerado ou não
    if not (agents_dir / "design-system.md").exists():
        (agents_dir / "design-system.md").write_text(
            _sem_canon(_sem_traves(_DS_AGENTE_MD)), encoding="utf-8")
    ger_ag.add("design-system")
    # skills de TEMPLATE (não sob medida), copiadas do repo pro OS na montagem (overwrite,
    # sempre fresquinhas). CORE = obrigatórias (ex: /extrair-design-system, a ferramenta REAL
    # do Guardião Visual); BÔNUS = brindes (ex: /site-reveal-cinematico). Moram versionadas em
    # .genesis/skills-core|skills-bonus/. As CORE entram no manifesto de gerados (contam e são
    # geridas no reinstall); as BÔNUS ficam de fora (template puro, sobrevivem intactas).
    # Ver .genesis/CLAUDE.md §Skills bônus. O catálogo/reveal marca via .genesis/bonus-skills.json.
    for _tdir, _mark in ((base / ".genesis" / "skills-core", ger_sk),
                         (base / ".genesis" / "skills-bonus", None)):
        if not _tdir.is_dir():
            continue
        for _s in sorted(x for x in _tdir.glob("*") if x.is_dir()):
            _dst = skills_dir / _s.name
            if _dst.exists():
                shutil.rmtree(_dst)
            shutil.copytree(_s, _dst)
            if _mark is not None:
                _mark.add(_s.name)

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
    # "sob medida" só quando FOI sob medida: no caminho do esboço a frase seria mentira, e
    # o README é a primeira coisa que o comprador lê no repo dele.
    _linha = (f"{n_agentes} agentes, {n_skills} skills, feitos sob medida pra você."
              if not motivo else
              f"{n_agentes} agentes, {n_skills} skills, em versão BASE.\n\n"
              f"> {_FRASE_MOTIVO.get(motivo) or _FRASE_MOTIVO[MOTIVO_ERRO]}")
    (base / "README.md").write_text(
        "# Meu OS\n\nGerado pelo Genesis Studio. " + _linha + "\n\n"
        "Estrutura do seu OS:\n"
        "- `.claude/agents/`: **o seu time, como subagents reais do Claude Code** (invocáveis)\n"
        "- `contexto/`: quem você é. Jogue seus docs em `contexto/referencia/` ANTES de montar, o time nasce sabendo\n"
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
    # contexto/referencia/ — o KNOWLEDGE BASE. O comprador joga os docs do negócio aqui ANTES
    # de montar; a montagem lê e o time nasce sabendo. Fecha o gap de "dado real".
    ref = base / "contexto" / "referencia"
    ref.mkdir(parents=True, exist_ok=True)
    if not (ref / "README.md").exists():
        (ref / "README.md").write_text(
            "# Referência (o seu knowledge base)\n\n"
            "Jogue aqui os documentos do seu negócio (.md, .txt, .csv): quem você é, seus "
            "produtos, seu tom de voz, seu público, seus números, seus casos. Antes de montar "
            "(ou remontar) o time com o Genesis, o seu Claude Code LÊ esta pasta e escreve os "
            "agentes JÁ sabendo do seu negócio, não genéricos.\n\n"
            "Quanto mais real o material aqui, mais afiado o time sai. Sem nada aqui, o time "
            "nasce só pelo que você contou na entrevista.\n", encoding="utf-8")
    # contexto/fonte.md — a fonte de dados VIVA (além do knowledge estático da referencia)
    (base / "contexto" / "fonte.md").write_text(
        "# Minha fonte de dados\n\n**" + _sem_html(fonte.get("titulo", "sua fonte")) + "**\n\n" +
        _sem_html(fonte.get("sub", "")) +
        "\n\n> Aqui vai a fonte de dados VIVA (planilha, API, export que atualiza). O knowledge "
        "estático (quem você é, produtos, tom, casos) vai em `contexto/referencia/`.\n",
        encoding="utf-8")

    (base / "producao" / ".gitkeep").write_text("", encoding="utf-8")

    # git limpo: os únicos rastreados que o config sobrescreve são CLAUDE.md e README.md
    # (o resto do OS é gitignored). skip-worktree faz o git parar de mostrá-los como
    # modificados e o pull de melhorias do código (.genesis/) nunca esbarrar neles.
    if (base / ".git").exists():
        try:
            subprocess.run(["git", "-C", str(base), "update-index", "--skip-worktree",
                            "CLAUDE.md", "README.md"], capture_output=True, timeout=15)
        except Exception:
            pass
    _mlog("Time gravado no seu repositório.")
    # devolve O QUE ACONTECEU, não só onde: `motivo` None = time sob medida escrito do zero;
    # senão o MOTIVO_* do esboço. O servidor sobe isso pro /status e a cena para de comemorar
    # um time que não foi escrito.
    return {"caminho": base, "sob_medida": not motivo, "motivo": motivo,
            "aviso": (_FRASE_MOTIVO.get(motivo) or _FRASE_MOTIVO[MOTIVO_ERRO]) if motivo else ""}


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
        eventos.append({"agente": nomes.get(ag, ag) or "o time", "acao": str(e.get("acao", "")), "quando": quando, "_ts": ts})
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
