# -*- coding: utf-8 -*-
"""
PASSE 3 do /analisar: a reconciliação.

Regra da casa: nenhum número chega na tela sem a própria certidão de nascimento.
Se a análise não consegue enunciar de onde o número veio, quantas linhas entraram,
quantas ficaram de fora e por quê, ela não tem direito de imprimir.

Isso existe porque erro barulhento é barato (o traceback aparece e alguém
conserta) e erro silencioso é o único que custa. Todos os casos medidos, subtotal
somado junto, coluna de tipo misto, mescla apagada, data no formato errado,
produzem um número plausível e errado. Nenhum deles levanta exceção.

A inversão que faz isso funcionar: a linha "TOTAL GERAL" que envenena a soma
ingênua é gabarito de graça. Tire ela da conta e depois use ela pra PROVAR a
conta. O arquivo quase sempre já traz a própria resposta.

Uso como biblioteca, dentro do script que o passe 2 escreve:

    from reconciliar import Auditoria

    a = Auditoria("Faturamento total 2025")
    vals = a.numeros(coluna_bruta, convencao="BR", contexto="coluna Faturamento")
    total = a.soma(vals)
    a.conferir(total, referencia=98287.60, fonte="linha TOTAL GERAL da planilha")
    print(a.certidao(total, moeda=True))

Sem dependência externa. Funciona com lista de valores crus, não exige pandas.
"""

import re
import sys
import unicodedata

# O console legado do Windows (cp1252) transforma "cálculo" em "c?lculo" e o
# relatório parece quebrado. Como TODO script gerado importa este módulo, o
# conserto aqui cobre todos eles de uma vez.
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

__all__ = ["Auditoria", "mascarar", "parse_numero", "MascaraPII"]


# ------------------------------------------------------------------ números

def parse_numero(v, convencao="BR"):
    """
    Converte um valor cru em float. Devolve None quando não dá, NUNCA zero:
    virar zero calado é exatamente como o dinheiro some do relatório.

    convencao='BR'    -> 1.234,56
    convencao='US'    -> 1,234.56
    convencao='AUTO'  -> tenta provar pelo próprio valor, e recusa se ambíguo
    """
    if v is None:
        return None
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)          # já é número: NÃO mexer. Aqui morava o erro de 37x.

    s = re.sub(r"[R$\s ]", "", str(v)).strip()
    if not s or s in ("-", "--"):
        return None

    tem_ponto, tem_virgula = "." in s, "," in s
    if convencao == "AUTO":
        if tem_ponto and tem_virgula:
            convencao = "BR" if s.rfind(",") > s.rfind(".") else "US"
        elif tem_virgula:
            convencao = "BR"
        elif re.fullmatch(r"-?\d{1,3}(\.\d{3})+", s):
            return None          # 1.234 sozinho é ambíguo. Não chute, devolva None.
        else:
            convencao = "US"

    if convencao == "BR":
        s = s.replace(".", "").replace(",", ".")
    else:
        s = s.replace(",", "")
    try:
        return float(s)
    except ValueError:
        return None


# ---------------------------------------------------------------------- PII

