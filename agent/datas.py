"""Extrai datas de frases em portugues, por regras. Aritmetica de calendario nao e tarefa para LLM pequeno."""
import re
import unicodedata
from calendar import monthrange
from datetime import date, timedelta

DIAS_SEMANA = {"segunda": 0, "terca": 1, "quarta": 2, "quinta": 3, "sexta": 4, "sabado": 5, "domingo": 6}


def _normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in texto if unicodedata.category(c) != "Mn")


def _montar(ano: int, mes: int, dia: int) -> date | None:
    try:
        return date(ano, mes, dia)
    except ValueError:
        return None


def extrair_data(texto: str, hoje: date) -> date | None:
    """Devolve a data citada na frase, ou None se nao houver (ou se for invalida)."""
    t = _normalizar(texto)

    m = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", t)
    if m:
        return _montar(int(m[1]), int(m[2]), int(m[3]))

    m = re.search(r"\b(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?\b", t)
    if m:
        dia, mes = int(m[1]), int(m[2])
        if m[3]:
            ano = int(m[3]) + (2000 if len(m[3]) == 2 else 0)
            return _montar(ano, mes, dia)
        data = _montar(hoje.year, mes, dia)
        if data and data < hoje:  # sem ano e ja passou: vale o ano que vem
            data = _montar(hoje.year + 1, mes, dia)
        return data

    if re.search(r"\bdepois de amanha\b", t):
        return hoje + timedelta(days=2)
    if re.search(r"\bamanha\b", t):
        return hoje + timedelta(days=1)
    if re.search(r"\bhoje\b", t):
        return hoje

    m = re.search(r"\bdaqui a (\d{1,3}) dias?\b", t)
    if m:
        return hoje + timedelta(days=int(m[1]))

    m = re.search(r"\bdia (\d{1,2})\b", t)
    if m:
        dia = int(m[1])
        ano, mes = hoje.year, hoje.month
        if dia < hoje.day:  # o dia ja passou neste mes: vale o proximo mes
            mes += 1
            if mes == 13:
                ano, mes = ano + 1, 1
        if not 1 <= dia <= monthrange(ano, mes)[1]:
            return None
        return date(ano, mes, dia)

    m = re.search(r"\b(segunda|terca|quarta|quinta|sexta|sabado|domingo)\b", t)
    if m:
        faltam = (DIAS_SEMANA[m[1]] - hoje.weekday()) % 7
        return hoje + timedelta(days=faltam or 7)  # mesmo dia da semana: vale a proxima semana

    return None
