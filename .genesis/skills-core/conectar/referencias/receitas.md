# Receitas de conexão

Conhecimento verificado contra a documentação oficial de cada fabricante. Isto **não**
é um catálogo de integrações prontas: é o que já foi conferido, pra não precisar
pesquisar de novo e pra não errar o caminho da credencial.

**Verificado em 2026-07-21.** Tela de software muda. Se o que está escrito aqui não
bater com o que a pessoa está vendo, **a receita envelheceu**: peça um print, resolva
com ela, e atualize a linha com a data de hoje.

Esforço: 🟢 conexão de 30 segundos (copia a chave de uma tela), 🟡 chave simples mas
com trava (admin, plano, passo escondido), 🔴 projeto (OAuth, app registrado, aprovação)

---

## Triagem rápida

| Ferramenta | Autenticação | Exige admin? | Esforço |
|---|---|---|---|
| **Mailchimp** | chave simples, Basic Auth | não | 🟢 |
| **ActiveCampaign** | chave simples, header `Api-Token` | doc não diz | 🟢 |
| **Airtable** | Personal Access Token, Bearer | não | 🟢 |
| **ClickUp** | token pessoal `pk_`, **sem "Bearer"** | não | 🟢 |
| **Pipedrive** | API token, header `x-api-token` | só p/ liberar a não-admin | 🟢 |
| **Monday** | token pessoal V2, valor cru no header | não confirmado | 🟢 |
| **RD Station CRM (v1)** | token simples | doc não diz | 🟢🟡 |
| **Trello** | API Key **+** Token | não | 🟢🟡 |
| **Omie** | app_key + app_secret **no corpo do JSON** | **sim** | 🟡 |
| **HubSpot** | Private App token | **sim, super admin** | 🟡 |
| **Kommo** | long-lived token ou OAuth | **sim** | 🟡 |
| **Notion** | token interno, Bearer | **sim, workspace owner** | 🟡 |
| **Zendesk** | API token, Basic Auth | **sim** + habilitar na conta | 🟡 |
| **Movidesk** | token (ver contradição abaixo) | doc não diz | 🟡 |
| **Bling** | OAuth 2.0 | não | 🔴 |
| **Conta Azul** | OAuth 2.0 | doc não diz | 🔴 |
| **Tiny (Olist v3)** | OAuth 2.0 | **não**, doc explícita | 🔴 |
| **Sankhya** | OAuth + header `X-Token` | doc não diz | 🔴 |
| **Salesforce** | OAuth obrigatório | **sim** | 🔴 |
| **Meta Ads** | OAuth + app registrado | verificação p/ conta de terceiro | 🔴 |
| **Google Ads** | OAuth + developer token **com aprovação** | **sim**, conta gerenciadora | 🔴 |
| **GA4** | OAuth ou service account via GCP | acesso à propriedade | 🔴 |
| **Google Sheets** | chave **só p/ planilha pública** | não documentado | 🔴 |

---

## O padrão que vale narrar

**Os ERPs brasileiros migraram em bloco pra OAuth.** Bling, Conta Azul e Tiny já
estão lá. O Sankhya trocou o modelo antigo de `appkey + token` por Client
Credentials. O Omie é o único que ainda entrega um par de chaves, e mesmo assim
manda no corpo do JSON e exige administrador.

A ideia de "pego a chave do meu ERP e conecto" **já não descreve o mercado**. Diga
isso com todas as letras em vez de deixar a pessoa descobrir sozinha.

---

## As duas armadilhas que falham com credencial válida

Estas duas merecem atenção porque a chave está certa e mesmo assim não funciona. São
o melhor exemplo de que **a credencial não é o problema**.

**Notion.** O token pode estar perfeito e a API responder erro ou vir vazia, porque a
página precisa ser **compartilhada manualmente com a integração**. Fluxo: abrir a
página, menu `•••`, "Add connections", buscar a integração. Compartilhar uma página
de nível superior propaga pras filhas. É o erro número um de quem conecta Notion pela
primeira vez.

**Mailchimp.** O prefixo de datacenter no subdomínio é a causa mais comum de falha. O
prefixo (ex: `us19`) sai da URL do painel logado, ou do sufixo da própria chave, depois
do último hífen (ex: `...xyz-us14`). Errou o prefixo, a conexão não sobe.

---

## Detalhe por ferramenta

### 🟢 Conexão de 30 segundos

**Mailchimp** — chave simples, sem registro de app. Ícone de perfil > Profile > menu
**Extras** > **API keys** > Create A Key. Cargo "Manager" já gera, não precisa de admin.
Base `https://{dc}.api.mailchimp.com/3.0/`, teste `GET /3.0/ping`. Limite de 10
conexões simultâneas. A chave é por usuário: se o usuário sai da conta, o token morre.
Fonte: `mailchimp.com/developer/marketing/guides/quick-start/`

