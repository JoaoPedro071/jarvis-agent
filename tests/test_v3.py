import json
from datetime import date

import pytest

from agent import agent as modulo
from agent import tools
from avaliacao.casos import CASOS
from avaliacao.rodar import avaliar_caso


@pytest.fixture(autouse=True)
def ambiente(tmp_path, monkeypatch):
    monkeypatch.setenv("JARVIS_DB", str(tmp_path / "t.db"))
    monkeypatch.setenv("JARVIS_LOG", str(tmp_path / "log.jsonl"))
    monkeypatch.setattr(tools, "hoje", lambda: date(2026, 11, 11))


def test_v3_data_vem_do_pedido_e_nao_do_modelo(monkeypatch):
    monkeypatch.setenv("JARVIS_PROMPT", "v3")
    do_modelo = [{"name": "add_task", "arguments": {"title": "Pagar a internet", "due_date": "2026-11-12"}}]
    prep = modulo.preparar_chamadas(do_modelo, "preciso pagar a internet hoje")
    assert prep[0]["arguments"]["due_date"] == "2026-11-11"


def test_v3_remove_data_inventada(monkeypatch):
    monkeypatch.setenv("JARVIS_PROMPT", "v3")
    do_modelo = [{"name": "add_task", "arguments": {"title": "estudar", "due_date": "2026-11-12"}}]
    prep = modulo.preparar_chamadas(do_modelo, "me lembra de estudar")
    assert "due_date" not in prep[0]["arguments"]
    do_modelo = [{"name": "add_task", "arguments": {"title": "revisar README", "due_date": "null"}}]
    assert "due_date" not in modulo.preparar_chamadas(do_modelo, "criar tarefa revisar o README")[0]["arguments"]


def test_v3_nao_mexe_em_outras_ferramentas(monkeypatch):
    monkeypatch.setenv("JARVIS_PROMPT", "v3")
    c = [{"name": "list_tasks", "arguments": {"scope": "today"}}]
    assert modulo.preparar_chamadas(c, "o que tenho para hoje?") == c


@pytest.mark.parametrize("versao", ["v1", "v2"])
def test_v1_e_v2_ficam_como_o_modelo_mandou(monkeypatch, versao):
    monkeypatch.setenv("JARVIS_PROMPT", versao)
    c = [{"name": "add_task", "arguments": {"title": "x", "due_date": "2026-11-12"}}]
    assert modulo.preparar_chamadas(c, "me lembra de x") == c


def test_prompt_invalido(monkeypatch):
    monkeypatch.setenv("JARVIS_PROMPT", "v9")
    with pytest.raises(ValueError):
        modulo.versao_prompt()


def test_schema_v3_sem_due_date_e_legado_intacto():
    v3 = {s["function"]["name"]: s for s in tools.schemas_para("v3")}
    assert "due_date" not in v3["add_task"]["function"]["parameters"]["properties"]
    v2 = {s["function"]["name"]: s for s in tools.schemas_para("v2")}
    assert "due_date" in v2["add_task"]["function"]["parameters"]["properties"]
    assert "due_date" in tools.TOOL_SCHEMAS[0]["function"]["parameters"]["properties"]  # original nao foi alterado


def test_agente_v3_grava_data_correta_e_loga_a_correcao(tmp_path, monkeypatch):
    monkeypatch.setenv("JARVIS_PROMPT", "v3")
    fila = [
        {"content": "", "tool_calls": [
            {"name": "add_task", "arguments": {"title": "Estudar BD", "due_date": "2026-11-20"}}]},
        {"content": "Pronto.", "tool_calls": []},
    ]
    agente = modulo.Agente(llm=lambda m: fila.pop(0))
    agente.pedir("me lembra de estudar BD amanhã")
    assert tools.list_tasks("open")["tasks"][0]["due_date"] == "2026-11-12"
    linhas = [json.loads(l) for l in (tmp_path / "log.jsonl").read_text(encoding="utf-8").splitlines()]
    chamada = next(l for l in linhas if l["evento"] == "chamada_ferramenta")
    assert chamada["argumentos"]["due_date"] == "2026-11-12"
    assert chamada["argumentos_do_modelo"]["due_date"] == "2026-11-20"


# Saidas REAIS do llama3.2:3b (prompt v2) na rodada de avaliacao de 12/11/2026, reaproveitadas
# para checar o que o v3 corrigiria. Nao e uma nova rodada: o modelo pode se comportar diferente.
SAIDAS_REAIS_V2 = {
    "c05": {"title": "", "due_date": "2026-11-12"},
    "c06": {"title": "anotar tarefa", "due_date": "2026-11-12"},
    "c07": {"title": "Pagar a internet hoje", "due_date": "2026-11-12"},
    "c08": {"title": "Estudar inglçâs", "due_date": "2026-11-12"},
    "c09": {"title": "Ligaria para o dentista", "due_date": "2026-11-12"},
    "c11": {"title": "revisar o README", "due_date": "null"},
    "c12": {"title": "estudar", "due_date": "2026-11-12"},
}


def test_replay_das_saidas_reais_do_v2(monkeypatch):
    monkeypatch.setenv("JARVIS_PROMPT", "v3")
    casos = {c["id"]: c for c in CASOS}
    passou = {}
    for cid, args in SAIDAS_REAIS_V2.items():
        chamadas = modulo.preparar_chamadas([{"name": "add_task", "arguments": args}], casos[cid]["frase"])
        passou[cid] = avaliar_caso(casos[cid]["esperado"], chamadas)["passou"]
    # datas deixam de ser o problema; sobram os titulos ruins (c05, c06, c08)
    assert passou == {"c05": False, "c06": False, "c07": True, "c08": False,
                      "c09": True, "c11": True, "c12": True}
