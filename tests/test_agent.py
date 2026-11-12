import json
from datetime import date

import pytest

from agent import agent as modulo_agente
from agent import tools


@pytest.fixture(autouse=True)
def ambiente(tmp_path, monkeypatch):
    monkeypatch.setenv("JARVIS_DB", str(tmp_path / "teste.db"))
    monkeypatch.setenv("JARVIS_LOG", str(tmp_path / "decisoes.jsonl"))
    monkeypatch.setattr(tools, "hoje", lambda: date(2026, 11, 10))


def llm_roteirizado(respostas):
    """LLM de mentira: devolve as respostas combinadas, uma por chamada."""
    fila = list(respostas)
    return lambda mensagens: fila.pop(0)


def ler_log(tmp_path):
    linhas = (tmp_path / "decisoes.jsonl").read_text(encoding="utf-8").splitlines()
    return [json.loads(l) for l in linhas]


def test_pedido_vira_tarefa_e_gera_log(tmp_path):
    llm = llm_roteirizado([
        {"content": "", "tool_calls": [
            {"name": "add_task", "arguments": {"title": "Estudar BD", "due_date": "2026-11-11"}}]},
        {"content": "Tarefa criada para amanha.", "tool_calls": []},
    ])
    agente = modulo_agente.Agente(llm=llm)
    resposta = agente.pedir("me lembra de estudar BD amanha")

    assert resposta == "Tarefa criada para amanha."
    assert tools.list_tasks("open")["tasks"][0]["title"] == "Estudar BD"
    eventos = [e["evento"] for e in ler_log(tmp_path)]
    assert eventos == ["pedido", "chamada_ferramenta", "resposta_final"]


def test_erro_de_ferramenta_volta_para_o_modelo(tmp_path):
    llm = llm_roteirizado([
        {"content": "", "tool_calls": [
            {"name": "add_task", "arguments": {"title": "X", "due_date": "algum dia"}}]},
        {"content": "", "tool_calls": [
            {"name": "add_task", "arguments": {"title": "X", "due_date": "2026-11-11"}}]},
        {"content": "Pronto.", "tool_calls": []},
    ])
    agente = modulo_agente.Agente(llm=llm)
    assert agente.pedir("anota X amanha") == "Pronto."
    chamadas = [e for e in ler_log(tmp_path) if e["evento"] == "chamada_ferramenta"]
    assert "error" in chamadas[0]["resultado"]
    assert "error" not in chamadas[1]["resultado"]


def test_limite_de_passos(tmp_path):
    loop = {"content": "", "tool_calls": [{"name": "list_tasks", "arguments": {}}]}
    llm = llm_roteirizado([loop] * (modulo_agente.MAX_PASSOS + 1))
    agente = modulo_agente.Agente(llm=llm)
    assert "limite" in agente.pedir("qualquer coisa")
    assert ler_log(tmp_path)[-1]["evento"] == "limite_de_passos"
