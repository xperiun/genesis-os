# -*- coding: utf-8 -*-
"""
PASSE 1 do /analisar: o profiler.

Lê 100% das linhas do arquivo e devolve um relatório de tamanho FIXO.
Determinístico, sem modelo de linguagem, sem chute. Existe porque amostrar as
primeiras N linhas é viés, não amostra: numa planilha de negócio brasileira as
armadilhas moram no corpo do arquivo, não no topo. Medido: num arquivo de 1.210
linhas com 5 subtotais, o primeiro subtotal só aparece na linha 241. Head de 50,
de 100 e de 250 não veem nenhum, e aí o modelo escreve um script confiante que
soma subtotal junto com transação e erra 3x em silêncio.

O que ele detecta (todas medidas, cada uma já produziu erro silencioso em teste):
  · linha real do cabeçalho (relatório de ERP começa com logo e 6 linhas de miolo)
  · linhas de agregação no meio dos dados (TOTAL/SUBTOTAL) -> inflam a soma
  · coluna de tipo misto, número junto com texto -> a limpeza padrão destrói o
    float que já estava certo (12450.80 vira 124508, inflou 37x no teste)
  · separador decimal ambíguo (1.234 é mil e duzentos ou é um vírgula dois?)
  · data ambígua (05/01 é 5 de janeiro ou 1 de maio?)
  · células mescladas, que o pandas descarta calado (sumiram 60% do dinheiro)
  · aba errada plausível (responder a meta achando que é a venda)
  · encoding e delimitador de CSV (export BR sai em cp1252 com ponto e vírgula)

Uso:
    python perfilar.py <arquivo> [--aba NOME] [--json]

Dependências: só a biblioteca padrão + openpyxl (pra .xlsx). Sem pandas de
propósito: o profiler precisa do acesso à célula crua, e pandas joga fora
exatamente o sinal de mescla que interessa aqui.
"""

import argparse
import csv
import io
import json
import os
import re
import sys
import unicodedata
from datetime import date, datetime

# Windows com console legado quebra em acento. Não deixa o profiler morrer por isso.
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

TETO_LINHAS_LIDAS = 2_000_000      # trava de sanidade, não limite de uso
TETO_AMOSTRA = 12                  # linhas mostradas por estrato
TETO_MARCADORES_LISTADOS = 15      # o relatório é de tamanho fixo, sempre

MARCADOR = re.compile(
    r"\b(total|subtotal|sub-total|soma|somatorio|acumulado|geral|consolidado|"
    r"resumo|média|media|saldo)\b", re.I
)

# Colunas cujo conteúdo não pode ser exibido sem antes passar pelo scan de PII.
SUSPEITA_PII = re.compile(
    r"\b(cpf|cnpj|rg|email|e-mail|telefone|celular|fone|whatsapp|endereco|"
    r"endereço|cep|salario|salário|remuneracao|remuneração|conta|agencia|"
    r"agência|cartao|cartão|nascimento)\b", re.I
)


# ---------------------------------------------------------------- utilidades

def _norm(v):
    """Minúscula sem acento. Usado só pra casar padrão, nunca pra exibir."""
    s = unicodedata.normalize("NFKD", str(v))
    return s.encode("ascii", "ignore").decode("ascii").lower().strip()


def _vazio(v):
    return v is None or (isinstance(v, str) and not v.strip())


def _preenchidas(linha):
    return sum(1 for c in linha if not _vazio(c))


def _texto_curto(v):
    return isinstance(v, str) and 0 < len(v.strip()) <= 60


# ------------------------------------------------------- análise de conteúdo

def _linha_de_agregacao(linha):
    """Alguma célula de texto marca essa linha como total/subtotal?"""
    for c in linha:
        if isinstance(c, str) and MARCADOR.search(_norm(c)):
            return c.strip()
    return None


