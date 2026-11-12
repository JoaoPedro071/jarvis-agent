from datetime import date

import pytest

from agent import agent as modulo
from agent import tools
from avaliacao.casos import CASOS
from avaliacao.rodar import avaliar_caso


@pytest.fixture(autouse=True)
def ambiente(monkeypatch):
    monkeypatch.setattr(tools, "hoje", lambda: date(2026, 11, 11))
    monkeypatch.delenv("JARVIS_DATAS", raising=False)


def test_v2_com_datas_por_codigo_corrige_a_data(monkeypatch):
    monkeypatch.setenv("JARVIS_PROMPT", "v2")
    monkeypatch.setenv("JARVIS_DATAS", "codigo")
    mandou = [{"name": "add_task", "arguments": {"title": "Pagar a internet hoje", "due_date": "2026-11-12"}}]
    prep = modulo.preparar_chamadas(mandou, "preciso pagar a internet hoje")
    assert prep[0]["arguments"]["due_date"] == "2026-11-11"


def test_v2_padrao_nao_mexe(monkeypatch):
    monkeypatch.setenv("JARVIS_PROMPT", "v2")
    mandou = [{"name": "add_task", "arguments": {"title": "x", "due_date": "2026-11-12"}}]
    assert modulo.preparar_chamadas(mandou, "me lembra de x") == mandou


def test_datas_invalido(monkeypatch):
    monkeypatch.setenv("JARVIS_DATAS", "talvez")
    with pytest.raises(ValueError):
        modulo.datas_por_codigo()


# Saidas REAIS do llama3.2:3b (prompt v2, temperatura 0) na rodada de 12/11/2026.
SAIDAS_REAIS_V2_T0 = {
    "c06": {"title": "anotar o ME1", "due_date": "2026-11-12"},
    "c07": {"title": "Pagar a internet hoje", "due_date": "2026-11-12"},
    "c08": {"title": "estudar inglçãs na segunda", "due_date": "2026-11-12"},
    "c09": {"title": "Ligar para o dentista", "due_date": "2026-11-12"},
    "c11": {"title": "revisar o README", "due_date": "2026-11-12"},
    "c12": {"title": "Estudar", "due_date": "2026-11-12"},
}


def test_replay_v2_t0_com_datas_por_codigo(monkeypatch):
    monkeypatch.setenv("JARVIS_PROMPT", "v2")
    monkeypatch.setenv("JARVIS_DATAS", "codigo")
    casos = {c["id"]: c for c in CASOS}
    passou = {}
    for cid, args in SAIDAS_REAIS_V2_T0.items():
        chamadas = modulo.preparar_chamadas([{"name": "add_task", "arguments": args}], casos[cid]["frase"])
        passou[cid] = avaliar_caso(casos[cid]["esperado"], chamadas)["passou"]
    # so o c08 continua falhando: o modelo corrompeu o acento do titulo ("inglçãs")
    assert passou == {"c06": True, "c07": True, "c08": False, "c09": True, "c11": True, "c12": True}
