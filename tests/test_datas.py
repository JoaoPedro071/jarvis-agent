from datetime import date

import pytest

from agent.datas import extrair_data

HOJE = date(2026, 11, 11)  # quarta-feira


@pytest.mark.parametrize("frase,esperado", [
    ("me lembra de estudar banco de dados amanhã", date(2026, 11, 12)),
    ("anota: entregar o ME1 sexta-feira", date(2026, 11, 13)),
    ("preciso pagar a internet hoje", date(2026, 11, 11)),
    ("adiciona estudar inglês na segunda", date(2026, 11, 16)),
    ("me lembra de ligar para o dentista depois de amanhã", date(2026, 11, 13)),
    ("anota comprar café dia 20", date(2026, 11, 20)),
    ("reunião na terça-feira", date(2026, 11, 17)),
    ("churrasco no sábado", date(2026, 11, 14)),
    ("revisar na quarta", date(2026, 11, 18)),          # mesmo dia da semana: semana que vem
    ("pagar boleto dia 5", date(2026, 12, 5)),           # dia 5 ja passou: mes que vem
    ("entregar dia 11", date(2026, 11, 11)),             # hoje
    ("viagem dia 25/12", date(2026, 12, 25)),
    ("prova em 02/03", date(2027, 3, 2)),                # sem ano e ja passou: ano que vem
    ("consulta 15/12/2026", date(2026, 12, 15)),
    ("consulta 15/12/26", date(2026, 12, 15)),
    ("entrega em 2026-11-30", date(2026, 11, 30)),
    ("estudar daqui a 3 dias", date(2026, 11, 14)),
    ("me lembra amanhã às 19h", date(2026, 11, 12)),
    ("criar tarefa revisar o README", None),
    ("me lembra de estudar", None),
    ("obrigado!", None),
    ("bom dia, tudo bem?", None),
    ("conclui a tarefa 3", None),                        # numero solto nao e data
    ("anota dia 31", None),                              # novembro nao tem dia 31
    ("entrega 2026-02-30", None),
])
def test_extrair_data(frase, esperado):
    assert extrair_data(frase, HOJE) == esperado


def test_virada_de_ano():
    assert extrair_data("dia 5", date(2026, 12, 20)) == date(2027, 1, 5)
    assert extrair_data("25/12", date(2026, 12, 26)) == date(2027, 12, 25)