def _tem_numero(linha):
    """A linha carrega algum valor numérico (nativo ou em texto)?"""
    for c in linha:
        if isinstance(c, bool):
            continue
        if isinstance(c, (int, float)):
            return True
        if isinstance(c, str) and c.strip():
            if (_num_br(c) is not None or _num_us(c) is not None
                    or _num_simples(c) is not None):
                return True
    return False


def _agregacao_sem_rotulo(linha, largura_tipica):
    """Linha com CARA de agregação, mas sem palavra que a marque.

    O `_linha_de_agregacao` acha por PALAVRA (total, subtotal, soma, saldo...), que é o
    vocabulário que ERP brasileiro escreve. Quando o subtotal vem SEM rótulo (só negrito, ou
    "Acum.", ou a célula do rótulo em branco), ele passava batido e entrava na soma sem
    ninguém ver, que é exatamente a classe de erro que esta skill existe pra matar.

    O sinal estrutural: a linha preenche bem MENOS colunas que o corpo (subtotal costuma ser
    rótulo + valor, o resto vazio) e mesmo assim carrega número.

    É SUSPEITA, não veredito. Por isso ela só vira ARMADILHA REPORTADA e **não** é excluída
    do cálculo por conta própria: descartar uma linha boa por engano SUBESTIMA o total, que é
    tão errado quanto somar subtotal, e erra pro lado que a reconciliação não pega (o valor
    some sem deixar rastro pra conferir). Quem decide é o passe 2, agora sabendo que existe.
    """
    if largura_tipica < 3:
        return False
    p = _preenchidas(linha)
    return 0 < p <= max(2, largura_tipica // 3) and _tem_numero(linha)


def _num_br(s):
    """1.234,56 -> 1234.56. Só aceita se o padrão for inequivocamente BR."""
    s = s.strip()
    if not re.fullmatch(r"-?\s*R?\$?\s*[\d.]+,\d+", s):
        return None
    s = re.sub(r"[R$\s]", "", s).replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def _num_us(s):
    """1,234.56 ou 1234.56 -> 1234.56."""
    s = re.sub(r"[R$\s]", "", s.strip())
    if not re.fullmatch(r"-?[\d,]*\.?\d+", s):
        return None
    try:
        return float(s.replace(",", ""))
    except ValueError:
        return None


def _num_simples(s):
    """Só dígitos, sem separador. Não desambigua nada, mas conta como numérico."""
    s = re.sub(r"[R$\s]", "", s.strip())
    return float(s) if re.fullmatch(r"-?\d+", s) else None


def _perfil_numerico(valores):
    """
    Devolve o diagnóstico da coluna. O campo que mais importa é `misto`:
    quando a coluna tem float nativo E texto junto, a limpeza padrão
    (replace('.','').replace(',','.')) conserta o texto e DESTRÓI o float.
    Foi o erro de 37x medido no teste.
    """
    nativos, textos, vazios = [], [], 0
    for v in valores:
        if _vazio(v):
            vazios += 1
        elif isinstance(v, (int, float)) and not isinstance(v, bool):
            nativos.append(v)
        else:
            textos.append(str(v))

    ok_br = sum(1 for t in textos if _num_br(t) is not None)
    ok_us = sum(1 for t in textos if _num_us(t) is not None)
    ok_simples = sum(1 for t in textos if _num_simples(t) is not None)
    parseavel = sum(
        1 for t in textos
        if _num_br(t) is not None or _num_us(t) is not None or _num_simples(t) is not None
    )
    nao_numerico = len(textos) - parseavel

    # Ambiguidade do separador: "1.234" sozinho pode ser milhar ou decimal.
    # Se existir pelo menos um valor com vírgula decimal, o formato é BR provado.
    tem_virgula_decimal = any(re.search(r",\d{1,2}\b", t) for t in textos)
    tem_ponto_decimal_curto = any(re.search(r"\.\d{1,2}\b", t) for t in textos)
    so_ponto_milhar = any(re.fullmatch(r"-?\d{1,3}(\.\d{3})+", t.strip()) for t in textos)

    if tem_virgula_decimal:
        convencao, prova = "BR", "achei valor com vírgula decimal (ex: 1.234,56)"
    elif tem_ponto_decimal_curto and not so_ponto_milhar:
        convencao, prova = "US", "achei ponto decimal com 1 ou 2 casas e nenhum milhar por ponto"
    elif so_ponto_milhar:
        convencao, prova = "AMBIGUO", "só achei ponto agrupando de 3 em 3, pode ser milhar ou decimal"
    else:
        convencao, prova = "INDEFINIDO", "sem separador suficiente pra provar"

    total_valores = len(nativos) + len(textos)
    return {
        "vazios": vazios,
        "numeros_nativos": len(nativos),
        "textos": len(textos),
        "texto_parseavel": parseavel,
        "texto_nao_numerico": nao_numerico,
        "parse_br": ok_br,
        "parse_us": ok_us,
        "parse_simples": ok_simples,
        "misto": len(nativos) > 0 and parseavel > 0,
        "convencao": convencao,
        "prova_convencao": prova,
        "e_numerica": total_valores > 0 and (len(nativos) + parseavel) / total_valores >= 0.7,
        "perda_se_coercao": nao_numerico,
    }


def _perfil_data(valores):
    """
    dd/mm ou mm/dd? Só é possível PROVAR quando existe algum componente > 12.
    Sem prova, a skill tem que perguntar, nunca chutar. Medido: sem dayfirst,
    6 de 7 linhas caíram no mês errado e o agrupamento por trimestre mentiu.
    """
    padrao = re.compile(r"^\s*(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})")
    primeiro_alto = segundo_alto = casadas = 0
    nativas = 0
    for v in valores:
        if isinstance(v, (datetime, date)):
            nativas += 1
            continue
        if _vazio(v):
            continue
        m = padrao.match(str(v))
        if not m:
            continue
        casadas += 1
        a, b = int(m.group(1)), int(m.group(2))
        if a > 12:
            primeiro_alto += 1
        if b > 12:
            segundo_alto += 1

    if not casadas and not nativas:
        return None
    if nativas and not casadas:
        veredito, detalhe = "NATIVA", "a célula já é data de verdade, sem ambiguidade de formato"
    elif primeiro_alto and segundo_alto:
        veredito, detalhe = "INCONSISTENTE", "achei dia > 12 nas duas posições, a coluna mistura formatos"
    elif primeiro_alto:
        veredito, detalhe = "BR", f"{primeiro_alto} valor(es) com dia > 12 na 1ª posição, dayfirst confirmado"
    elif segundo_alto:
        veredito, detalhe = "US", f"{segundo_alto} valor(es) > 12 na 2ª posição, mês vem primeiro"
    else:
        veredito, detalhe = "AMBIGUO", "nenhum componente passa de 12, não dá pra provar o formato"
    return {"veredito": veredito, "detalhe": detalhe, "texto": casadas, "nativas": nativas}


# ----------------------------------------------------------------- cabeçalho

def _merges_no_corpo(merges, linha_cabecalho):
    """
    Só interessa mescla que cai DENTRO dos dados. Relatório de ERP quase sempre
    mescla a razão social e o título no topo, e isso é inofensivo: fica acima do
    cabeçalho e não entra em nenhum agrupamento. Marcar aquilo como P0 é alarme
    falso, e alarme falso ensina o modelo a ignorar o profiler.
    """
    dentro = []
    for r in merges:
        m = re.search(r"[A-Z]+(\d+):[A-Z]+(\d+)", str(r))
        if not m:
            continue
        if max(int(m.group(1)), int(m.group(2))) > linha_cabecalho:
            dentro.append(str(r))
    return dentro


def _achar_cabecalho(linhas, limite=25):
    """
    Relatório de ERP tem logo, razão social e duas linhas em branco antes da
    tabela. O cabeçalho real é a primeira linha densa, feita só de texto curto,
    seguida de outra linha densa.
    """
    if not linhas:
        return 0, 0.0
    largura = max((len(l) for l in linhas[:limite]), default=0)
    if not largura:
        return 0, 0.0

    melhor, melhor_nota = 0, -1.0
    for i, linha in enumerate(linhas[:limite]):
        n = _preenchidas(linha)
        if n < 2:
            continue
        densidade = n / largura
        textos = sum(1 for c in linha if _texto_curto(c))
        proporcao_texto = textos / max(n, 1)
        seguinte = _preenchidas(linhas[i + 1]) / largura if i + 1 < len(linhas) else 0
        nota = densidade * 2 + proporcao_texto * 2 + min(seguinte, 1.0)
        # Cabeçalho quase nunca é a última coisa do arquivo.
        if i + 2 >= len(linhas):
            nota -= 1
        if nota > melhor_nota:
            melhor, melhor_nota = i, nota
    confianca = max(0.0, min(1.0, melhor_nota / 5.0))
    return melhor, round(confianca, 2)


# -------------------------------------------------------------------- leitura

def _ler_xlsx(caminho):
    try:
        import openpyxl
    except ImportError:
        raise SystemExit(
            "ERRO: preciso do openpyxl pra ler .xlsx.\n"
            "  Instale com: pip install openpyxl\n"
            "  (o Genesis instala sozinho no first-run, isso só aparece rodando na mão)"
        )
    wb = openpyxl.load_workbook(caminho, data_only=True, read_only=False)
    abas = []
    for ws in wb.worksheets:
        linhas = []
        for i, linha in enumerate(ws.iter_rows(values_only=True)):
            if i >= TETO_LINHAS_LIDAS:
                break
            linhas.append(list(linha))
        merges = [str(r) for r in getattr(ws, "merged_cells", []).ranges] \
            if hasattr(ws, "merged_cells") else []
        abas.append({"nome": ws.title, "linhas": linhas, "merges": merges})
    wb.close()
    return abas


def _ler_csv(caminho):
    """Export BR sai em cp1252 com ponto e vírgula. Detecta os dois."""
    bruto = open(caminho, "rb").read()
    encoding, texto = None, None
    for tentativa in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            texto = bruto.decode(tentativa)
            encoding = tentativa
            break
        except UnicodeDecodeError:
            continue
    if texto is None:
        raise SystemExit("ERRO: não consegui decodificar o arquivo em nenhum encoding conhecido.")

    cabeca = "\n".join(texto.splitlines()[:30])
    try:
        delim = csv.Sniffer().sniff(cabeca, delimiters=";,\t|").delimiter
    except Exception:
        delim = ";" if cabeca.count(";") > cabeca.count(",") else ","

    linhas = []
    for i, linha in enumerate(csv.reader(io.StringIO(texto), delimiter=delim)):
        if i >= TETO_LINHAS_LIDAS:
            break
        linhas.append(linha)
    return [{
        "nome": os.path.basename(caminho),
        "linhas": linhas,
        "merges": [],
        "encoding": encoding,
        "delimitador": delim,
    }]


# -------------------------------------------------------------------- perfil

def _parece_lixo(aba):
    """Aba de instruções/capa: pouquíssimo conteúdo e nenhuma cara de tabela."""
    uteis = [l for l in aba["linhas"] if _preenchidas(l)]
    if len(uteis) <= 3:
        return True
    largura = max((_preenchidas(l) for l in uteis), default=0)
    return largura <= 1


def _escolher_aba(abas, pedida):
    if pedida:
        for a in abas:
            if a["nome"].strip().lower() == pedida.strip().lower():
                return a, f"você pediu a aba '{pedida}'"
        raise SystemExit(
            f"ERRO: não achei a aba '{pedida}'. Abas do arquivo: "
            + ", ".join(repr(a['nome']) for a in abas)
        )
    candidatas = [a for a in abas if not _parece_lixo(a)]
    if not candidatas:
        return abas[0], "nenhuma aba parece tabela, peguei a primeira"
    melhor = max(candidatas, key=lambda a: sum(1 for l in a["linhas"] if _preenchidas(l) >= 2))
    if len(candidatas) > 1:
        motivo = (f"escolhi por ter mais linhas de tabela, entre {len(candidatas)} candidatas. "
                  f"Se a resposta for sobre outra, rode de novo com --aba")
    else:
        motivo = "única aba com cara de tabela"
    return melhor, motivo


def perfilar(caminho, aba_pedida=None):
    ext = os.path.splitext(caminho)[1].lower()
    if ext in (".xlsx", ".xlsm"):
        abas = _ler_xlsx(caminho)
    elif ext in (".csv", ".txt", ".tsv"):
        abas = _ler_csv(caminho)
    else:
        raise SystemExit(
            f"ERRO: não sei ler '{ext}'. Formatos suportados: .xlsx, .xlsm, .csv, .tsv.\n"
            "  .xls antigo: abra no Excel e salve como .xlsx.\n"
            "  .pdf ou .docx: esses o Claude lê direto, não precisa deste profiler."
        )

    aba, motivo_aba = _escolher_aba(abas, aba_pedida)
    linhas = aba["linhas"]
    i_cab, confianca = _achar_cabecalho(linhas)
    # A partir daqui, "merges" quer dizer mescla que cai nos dados. As de cima
    # (razão social, título do relatório) são ruído visual, não risco de cálculo.
    merges_relevantes = _merges_no_corpo(aba["merges"], i_cab + 1)
    merges_decorativos = len(aba["merges"]) - len(merges_relevantes)

    cabecalho = linhas[i_cab] if i_cab < len(linhas) else []
    nomes = []
    for j, c in enumerate(cabecalho):
        nomes.append(str(c).strip() if not _vazio(c) else f"(coluna {j + 1} sem nome)")

    corpo = linhas[i_cab + 1:]
    corpo_util = [l for l in corpo if _preenchidas(l)]
    vazias_no_meio = len(corpo) - len(corpo_util)

    # Linhas de agregação: a armadilha que infla a soma, e ao mesmo tempo o
    # gabarito de graça pra provar o cálculo no passe 3.
    agregacoes = []
    for k, linha in enumerate(corpo_util):
        marca = _linha_de_agregacao(linha)
        if marca:
            agregacoes.append({
                "linha_no_arquivo": i_cab + 2 + corpo.index(linha) if linha in corpo else None,
                "posicao_no_corpo": k,
                "marcador": marca,
                "conteudo": [("" if _vazio(c) else str(c)) for c in linha][:8],
            })

    limpas = [l for l in corpo_util if not _linha_de_agregacao(l)]

    # Agregação SEM rótulo: o subtotal que não escreveu "total" e por isso escapou do
    # MARCADOR. Continua DENTRO de `limpas` (não removo por suspeita, ver
    # `_agregacao_sem_rotulo`), mas vira armadilha reportada pro passe 2 decidir.
    _cont = [_preenchidas(l) for l in limpas]
    largura_tipica = max(set(_cont), key=_cont.count) if _cont else 0
    suspeitas_agregacao = [
        {"posicao_no_corpo": k,
         "preenchidas": _preenchidas(linha),
         "conteudo": [("" if _vazio(c) else str(c)) for c in linha][:8]}
        for k, linha in enumerate(limpas)
        if _agregacao_sem_rotulo(linha, largura_tipica)
    ]

    colunas = []
    for j, nome in enumerate(nomes):
        valores_limpos = [l[j] if j < len(l) else None for l in limpas]
        num = _perfil_numerico(valores_limpos)
        dat = _perfil_data(valores_limpos)
        amostra = [str(v) for v in valores_limpos if not _vazio(v)][:4]
        colunas.append({
            "indice": j,
            "nome": nome,
            "numerico": num,
            "data": dat,
            "possivel_pii": bool(SUSPEITA_PII.search(_norm(nome))),
            "amostra": amostra,
        })

    # Amostra estratificada: topo, miolo e fim, sem repetir linha quando o
    # arquivo é pequeno demais pra ter três estratos distintos. Fixa, não
    # aleatória, pra o relatório ser reprodutível entre execuções.
    def _fatiar(ls):
        return [[("" if _vazio(c) else str(c)) for c in l][:8] for l in ls]

    n = len(limpas)
    if n <= 12:
        faixas = {"topo": range(n), "miolo": range(0), "fim": range(0)}
    else:
        meio = n // 2
        faixas = {
            "topo": range(0, 5),
            "miolo": range(meio - 2, meio + 3),
            "fim": range(n - 5, n),
        }
    amostra = {k: _fatiar([limpas[i] for i in v]) for k, v in faixas.items()}
    amostra["agregacao"] = [a["conteudo"] for a in agregacoes[:TETO_AMOSTRA]]

    try:
        import pandas  # noqa: F401
        tem_pandas = True
    except ImportError:
        tem_pandas = False

    return {
        "arquivo": {
            "caminho": os.path.abspath(caminho),
            "nome": os.path.basename(caminho),
            "bytes": os.path.getsize(caminho),
            "formato": ext,
            "encoding": aba.get("encoding"),
            "delimitador": aba.get("delimitador"),
        },
        "ambiente": {
            "python": sys.version.split()[0],
            "pandas_disponivel": tem_pandas,
        },
        "abas": [{
            "nome": a["nome"],
            "linhas": len(a["linhas"]),
            "parece_lixo": _parece_lixo(a),
            "escolhida": a is aba,
        } for a in abas],
        "aba_escolhida": {"nome": aba["nome"], "motivo": motivo_aba},
        "cabecalho": {
            "linha": i_cab + 1,
            "confianca": confianca,
            "colunas": nomes,
        },
        "contagem": {
            "linhas_totais_na_aba": len(linhas),
            "linhas_antes_do_cabecalho": i_cab,
            "linhas_de_dado": len(limpas),
            "linhas_de_agregacao": len(agregacoes),
            "linhas_em_branco_no_meio": vazias_no_meio,
        },
        "agregacoes": agregacoes[:TETO_MARCADORES_LISTADOS],
        "agregacoes_omitidas": max(0, len(agregacoes) - TETO_MARCADORES_LISTADOS),
        "agregacoes_sem_rotulo": suspeitas_agregacao[:TETO_MARCADORES_LISTADOS],
        "merges": merges_relevantes[:TETO_MARCADORES_LISTADOS],
        "merges_total": len(merges_relevantes),
        "merges_decorativos": merges_decorativos,
        "colunas": colunas,
        "amostra": amostra,
        "armadilhas": _armadilhas(merges_relevantes, colunas, agregacoes, confianca,
                                  vazias_no_meio, suspeitas_agregacao),
    }


def _armadilhas(merges, colunas, agregacoes, confianca_cab, vazias, sem_rotulo=()):
    """Veredito priorizado. P0 = produz número errado sem avisar."""
    achados = []

    if agregacoes:
        achados.append(("P0", "agregacao",
                        f"{len(agregacoes)} linha(s) de TOTAL/SUBTOTAL no meio dos dados. "
                        f"Somar junto infla o resultado (medido: 3x). Exclua do cálculo e "
                        f"depois use o TOTAL GERAL pra CONFERIR o seu número."))

    if sem_rotulo:
        achados.append(("P0", "agregacao_sem_rotulo",
                        f"{len(sem_rotulo)} linha(s) com CARA de agregação mas SEM rótulo "
                        f"(preenchem poucas colunas e carregam número, porém não dizem "
                        f"'total'/'subtotal'). Elas CONTINUAM no cálculo: não removi por "
                        f"suspeita, porque descartar linha boa subestima o total e some sem "
                        f"deixar rastro. OLHE as linhas listadas em `agregacoes_sem_rotulo` "
                        f"e decida. Se forem subtotal, exclua e reconcilie."))

    if merges:
        achados.append(("P0", "merge",
                        f"{len(merges)} intervalo(s) de célula mesclada DENTRO dos dados. O pandas "
                        f"transforma em vazio sem avisar e o agrupamento perde linha "
                        f"(medido: sumiram 60% do valor). Preencha pra baixo antes de agrupar."))

    for c in colunas:
        n = c["numerico"]
        if n["misto"]:
            achados.append(("P0", "tipo_misto",
                            f"coluna '{c['nome']}' tem {n['numeros_nativos']} número(s) nativo(s) "
                            f"E {n['texto_parseavel']} valor(es) em texto. A limpeza padrão "
                            f"replace('.','').replace(',','.') conserta o texto e DESTRÓI o "
                            f"float (medido: inflou 37x). Trate cada tipo separado."))
        if n["e_numerica"] and n["convencao"] == "AMBIGUO":
            achados.append(("P0", "separador_ambiguo",
                            f"coluna '{c['nome']}': {n['prova_convencao']}. Não dá pra provar se "
                            f"1.234 é mil duzentos e trinta e quatro ou um vírgula dois. PERGUNTE."))
        if n["e_numerica"] and n["perda_se_coercao"]:
            achados.append(("P1", "perda_coercao",
                            f"coluna '{c['nome']}': {n['perda_se_coercao']} valor(es) não viram "
                            f"número. Com errors='coerce' eles somem calados. Liste antes de descartar."))
        d = c["data"]
        if d and d["veredito"] == "AMBIGUO":
            achados.append(("P0", "data_ambigua",
                            f"coluna '{c['nome']}': {d['detalhe']}. 05/01 pode ser 5 de janeiro "
                            f"ou 1 de maio. PERGUNTE antes de agrupar por mês."))
        if d and d["veredito"] == "INCONSISTENTE":
            achados.append(("P0", "data_inconsistente",
                            f"coluna '{c['nome']}': {d['detalhe']}. Parte das linhas vai cair no "
                            f"mês errado independente do formato escolhido."))
        if c["possivel_pii"]:
            achados.append(("P1", "pii",
                            f"coluna '{c['nome']}' tem nome de dado pessoal. Mascare antes de "
                            f"mostrar em tela, relatório ou apresentação."))

    if confianca_cab < 0.55:
        achados.append(("P1", "cabecalho",
                        f"confiança baixa ({confianca_cab}) na linha de cabeçalho. Confira as "
                        f"colunas listadas antes de seguir."))

    if vazias > 0:
        achados.append(("P2", "linhas_vazias",
                        f"{vazias} linha(s) em branco no meio dos dados. Costuma ser separador "
                        f"visual de bloco, e frequentemente vem junto de subtotal."))

    ordem = {"P0": 0, "P1": 1, "P2": 2}
    achados.sort(key=lambda a: ordem[a[0]])
    return [{"severidade": s, "tipo": t, "detalhe": d} for s, t, d in achados]


# ------------------------------------------------------------------ renderizar

def _linha_tabela(cells, larg=18):
    return " | ".join((c or "")[:larg].ljust(min(larg, 18)) for c in cells)


def renderizar(rel):
    o = []
    a = rel["arquivo"]
    o.append("=" * 78)
    o.append(f"PERFIL DO ARQUIVO: {a['nome']}")
    o.append("=" * 78)
    o.append(f"  {a['bytes']:,} bytes, formato {a['formato']}"
             + (f", encoding {a['encoding']}, delimitador '{a['delimitador']}'"
                if a.get("encoding") else ""))
    o.append(f"  python {rel['ambiente']['python']}, pandas "
             + ("disponível" if rel["ambiente"]["pandas_disponivel"] else "AUSENTE (use csv/openpyxl)"))
    o.append("")

    if len(rel["abas"]) > 1:
        o.append("ABAS")
        for ab in rel["abas"]:
            marca = " <- ESCOLHIDA" if ab["escolhida"] else (" (parece capa/instrução)" if ab["parece_lixo"] else "")
            o.append(f"  - {ab['nome']}: {ab['linhas']} linhas{marca}")
        o.append(f"  motivo: {rel['aba_escolhida']['motivo']}")
        o.append("")

    c = rel["contagem"]
    o.append("ESTRUTURA")
    o.append(f"  cabeçalho na linha {rel['cabecalho']['linha']} (confiança {rel['cabecalho']['confianca']})")
    o.append(f"  {c['linhas_de_dado']} linhas de dado, {c['linhas_de_agregacao']} de agregação, "
             f"{c['linhas_em_branco_no_meio']} em branco, {c['linhas_antes_do_cabecalho']} de miolo antes do cabeçalho")
    if rel["merges_total"]:
        o.append(f"  {rel['merges_total']} intervalo(s) mesclado(s): {', '.join(rel['merges'][:6])}"
                 + (" ..." if rel["merges_total"] > 6 else ""))
    o.append("")

    o.append("COLUNAS")
    for col in rel["colunas"]:
        n, d = col["numerico"], col["data"]
        if n["e_numerica"]:
            tipo = f"numérica ({n['convencao']})"
        elif d:
            tipo = f"data ({d['veredito']})"
        else:
            tipo = "texto"
        flag = " [PII?]" if col["possivel_pii"] else ""
        o.append(f"  {col['indice'] + 1:>2}. {col['nome'][:32]:<32} {tipo}{flag}")
        if col["amostra"]:
            o.append(f"      ex: {' · '.join(x[:20] for x in col['amostra'])}")
    o.append("")

    if rel["agregacoes"]:
        o.append("LINHAS DE AGREGAÇÃO ENCONTRADAS (excluir do cálculo, usar pra conferir)")
        for ag in rel["agregacoes"]:
            o.append(f"  - {' | '.join(x for x in ag['conteudo'] if x)[:70]}")
        if rel["agregacoes_omitidas"]:
            o.append(f"  ... e mais {rel['agregacoes_omitidas']}")
        o.append("")

    o.append("AMOSTRA ESTRATIFICADA (topo, miolo e fim, só linhas de dado)")
    for rotulo, chave in (("topo ", "topo"), ("miolo", "miolo"), ("fim  ", "fim")):
        for linha in rel["amostra"][chave]:
            o.append(f"  {rotulo} {_linha_tabela(linha)}")
    o.append("")

    o.append("=" * 78)
    o.append("ARMADILHAS")
    o.append("=" * 78)
    if not rel["armadilhas"]:
        o.append("  nenhuma detectada. Ainda assim, reconcilie o resultado antes de mostrar.")
    for arm in rel["armadilhas"]:
        o.append(f"  [{arm['severidade']}] {arm['detalhe']}")
    o.append("")
    p0 = [x for x in rel["armadilhas"] if x["severidade"] == "P0"]
    if p0:
        o.append(f"  >> {len(p0)} armadilha(s) P0. Cada uma dessas produz número errado SEM AVISAR.")
        o.append("  >> Trate todas no script antes de mostrar qualquer resultado.")
    return "\n".join(o)


def main():
    ap = argparse.ArgumentParser(description="Passe 1 do /analisar: perfila a planilha antes de analisar.")
    ap.add_argument("arquivo")
    ap.add_argument("--aba", default=None, help="nome da aba (padrão: escolhe a que tem cara de tabela)")
    ap.add_argument("--json", action="store_true", help="saída em JSON em vez de texto")
    args = ap.parse_args()

    if not os.path.exists(args.arquivo):
        raise SystemExit(f"ERRO: não achei o arquivo: {args.arquivo}")

    rel = perfilar(args.arquivo, args.aba)
    if args.json:
        print(json.dumps(rel, ensure_ascii=False, indent=2, default=str))
    else:
        print(renderizar(rel))


if __name__ == "__main__":
    main()
