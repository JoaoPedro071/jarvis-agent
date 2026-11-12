from datetime import date

from avaliacao.casos import CASOS
from avaliacao.rodar import avaliar_caso, resumir

TOOLS_VALIDAS = {"add_task", "list_tasks", "complete_task", "rollover_overdue"}


def chamada_perfeita(esperado):
    """Monta a chamada que um modelo perfeito faria para este caso."""
    if esperado["tool"] is None:
        return []
    args = {}
    for chave, valor in esperado["args"].items():
        if valor is None:
            continue
        args[chave] = valor["contem"] if isinstance(valor, dict) else valor
    return [{"name": esperado["tool"], "arguments": args}]


def test_casos_sao_consistentes():
    ids = [c["id"] for c in CASOS]
    assert len(ids) == len(set(ids))
    for c in CASOS:
        tool = c["esperado"]["tool"]
        assert tool is None or tool in TOOLS_VALIDAS
        data = c["esperado"]["args"].get("due_date")
        if isinstance(data, str):
            assert date.fromisoformat(data) >= date(2026, 11, 11)


def test_datas_relativas_dos_casos():
    # hoje = quarta-feira 2026-11-11
    esperado = {"c05": "2026-11-12", "c06": "2026-11-13", "c07": "2026-11-11",
                "c08": "2026-11-16", "c09": "2026-11-13", "c10": "2026-11-20"}
    for c in CASOS:
        if c["id"] in esperado:
            assert c["esperado"]["args"]["due_date"] == esperado[c["id"]]
    assert date(2026, 11, 13).strftime("%A") == "Friday"
    assert date(2026, 11, 16).strftime("%A") == "Monday"


def test_modelo_perfeito_acerta_tudo():
    for c in CASOS:
        v = avaliar_caso(c["esperado"], chamada_perfeita(c["esperado"]))
        assert v["passou"], c["id"]


def test_erros_sao_detectados():
    conversa = CASOS[0]["esperado"]  # "oi": nao pode chamar ferramenta
    assert not avaliar_caso(conversa, [{"name": "add_task", "arguments": {"title": ""}}])["passou"]

    criar = next(c for c in CASOS if c["id"] == "c05")["esperado"]
    errada = [{"name": "add_task", "arguments": {"title": "estudar banco de dados", "due_date": "2026-11-13"}}]
    v = avaliar_caso(criar, errada)
    assert v["tool_ok"] and not v["args_ok"]

    sem_data = next(c for c in CASOS if c["id"] == "c11")["esperado"]
    inventou = [{"name": "add_task", "arguments": {"title": "revisar README", "due_date": "2026-11-12"}}]
    assert not avaliar_caso(sem_data, inventou)["passou"]


def test_scope_omitido_vale_open_e_acento_nao_importa():
    listar = next(c for c in CASOS if c["id"] == "c16")["esperado"]
    assert avaliar_caso(listar, [{"name": "list_tasks", "arguments": {}}])["passou"]
    ingles = next(c for c in CASOS if c["id"] == "c08")["esperado"]
    ok = [{"name": "add_task", "arguments": {"title": "Estudar Inglês", "due_date": "2026-11-16"}}]
    assert avaliar_caso(ingles, ok)["passou"]


def test_resumo():
    rs = []
    for c in CASOS[:4]:
        v = avaliar_caso(c["esperado"], chamada_perfeita(c["esperado"]))
        rs.append({"id": c["id"], "categoria": c["categoria"], "esperado": c["esperado"],
                   "latencia_ms": 1000, **v})
    r = resumir(rs)
    assert r["acertos"] == 4 and r["por_categoria"]["conversa"] == "4/4"
