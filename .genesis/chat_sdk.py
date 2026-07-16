"""Chat com um agente do OS rodando na ASSINATURA do comprador (claude-agent-sdk, R$ 0
de token), com streaming token a token e sessão viva por agente. Portado do agentic-os
(nucleo/chat.py do painel do founder), adaptado pro OS do aluno: um time plano (slug),
base = raiz do repo DELE.

Três decisões que vieram juntas do port:
- tools READ-ONLY (Read/Grep/Glob): o agente LÊ o repo (contexto/, producao/, um arquivo)
  pra responder com dado real, mas NÃO escreve nem roda comando. Trabalho que produz
  arquivo é o BUILD (botão "põe pra trabalhar").
- cliente QUENTE por agente, com continuidade de sessão (o agente lembra do papo). O
  flag `novo` recicla a sessão daquele agente (conversa nova começa do zero).
- a persona (o .agent.md + knowledge) NÃO vai no system_prompt: no Windows o SDK monta o
  system via argv e a linha estoura (WinError 206). O system fica CURTO no argv, e a
  persona inteira entra na PRIMEIRA mensagem (stdin, sem limite). A sessão segura a
  persona nos turnos seguintes.

A chave de API sai do ambiente do subprocesso DE PROPÓSITO: sem ela o Claude Code usa o
login OAuth do comprador e o billing vai pra assinatura. Se o SDK não estiver instalado
ou falhar, o servidor cai no caminho single-shot (`painel_backend.chat`), que continua
funcionando igual antes.

A GAIOLA HONESTA (caso real do founder, 2026-07-16): o agente do chat oferecia "quer que
eu rode /titulos agora?" sem ter como executar skill nenhuma, e a tentativa dava erro. O
conserto não é dar mais poder ao chat (isso reabre o risco todo): é ensinar o agente a
admitir a própria gaiola, no system. Aqui você só lê; pra executar, o dono usa o build ou
o terminal. Nunca prometa disparar o que você não pode."""
import asyncio
import os
import shutil
import threading

_loop = None
_loop_pronto = threading.Event()
_clientes = {}            # slug -> ClaudeSDKClient (quente, com sessão viva)

# O SDK procura um claude.exe "bundled" que não existe; aponta o cli_path pro binário real.
_CLI = next((p for p in (os.environ.get("CLAUDE_CODE_EXECPATH"), shutil.which("claude"))
             if p and os.path.exists(p)), None)

# System curto (cabe no argv). A persona real entra na 1ª mensagem via stdin.
_SYSTEM_CURTO = (
    "Você incorpora um especialista do time de IA pessoal do dono deste OS. A definição "
    "COMPLETA da sua persona (papel, método, voz) e o contexto do negócio dele chegam na "
    "PRIMEIRA mensagem desta conversa. Incorpore essa persona por inteiro e responda SEMPRE "
    "em personagem, na voz dela: direto, caloroso, brasileiro, sem corporativês, português "
    "do Brasil com todos os acentos. Nunca invente número, depoimento ou fato. Sem abertura "
    "de chatbot. Zero travessão em prosa. Nunca escreva 'canon' ou 'canônico'.\n\n"
    "VOCÊ TEM ACESSO DE LEITURA ao repositório (ferramentas Read, Grep, Glob). Quando o "
    "dono pedir análise ou leitura de algo que está no repo (contexto/, producao/, um "
    "arquivo), ABRA E LEIA você mesmo e responda com o dado real na mão. NUNCA peça pra "
    "ele colar o que já está no disco. No máximo UMA pergunta de escopo, nunca três.\n\n"
    "SUA GAIOLA (seja honesto sobre ela): neste chat você SÓ LÊ. Você NÃO executa skills "
    "(/comandos), NÃO escreve arquivo, NÃO roda comando nenhum. NUNCA ofereça 'quer que eu "
    "rode /skill?' nem prometa disparar qualquer coisa: você não consegue, e prometer é "
    "mentir pro dono. Quando o pedido exigir executar ou produzir (rodar uma skill, gravar "
    "um lançamento, gerar um arquivo), aponte o caminho real com clareza: ele clica em "
    "'põe pra trabalhar' (o build, que tem as ferramentas de escrita), ou roda a skill "
    "direto no Claude Code dele (digitando o /comando lá no terminal)."
)
_SEP = "\n\n===== A PARTIR DAQUI COMEÇA A CONVERSA (responda como este especialista) =====\n\n"


