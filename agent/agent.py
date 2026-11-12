import json
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from agent import tools

MODELO = os.environ.get("JARVIS_MODEL", "llama3.2:3b")
MAX_PASSOS = 5  # trava de seguranca: evita o agente ficar chamando ferramentas para sempre

DIAS = ["segunda-feira", "terca-feira", "quarta-feira", "quinta-feira",
        "sexta-feira", "sabado", "domingo"]


def prompt_sistema() -> str:
    h = tools.hoje()
    return (
        f"Voce e um assistente de agenda e tarefas. Hoje e {DIAS[h.weekday()]}, {h.isoformat()}. "
        "Responda em portugues do Brasil, de forma curta. "
        "Use as ferramentas para criar, listar, concluir e replanejar tarefas. "
        "Converta datas relativas (amanha, sexta) para o formato YYYY-MM-DD. "
        "Nunca invente tarefas ou ids: se precisar de um id, liste as tarefas antes. "
        "Se uma ferramenta devolver erro, corrija os argumentos e tente de novo."
    )


def chamar_llm(mensagens: list[dict]) -> dict:
    """Fala com o Ollama e devolve algo simples: {'content': str, 'tool_calls': [...]}."""
    import ollama  # importado aqui para os testes rodarem sem o Ollama instalado

    resp = ollama.chat(model=MODELO, messages=mensagens, tools=tools.TOOL_SCHEMAS)
    msg = resp.message
    chamadas = [
        {"name": c.function.name, "arguments": dict(c.function.arguments)}
        for c in (msg.tool_calls or [])
    ]
    return {"content": msg.content or "", "tool_calls": chamadas}


def registrar(evento: dict) -> None:
    """Escreve uma linha JSON por decisao em logs/decisoes.jsonl."""
    caminho = Path(os.environ.get("JARVIS_LOG", "logs/decisoes.jsonl"))
    caminho.parent.mkdir(parents=True, exist_ok=True)
    evento = {"ts": datetime.now(timezone.utc).isoformat(), **evento}
    with caminho.open("a", encoding="utf-8") as f:
        f.write(json.dumps(evento, ensure_ascii=False) + "\n")


class Agente:
    def __init__(self, llm=chamar_llm):
        self.llm = llm  # trocavel: nos testes entra um LLM "de mentira"
        self.sessao = uuid.uuid4().hex[:8]
        self.mensagens = [{"role": "system", "content": prompt_sistema()}]

    def pedir(self, texto: str) -> str:
        self.mensagens.append({"role": "user", "content": texto})
        registrar({"sessao": self.sessao, "evento": "pedido", "texto": texto, "modelo": MODELO})

        for passo in range(1, MAX_PASSOS + 1):
            inicio = time.perf_counter()
            resposta = self.llm(self.mensagens)
            latencia_ms = round((time.perf_counter() - inicio) * 1000)

            if not resposta["tool_calls"]:
                registrar({
                    "sessao": self.sessao, "evento": "resposta_final", "passo": passo,
                    "texto": resposta["content"], "latencia_ms": latencia_ms,
                })
                self.mensagens.append({"role": "assistant", "content": resposta["content"]})
                return resposta["content"]

            # guarda no historico que o assistente pediu ferramentas
            self.mensagens.append({
                "role": "assistant",
                "content": resposta["content"],
                "tool_calls": [{"function": c} for c in resposta["tool_calls"]],
            })

            for chamada in resposta["tool_calls"]:
                resultado = tools.run_tool(chamada["name"], chamada["arguments"])
                registrar({
                    "sessao": self.sessao, "evento": "chamada_ferramenta", "passo": passo,
                    "ferramenta": chamada["name"], "argumentos": chamada["arguments"],
                    "resultado": resultado, "latencia_llm_ms": latencia_ms,
                })
                self.mensagens.append({
                    "role": "tool",
                    "tool_name": chamada["name"],
                    "content": json.dumps(resultado, ensure_ascii=False),
                })

        registrar({"sessao": self.sessao, "evento": "limite_de_passos", "max_passos": MAX_PASSOS})
        return "Nao consegui concluir o pedido dentro do limite de passos."