class MascaraPII:
    """
    Mascara dado pessoal antes de qualquer render. Não é bug, é risco jurídico:
    planilha de trabalho real tem nome, CPF, e-mail e salário, e a tela pode
    estar sendo projetada ou gravada.
    """
    CPF = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")
    CNPJ = re.compile(r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b")
    EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b")
    # Sem \b nas pontas: "(" não é caractere de palavra, então a fronteira falha
    # em "(11) 98765-4321" e o match começa no "1", deixando o parêntese pra trás
    # ("((**) *****-****"). Lookaround por dígito resolve e ainda segura o "+55".
    TELEFONE = re.compile(r"(?<![\d\w])(?:\+?55[\s-]?)?\(?\d{2}\)?[\s-]?9?\d{4}[-\s]?\d{4}(?!\d)")

    @classmethod
    def achar(cls, texto):
        t = str(texto)
        achados = []
        for nome, rx in (("CPF", cls.CPF), ("CNPJ", cls.CNPJ),
                         ("e-mail", cls.EMAIL), ("telefone", cls.TELEFONE)):
            if rx.search(t):
                achados.append(nome)
        return achados


def mascarar(valor):
    """Devolve o valor com o dado pessoal escondido, preservando o formato."""
    t = str(valor)
    t = MascaraPII.CPF.sub("***.***.***-**", t)
    t = MascaraPII.CNPJ.sub("**.***.***/****-**", t)
    t = MascaraPII.EMAIL.sub(lambda m: (m.group(0)[0] + "***@" + m.group(0).split("@")[1]), t)
    t = MascaraPII.TELEFONE.sub("(**) *****-****", t)
    return t


# ---------------------------------------------------------------- auditoria

def _norm(s):
    return unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode("ascii").lower()


class Auditoria:
    """
    Acumula a evidência do cálculo e decide se ele pode ou não ser mostrado.
    Se `bloqueado()` for True, o número NÃO vai pra tela: vai a divergência.
    """

    def __init__(self, pergunta):
        self.pergunta = pergunta
        self.linhas_lidas = 0
        self.linhas_usadas = 0
        self.excluidas = []          # (motivo, quantidade)
        self.descartes = []          # valores que não viraram número
        self.provas = []             # reconciliações que bateram
        self.divergencias = []       # reconciliações que NÃO bateram
        self.avisos = []
        self.pii_detectada = set()

    # -- ingestão ---------------------------------------------------------

    def numeros(self, valores, convencao="BR", contexto="a coluna"):
        """
        Converte, contando a perda. Nunca usa 'coerce e segue': todo valor que
        não vira número é registrado com o conteúdo original, porque descartar
        em silêncio é como o total encolhe sem ninguém ver.
        """
        self.linhas_lidas += len(valores)
        limpos = []
        for v in valores:
            if v is None or (isinstance(v, str) and not v.strip()):
                continue
            n = parse_numero(v, convencao)
            if n is None:
                self.descartes.append(str(v)[:40])
            else:
                limpos.append(n)
        if self.descartes:
            self.avisos.append(
                f"{len(self.descartes)} valor(es) de {contexto} não viraram número. "
                f"Exemplos: {', '.join(self.descartes[:3])}"
            )
        self.linhas_usadas = len(limpos)
        return limpos

    def excluir(self, quantidade, motivo):
        """Registra linhas tiradas do cálculo de propósito (subtotal, rodapé)."""
        if quantidade:
            self.excluidas.append((motivo, quantidade))

    def pii(self, amostra_de_valores):
        for v in amostra_de_valores:
            for tipo in MascaraPII.achar(v):
                self.pii_detectada.add(tipo)

    # -- cálculo ----------------------------------------------------------

    def soma(self, valores):
        self.linhas_usadas = len(valores)
        return round(sum(valores), 2)

    def media(self, valores):
        if not valores:
            self.avisos.append("média pedida sobre zero linhas válidas")
            return None
        self.linhas_usadas = len(valores)
        return round(sum(valores) / len(valores), 2)

    # -- prova ------------------------------------------------------------

    def conferir(self, valor, referencia, fonte, tolerancia=0.01):
        """
        Compara o resultado com um total independente vindo do próprio arquivo.
        Bateu, vira prova. Não bateu, vira divergência e BLOQUEIA a exibição.
        """
        if referencia in (None, 0):
            self.avisos.append(f"sem referência pra conferir contra ({fonte})")
            return False
        dif = abs(valor - referencia)
        rel = dif / max(abs(referencia), 1)
        if rel <= tolerancia:
            self.provas.append(f"confere com {fonte}: {_fmt(referencia)}, diferença {_fmt(dif)}")
            return True
        # O valor calculado aparece de propósito: sem ele não dá pra investigar a
        # divergência. Mas vem rotulado como não utilizável, senão vira resposta
        # na mão de quem só bateu o olho.
        self.divergencias.append(
            f"NÃO confere com {fonte}. Meu cálculo deu {_fmt(valor)} "
            f"(NÃO USE ESTE NÚMERO), a referência do arquivo diz {_fmt(referencia)}. "
            f"Diferença de {_fmt(dif)}, {rel * 100:.1f}%"
        )
        return False

    def conferir_partes(self, total, partes, rotulo="soma das partes"):
        """A soma dos grupos tem que dar o total. Pega mescla apagada e linha perdida."""
        soma_partes = round(sum(partes.values()), 2)
        return self.conferir(total, soma_partes, f"{rotulo} ({len(partes)} grupos)")

    # -- veredito ---------------------------------------------------------

    def bloqueado(self):
        return bool(self.divergencias)

    def certidao(self, valor=None, moeda=False):
        """A certidão de nascimento do número. Sempre acompanha o resultado."""
        o = []
        if self.bloqueado():
            o.append("!! NÚMERO NÃO LIBERADO PARA EXIBIÇÃO")
            for d in self.divergencias:
                o.append(f"   {d}")
            o.append("   Antes de mostrar qualquer valor, resolva a divergência acima.")
            return "\n".join(o)

        if valor is not None:
            o.append(f"{'R$ ' if moeda else ''}{_fmt(valor)}")
        o.append(f"  - {self.pergunta}")
        o.append(f"  - {self.linhas_usadas} linha(s) entraram no cálculo, de {self.linhas_lidas} lidas")
        for motivo, qtd in self.excluidas:
            o.append(f"  - {qtd} linha(s) fora do cálculo: {motivo}")
        if self.descartes:
            o.append(f"  - {len(self.descartes)} valor(es) descartados por não serem número")
        else:
            o.append("  - nenhum valor perdido na conversão")
        for p in self.provas:
            o.append(f"  - {p}")
        if not self.provas:
            o.append("  - SEM CONFERÊNCIA INDEPENDENTE: não achei total no arquivo pra bater contra. "
                     "Trate o número como estimativa até conferir na origem.")
        for a in self.avisos:
            o.append(f"  ! {a}")
        if self.pii_detectada:
            o.append(f"  ! dado pessoal detectado ({', '.join(sorted(self.pii_detectada))}). "
                     f"Mascare antes de mostrar em tela ou apresentação.")
        return "\n".join(o)


def _fmt(v):
    """Formato BR: 1.234.567,89"""
    try:
        return f"{v:,.2f}".replace(",", "~").replace(".", ",").replace("~", ".")
    except (TypeError, ValueError):
        return str(v)


# ------------------------------------------------------------------- ajuda

def marcadores_de_agregacao(linhas, coluna_texto=None):
    """
    Devolve (linhas_limpas, linhas_de_agregacao). A separação é a mesma que o
    profiler faz, repetida aqui pro script gerado não depender de importar o
    profiler inteiro.
    """
    rx = re.compile(r"\b(total|subtotal|sub-total|soma|somatorio|acumulado|geral|"
                    r"consolidado|resumo|saldo)\b", re.I)
    limpas, agregacao = [], []
    for linha in linhas:
        celulas = [linha[coluna_texto]] if coluna_texto is not None else list(linha)
        if any(isinstance(c, str) and rx.search(_norm(c)) for c in celulas):
            agregacao.append(linha)
        else:
            limpas.append(linha)
    return limpas, agregacao


if __name__ == "__main__":
    print(__doc__)