def disponivel():
    return _CLI is not None and _importa_sdk()


def _importa_sdk():
    try:
        import claude_agent_sdk  # noqa: F401
        return True
    except Exception:
        return False


def _garantir_worker():
    global _loop
    if _loop is not None and _loop.is_running():
        return
    _loop_pronto.clear()

    def rodar():
        global _loop
        _loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_loop)
        _loop_pronto.set()
        _loop.run_forever()

    threading.Thread(target=rodar, daemon=True, name="chat-loop").start()
    _loop_pronto.wait(10)


async def _novo_cliente(base):
    from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient
    # env = tudo do processo MENOS as chaves de API: sem elas, o Claude Code usa o OAuth
    # do comprador (billing na assinatura dele). Preserva PATH e CLAUDE_CODE_EXECPATH.
    env = {k: v for k, v in os.environ.items()
           if k not in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")}
    opts = ClaudeAgentOptions(
        cwd=str(base),                   # o repo do comprador: é ele que o agente lê
        env=env,
        cli_path=_CLI,
        system_prompt=_SYSTEM_CURTO,     # CURTO (a persona grande estouraria o argv)
        setting_sources=[],              # sem settings do projeto (init barato, sem hooks)
        allowed_tools=["Read", "Grep", "Glob"],  # LÊ o repo; sem Write/Bash (gaiola)
        permission_mode="default",
        include_partial_messages=True,   # streaming token a token
    )
    c = ClaudeSDKClient(opts)
    await c.connect()
    return c


async def _responder(slug, persona, mensagem, novo, ao_texto, base):
    from claude_agent_sdk import AssistantMessage, ResultMessage, TextBlock
    global _clientes
    if novo and slug in _clientes:
        try:
            await _clientes[slug].disconnect()
        except Exception:
            pass
        _clientes.pop(slug, None)
    c = _clientes.get(slug)
    criou = c is None
    if criou:
        c = await _novo_cliente(base)
        _clientes[slug] = c

    # cliente novo (1ª mensagem da sessão) leva a persona inteira colada na frente;
    # nos turnos seguintes a sessão já lembra dela, manda só a mensagem.
    prompt = (persona + _SEP + mensagem) if criou else mensagem

    partes, streamou = [], False
    await c.query(prompt)
    async for m in c.receive_response():
        if type(m).__name__ == "StreamEvent":
            ev = getattr(m, "event", None) or {}
            if ev.get("type") == "content_block_delta":
                d = (ev.get("delta") or {}).get("text")
                if d:
                    streamou = True
                    partes.append(d)
                    if ao_texto:
                        ao_texto(d)
        elif isinstance(m, AssistantMessage):
            if not streamou:  # sem partial disponível: emite o bloco inteiro de uma vez
                for b in m.content:
                    if isinstance(b, TextBlock) and b.text:
                        partes.append(b.text)
                        if ao_texto:
                            ao_texto(b.text)
        elif isinstance(m, ResultMessage):
            break
    return "".join(partes)


def responder(slug, persona, mensagem, base, novo=False, ao_texto=None):
    """Bloqueante: manda `mensagem` pro agente NA ASSINATURA, streama via ao_texto,
    devolve o texto completo. Levanta exceção se o SDK falhar (o servidor cai pro
    single-shot do painel_backend). Um erro no meio da sessão descarta o cliente
    daquele agente, pra próxima mensagem nascer numa sessão limpa."""
    _garantir_worker()
    fut = asyncio.run_coroutine_threadsafe(
        _responder(slug, persona, (mensagem or "").strip(), bool(novo), ao_texto, base),
        _loop)
    try:
        return fut.result(timeout=180)
    except Exception:
        resetar(slug)   # sessão possivelmente quebrada: recicla pra não travar o agente
        raise


async def _desconectar(slug):
    c = _clientes.pop(slug, None)
    if c is not None:
        try:
            await c.disconnect()
        except Exception:
            pass


def resetar(slug):
    """Encerra a sessão viva daquele agente (conversa nova começa do zero)."""
    if _clientes.get(slug) is not None and _loop is not None:
        asyncio.run_coroutine_threadsafe(_desconectar(slug), _loop)