**ActiveCampaign** — header `Api-Token`. My Settings > aba **Developer**, onde ficam a
chave **e** a URL base. Atenção: **a URL base é própria de cada conta**
(`https://{conta}.api-us1.com/api/3/`), e nem toda conta está em `api-us1`. Copie da
tela, nunca assuma. Teste `GET /api/3/users`. 5 req/s.
Fonte: `developers.activecampaign.com/reference/authentication`

**Airtable** — Personal Access Token, Bearer. `airtable.com/create/tokens`, escolher
escopos e liberar bases explicitamente (não é tudo ou nada). Aparece uma vez só. Teste
`GET /v0/meta/bases`. A API key legada **morreu em 01/fev/2024**, `api_key` na URL não
funciona mais. 5 req/s por base, e o 429 exige esperar 30 segundos.
Fonte: `airtable.com/developers/web/api/authentication`

**ClickUp** — Settings > Apps (`app.clickup.com/settings/apps`). **Pegadinha que quebra
integração:** o token pessoal vai em `Authorization: {token}` **sem** a palavra "Bearer".
Só o token OAuth leva Bearer. Teste `GET /api/v2/user`. 100 req/min nos planos menores.
Fonte: `developer.clickup.com/docs/authentication`

**Pipedrive** — header `x-api-token`. "Account name > Company settings > Personal
preferences > API", atalho `app.pipedrive.com/settings/api`. Admin só é necessário pra
**liberar** o acesso a não-admins. Teste `GET /api/v2/deals`. O limite é orçamento de
tokens por dia, não requisições por segundo. **Use a v2:** endpoints da v1 tinham
desativação marcada pra 31/dez/2025.
Fonte: `pipedrive.readme.io/docs/how-to-find-the-api-token`

**Monday** — GraphQL, endpoint único, tudo por POST. Foto de perfil > Developers > API
token. Header `Authorization` com o valor cru, sem Bearer. Header `API-Version` no
formato `AAAA-MM`. Limite por orçamento de complexidade, não por contagem.
Fonte: `developer.monday.com/api-reference/docs/authentication`

**Trello** — precisa de **dois** valores, API Key e Token, normalmente em query string.
Só existe OAuth 1.0, não há 2.0. ⚠️ **Duas páginas oficiais divergem no caminho:**
`trello.com/apps/admin` numa, `trello.com/power-ups/admin` na outra. Provável rebranding.
Abra as duas e veja qual responde.
Fonte: `developer.atlassian.com/cloud/trello/guides/rest-api/authorization/`

### 🟡 Parece simples, mas trava

**Omie** — não é REST e não é OAuth: `app_key` e `app_secret` vão **dentro do corpo
JSON**, junto de `call` e `param`. Tudo é POST, GET é rejeitado. Doc literal: *"apenas
os usuários 'administradores' conseguem obter a chave de integração"*. Caminho: card do
aplicativo > engrenagem > Resumo do App > Chave de Integração. **Regenerar a chave
derruba todas as integrações ativas.** 10 falhas seguidas geram bloqueio de 30 min.
Fonte: `developer.omie.com.br/service-list/`

**HubSpot** — Private App token. A API Key legada morreu em 30/nov/2022. Settings >
Integrations > Private Apps, token na aba **Auth**. Doc literal: *"You must be a super
admin"*. Contatos exigem o escopo `crm.objects.contacts.read`.
Fonte: `developers.hubspot.com/docs/apps/legacy-apps/private-apps/overview`

**Kommo** — long-lived token na aba "Keys and scopes" da integração privada, validade de
1 dia a 5 anos. Só visível no momento da geração. Doc literal: *"only a user with account
administrator rights can create it"*. **7 requisições por segundo por IP**, e violação
repetida bloqueia o IP.
Fonte: `developers.kommo.com/docs/long-lived-token`

**Notion** — Settings > Connections, `•••` na conexão interna pra copiar o token. Doc
literal: *"Only Workspace owners will be able to access the Connections tab"*. Header
`Notion-Version` obrigatório em toda chamada (valor na doc: `2026-03-11`). Teste
`GET /v1/users/me`. **Lembre do compartilhamento manual da página** (ver armadilhas).
Fonte: `developers.notion.com/guides/get-started/authorization`

**Zendesk** — Basic Auth no formato `{email}/token:{api_token}`, em base64. Admin Center
> Apps and integrations > APIs > API tokens. **Trava dupla:** doc literal, *"you must be
an administrator **and** API token access must be turned on in your account"*. O toggle
exige aceitar os termos. Só em plano pago. Teste `GET /api/v2/users/me`.
Fonte: `developer.zendesk.com/api-reference/introduction/security-and-auth/`

**Movidesk** — Configuration > Account > Parameters, aba Environment. Query via OData
(`$filter`, `$top`, `$select`). ⚠️ **A doc oficial se contradiz:** os exemplos de
endpoint mandam o token em **query string** (`?token=...`), e a página de introdução
manda usar **Bearer Token** no Postman. Não invente uma reconciliação: teste os dois.
Fonte: `atendimento.movidesk.com/kb/en/article/130599/api-do-movidesk`

