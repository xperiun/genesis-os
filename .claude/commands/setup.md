---
name: setup
description: >
  Monta (ou remonta) o OS do usuário: sobe o Genesis Studio no navegador, a entrevista
  que projeta o time de agentes e skills sob medida dele, escrito do zero pelo Claude
  Code dele. Use quando o usuário chamar /setup, ou disser "monta meu OS", "sobe o
  localhost", "configura o sistema", "quero começar", "é a primeira vez".
---

# /setup, o OS nasce aqui

O usuário quer montar (ou remontar) o OS dele.

**Este comando não entrevista ninguém.** A entrevista, o reveal e a montagem acontecem
inteiros na tela do navegador, com teatro. Aqui no chat o trabalho é outro: preparar o
terreno em silêncio e subir a cena.

> **Regra dura: não faça perguntas.** O usuário digitou `/setup` e a próxima coisa que ele
> deve ver é o navegador abrindo. Toda pergunta feita aqui é paciência que a cena não vai
> ter depois, e o terminal nunca pode morder. As únicas coisas que você tem permissão de
> escrever no chat são o aviso do passo 1 (se acontecer) e as duas linhas do passo 4.

## 1. Checar o cérebro (a única coisa que pode travar o fluxo)

Rode (esta linha, exatamente):

```
python -c "import shutil,os,glob;w=shutil.which('claude') or shutil.which('claude.cmd');c=[os.path.expandvars(r'%APPDATA%\npm\claude.cmd'),os.path.expandvars(r'%APPDATA%\npm\claude'),*glob.glob(os.path.expanduser('~/AppData/Roaming/npm/claude*')),*glob.glob(os.path.expanduser('~/.npm-global/bin/claude'))];print(w or next((x for x in c if os.path.exists(x)),'FALTANDO'))"
```

O Genesis inteiro (entrevista, montagem, chat com os agentes, build) roda pelo comando
`claude`, na assinatura do usuário, R$ 0 de API. Sem ele no PATH, tudo degrada em silêncio
pra uma entrevista enlatada e um time genérico, e o usuário nunca descobre por quê. Por isso
esta checagem vem antes de qualquer coisa.

Ela não olha só o PATH: um `claude` recém-instalado costuma existir no disco (`%APPDATA%\npm`)
mas ainda não estar no PATH do terminal que a extensão abriu, e mandar reabrir a janela nesse
caso é fricção à toa. A checagem sonda os locais canônicos de instalação antes de desistir.

- **Voltou um caminho:** siga pro passo 2 sem comentar nada. Não anuncie que checou.
- **Voltou `FALTANDO`:** PARE. Não suba o servidor. Diga exatamente isto e encerre:

  > Antes de começar, um problema: o comando `claude` não está instalado, e é ele que monta o
  > seu time (na sua assinatura, R$ 0). Instala com `npm i -g @anthropic-ai/claude-code`,
  > fecha e abre o VS Code, e roda `/setup` de novo.

## 2. Importar o contexto que já existe (silencioso, best-effort)

Se o usuário já usa o Claude Code, ele já contou quem é em outro lugar. Aproveite, sem
perguntar. Tente ler, ignorando qualquer erro:

1. `~/.claude/CLAUDE.md`, as instruções globais dele
2. `~/.claude/projects/*/memory/MEMORY.md`, o índice de memória de outros projetos dele

Se encontrar material com substância real sobre quem ele é (nome, negócio, o que faz, tom de
voz, preferências), destile num resumo e grave em `contexto/referencia/_contexto-importado.md`,
começando com este cabeçalho:

```markdown
# Contexto importado do seu Claude Code

> Puxado automaticamente pelo /setup do que você já tinha configurado em outros projetos.
> Se algo aqui estiver errado ou velho, corrija ou apague o arquivo: o seu time lê isto.
```

Regras deste passo:

- **Só o que é sobre a PESSOA e o NEGÓCIO dela.** Regra de código, atalho de ferramenta,
  configuração de projeto alheio e preferência técnica solta não entram, viram ruído no time.
- **Não invente pra preencher.** Achou pouco, grave pouco. Não achou nada com substância,
  não crie o arquivo e siga em frente calado.
- **Não é o CLAUDE.md deste repo.** O da raiz daqui é o template do produto, ignore ele.
- Nada disso vira pergunta. Se der erro de permissão ou o arquivo não existir, siga.

## 3. Subir a cena

Rode em segundo plano (background):

```
python .genesis/sobe.py
```

Isso prepara o ambiente (só na primeira vez) e abre o Genesis no navegador, em
`http://localhost:7799`.

> **Regra dura: `sobe.py` é o entrypoint oficial, não improvise em cima dele.** Ele existe
> pra instalar as dependências (flask, sdk) e só então subir `servidor_genesis.py` com o cwd
> certo (é o cwd que decide onde o OS nasce). **Não** rode `servidor_genesis.py` direto, **não**
> troque de comando, **não** conclua que "o roteiro está desatualizado" e **não** invente um
> caminho alternativo com `pip`/`flask` na mão. Se um `ls` ou um `cd` falhar, o problema é o
> cwd, corrija o cwd (rode a partir da raiz do repo) e rode `sobe.py` de novo. Se `sobe.py`
> em si der erro, mostre o erro cru e pare, não contorne.

## 4. Falar duas linhas e sair da frente

Diga, em no máximo duas frases: que a cena abriu no navegador (mostre o endereço, caso ele
não abra sozinho) e que é lá que ele vai conectar o material do negócio e fazer a entrevista.
Se você importou contexto no passo 2, acrescente **uma** linha dizendo o que puxou.

Depois **pare de falar**. Não explique o produto, não liste o que vai acontecer, não pergunte
nada. A cena faz isso melhor que você, e o usuário está olhando pra ela agora, não pro chat.

## Se o OS já estiver montado

Se `.claude/agents/` já existe e tem agentes, o usuário já tem um OS. Rodar `/setup` refaz o
time do zero pela entrevista. Isso é seguro (o que ele escreveu à mão e as entregas em
`producao/` ficam intactas), mas provavelmente não é o que ele quer se só ia trabalhar.
Nesse caso, antes de subir a cena, diga **uma** linha:

> Você já tem um OS montado aqui. Se era só pra trabalhar, roda `/painel` (o time, as tarefas
> e o chat). Seguindo com o `/setup`, você refaz a entrevista e o time nasce de novo, e as
> suas entregas em `producao/` continuam intactas.

E siga com a montagem normalmente. Não espere resposta: o usuário pediu `/setup`, ele sabe
o que quer. A linha existe pra ele não descobrir tarde demais que havia um caminho melhor.
