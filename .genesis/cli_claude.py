# -*- coding: utf-8 -*-
"""Resolve o caminho do executável do Claude Code. UM lugar só, usado por todo mundo que
executa o CLI (motor, backend, chat).

POR QUE ISSO EXISTE (não simplifique de volta pro `shutil.which("claude")` puro)
-------------------------------------------------------------------------------
No Windows o npm põe no PATH um `claude.CMD`, que é um wrapper batch: ele só chama o
`claude.exe` de verdade em `node_modules/@anthropic-ai/claude-code/bin/`. Rodar pelo
wrapper faz o processo nascer atrás de um `cmd.exe`, e o `cmd.exe` QUEBRA o argumento
que tiver QUEBRA DE LINHA dentro. Todo `--system-prompt` daqui tem quebra de linha.

Os dois estragos, os dois silenciosos (medidos em 2026-07-25, mesma máquina, mesmo
modelo, variando só o executável):

1. Pelo SDK (chat do agente): o `initialize` nunca completa e morre em timeout.
       .exe + system de 1398 chars ->  connect 1,8s / turno 1,8s
       .CMD + system de 1398 chars ->  FALHA em 70,2s "Control request timeout: initialize"
   O servidor então cai no fallback single-shot (+35s) e o turno leva ~105s entregando
   tudo de uma vez, sem streaming. Parece "a IA pensando". Não é.

2. Pelo subprocess (`claude -p`, na entrevista, montagem, build): NÃO dá timeout, faz
   coisa pior. O `--system-prompt` é descartado em silêncio, com `rc=0`, e o modelo
   responde como se não houvesse system nenhum. Teste com a instrução decisiva depois
   da quebra ("responda APENAS a palavra BETA"):
       .exe -> 'BETA'
       .CMD -> 'Fala! (...) **Xperiun OS**, o sistema operacional dos (...)'   rc=0
   O `_SYSTEM` da entrevista tem 7.287 chars e 101 quebras de linha. Ou seja: no Windows,
   pelo wrapper, as regras da entrevista nunca chegavam ao modelo.

NÃO É TAMANHO, É QUEBRA DE LINHA. Foi o que enganou o diagnóstico anterior, e é o que
justifica ter apagado os comentários que falavam de "limite de ~8KB do .cmd". Prova, tudo
no .CMD:
       1398 chars, SEM quebra ->  OK em  7,6s
       1398 chars, COM quebra ->  FALHA em 70,2s
         52 chars, COM quebra ->  FALHA em 70,2s   <- encurtar o prompt não salva nada

Em macOS e Linux isto é no-op: lá o `which` devolve binário ou symlink, nunca `.cmd`, e a
função devolve o candidato intacto.
"""
import os
import shutil

# O que o próprio claude.CMD executa, relativo à pasta dele.
_ALVO = os.path.join("node_modules", "@anthropic-ai", "claude-code", "bin", "claude.exe")


def _nativo(caminho):
    """Troca o wrapper batch pelo executável real. Se não achar o irmão nativo, devolve o
    caminho original: perder o wrapper seria pior que rodar por ele."""
    if not caminho or os.path.splitext(caminho)[1].lower() not in (".cmd", ".bat"):
        return caminho
    irmao = os.path.join(os.path.dirname(caminho), _ALVO)
    return irmao if os.path.exists(irmao) else caminho


def caminho(preferido=None):
    """O executável do Claude Code, ou None se não houver.

    `preferido` entra na frente do PATH (é por onde o chat passa o CLAUDE_CODE_EXECPATH).
    Quem não passa nada continua enxergando exatamente o que o `which` enxergava, só que
    pelo executável nativo em vez do wrapper."""
    for c in (preferido, shutil.which("claude")):
        if c and os.path.exists(c):
            return _nativo(c)
    return None