### 🔴 Projeto, não conexão

**Bling** — OAuth 2.0 Authorization Code, único grant. Central de Extensões > Área do
Integrador > Criar aplicativo. Homologação obrigatória pra uso além do teste de 30 dias.
Fonte: `developer.bling.com.br/aplicativos`

**Conta Azul** — OAuth 2.0, e o cadastro é num **portal separado**
(`developers-portal.contaazul.com`). Sem sandbox dedicado, sem webhooks (exige polling),
sem SDK oficial.
Fonte: `developers.contaazul.com/auth`

**Tiny (Olist ERP v3)** — OAuth 2.0, access token de 4 horas. Configurações > aba geral >
Aplicativos. Doc explícita de que **não** exige admin. Só a partir do **plano Construa**,
e exige a extensão "Gestão de Aplicativos" instalada.
Fonte: `api-docs.erp.olist.com/documentacao/comecando/autenticacao`

**Sankhya** — não é self-service: o portal é restrito a cliente, parceiro ou
"Desenvolvedor Credenciado", com CNPJ e aprovação. OAuth Client Credentials **mais**
header `X-Token`. **Exige whitelist de IP no firewall.**
Fonte: `developer.sankhya.com.br/reference/post_authenticate`

**Salesforce** — OAuth obrigatório na prática. Setup > App Manager > New Connected App.
Exige "Customize Application" e ("Modify All Data" ou "Manage Connected Apps"), ou seja,
System Administrator. Desde Spring '26 a criação de **novos** Connected Apps está
restrita, a doc recomenda External Client Apps.
Fonte: `developer.salesforce.com/docs/atlas.en-us.api_rest.meta/api_rest/intro_oauth_and_connected_apps.htm`

**Meta Ads** — app registrado no App Dashboard, obrigatório. Não existe chave de tela.
User Access Token pelo Graph API Explorer, ou System User Token pelo Business Suite (não
expira, melhor pra servidor). Versão v25.0. Conta de terceiro exige Business Verification.
Fonte: `developers.facebook.com/docs/marketing-api/get-started/authentication/`

**Google Ads** — a de maior atrito da lista. OAuth **mais** developer token com aprovação
(revisão típica de 5 dias úteis pro Basic, 10 pro Standard). Exige conta **gerenciadora**.
Não existe GET simples de teste: a consulta é GAQL via
`POST .../googleAds:searchStream`. Versão v24.
Fonte: `developers.google.com/google-ads/api/docs/get-started/dev-token`

**GA4 (Data API)** — OAuth ou service account, sempre via projeto no Google Cloud. Não
existe tela única: JSON key no Cloud Console **mais** conceder acesso à propriedade em
Admin > Property Access Management (vale pro e-mail da service account também). Teste
`POST /properties/{id}:runReport`. Quota por tokens, não por requisição.
Fonte: `developers.google.com/analytics/devguides/reporting/data/v1`

**Google Sheets** — a pegadinha central: a API key **só serve pra planilha pública**.
Doc literal, ela é pra *"anonymously access publicly available data"*. Planilha privada
exige OAuth ou service account, o que joga o Sheets no vermelho pra qualquer caso real
de empresa. Credencial no Cloud Console, não na interface do Sheets.
Fonte: `developers.google.com/workspace/guides/create-credentials`

---

## ⚠️ O que NÃO foi verificado

Trate cada item como desconhecido. **Não afirme nada sobre eles**, pesquise na hora.

| Ferramenta | O que falta | Por quê |
|---|---|---|
| RD Station CRM | caminho na tela pra gerar o token v1 | a página de ajuda linkada pela doc não carregou |
| RD Station CRM | se o token v1 vai em header ou query string | a página encontrada era do RD Station **Marketing**, produto diferente |
| RD Station CRM | se exige admin | doc só fala de "nível de visibilidade", que é escopo de dado |
| Monday | se guest consegue gerar token | as duas páginas oficiais de auth não mencionam guest |
| Monday | se o limite de queries/min é paralelo ou adicional ao de complexidade | a própria página traz os dois sem reconciliar |
| Movidesk | o formato real de autenticação | duas páginas oficiais se contradizem |
| Movidesk | rate limit, limite de registros e janela de 90 dias | a página específica deu 403 em todas as tentativas |
| Movidesk | se exige admin | sem menção nas páginas acessíveis |
| Meta Ads | se "Limited/Full Access" substitui ou coexiste com App Review | blog oficial e docs descrevem processos diferentes |
| Google Ads | se existe o nível "Explorer Access" | duas páginas oficiais do Google usam nomes diferentes |
| GA4 | nível mínimo de permissão na propriedade | a doc lida não especifica |
| Google Sheets | rate limit numérico | não checado nesta rodada |

---

## Como atualizar uma receita

Resolveu um caso que a receita não cobria, ou descobriu que a tela mudou? Edite a linha,
troque a data de "verificado em", e escreva a fonte oficial que você leu. Receita sem
fonte não vale, e receita sem data envelhece sem ninguém perceber.
