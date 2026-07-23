---
name: painel
description: >
  Abre o painel do OS do usuário no navegador: o time dele em canvas, o chat com cada
  agente, o board de tarefas, o contexto e as skills. Use quando o usuário chamar /painel,
  ou disser "abre o painel", "quero ver meu time", "abre meu OS", "mostra as tarefas".
---

# /painel, a sala de controle do OS

O usuário quer ver o OS dele funcionando. Este comando **não monta nada e não pergunta
nada**: só sobe o servidor e abre o painel.

É o caminho do dia a dia. O `/setup` é uso único (monta o time); o `/painel` é pra voltar
aqui todo dia sem refazer entrevista nenhuma.

## 1. Se o OS ainda não existe

Se `.claude/agents/` não existe ou está vazia, não há painel pra mostrar. Diga **uma** linha
e pare:

> Seu OS ainda não foi montado, então não tem time pra mostrar aqui. Roda `/setup` primeiro,
> leva alguns minutos e você faz a entrevista na tela.

## 2. Subir e abrir

Rode em segundo plano (background):

```
python .genesis/sobe.py painel
```

O servidor sobe em `http://localhost:7799` e já abre direto no painel. (O `painel` vai sem
barra de propósito: barra na frente é manglada pelo Git Bash no Windows; o servidor
normaliza.) Passe o endereço pro
usuário:

**http://localhost:7799/painel**

Se o servidor já estiver no ar (a porta 7799 responde), não suba outro: só passe o endereço.
Com o OS montado, o `/` também redireciona pro painel, então qualquer aba que caia na home
vai parar no lugar certo.

## 3. Falar uma linha e sair da frente

Diga que o painel está no ar e passe o endereço. Não descreva as abas, não liste o time, não
pergunte o que ele quer fazer. Ele está olhando pra tela agora.

## O que ele encontra lá

Contexto pra você, não roteiro pra recitar no chat:

- **Painel**, a visão geral (contadores, perfil, pulso, fonte)
- **Meu time**, o canvas dos agentes, com chat direto com cada um
- **Tarefas**, o board: ele descreve uma ideia e manda o time construir de verdade
- **Contexto**, o CLAUDE.md e a pasta `contexto/`, editáveis, mais o "puxar do site"
- **Skills**, o catálogo, com o SKILL.md editável
- **Integrações**, o status das conexões

O chat e o build rodam no `claude` da assinatura dele, R$ 0 de API.
