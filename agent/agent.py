import json
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from agent import datas, tools

MODELO = os.environ.get("JARVIS_MODEL", "llama3.2:3b")
TEMPERATURA = float(os.environ.get("JARVIS_TEMPERATURA", "0"))  # 0 = respostas reproduziveis
MAX_PASSOS = 5  # trava de seguranca: evita o agente ficar chamando ferramentas para sempre

DIAS = ["segunda-feira", "terca-feira", "quarta-feira", "quinta-feira",
        "sexta-feira", "sabado", "domingo"]

REGRAS_V1 = (
    "Responda em portugues do Brasil, de forma curta. "
    "Use as ferramentas para criar, listar, concluir e replanejar tarefas. "
    "Converta datas relativas (amanha, sexta) para o formato YYYY-MM-DD. "
    "Nunca invente tarefas ou ids: se precisar de um id, liste as tarefas antes. "
    "Se uma ferramenta devolver erro, corrija os argumentos e tente de novo."
)

# v2: acrescenta regras para os erros vistos no log (chamar ferramenta em "oi" e inventar tarefas)
REGRAS_V2 = REGRAS_V1 + (
    " Se o usuario apenas cumprimentar, agradecer ou conversar, ou perguntar algo que nao seja "
    "sobre tarefas, responda normalmente SEM usar ferramentas. "
    "Nao preencha due_date se o usuario nao citou um dia. "
    "Depois de usar uma ferramenta, responda usando somente o que ela devolveu: "
    "nunca invente nem liste tarefas que nao vieram do resultado."
)

# v3: o modelo nao calcula datas. O codigo extrai a data do pedido (agent/datas.py).
REGRAS_V3 = (
    "Responda em portugues do Brasil, de forma curta. "
    "Use as ferramentas para criar, listar, concluir e replanejar tarefas. "
    "Ao criar uma tarefa, informe so o titulo, curto e sem a data: o sistema extrai a data do pedido. "
    "Nunca invente tarefas ou ids: se precisar de um id, liste as tarefas antes. "
    "Se uma ferramenta devolver erro, corrija os argumentos e tente de novo. "
    "Se o usuario apenas cumprimentar, agradecer ou conversar, ou perguntar algo que nao seja "
    "sobre tarefas, responda normalmente SEM usar ferramentas. "
    "Depois de usar uma ferramenta, responda usando somente o que ela devolveu: "
    "nunca invente nem liste tarefas que nao vieram do resultado."
)

REGRAS = {"v1": REGRAS_V1, "v2": REGRAS_V2, "v3": REGRAS_V3}


def versao_prompt() -> str:
    versao = os.environ.get("JARVIS_PROMPT", "v2")
    if versao not in REGRAS:
        raise ValueError(f"JARVIS_PROMPT invalido: {versao}. Use v1, v2 ou v3.")
    return versao


def prompt_sistema() -> str:
    h = tools.hoje()
    return (
        f"Voce e um assistente de agenda e tarefas. Hoje e {DIAS[h.weekday()]}, {h.isoformat()}. "
        + REGRAS[versao_prompt()]
    )


def preparar_chamadas(chamadas: list[dict], texto_usuario: str) -> list[dict]:
    """v3: a data de uma tarefa nova vem do pedido do usuario (por codigo), nunca do modelo.
    v1 e v2 ficam exatamente como o modelo mandou."""
    if versao_prompt() != "v3":
        return chamadas
    preparadas = []
    for c in chamadas:
        args = dict(c["arguments"])
        if c["name"] == "add_task":
            args.pop("due_date", None)
            data = datas.extrair_data(texto_usuario, tools.hoje())
            if data is not None:
                args["due_date"] = data.isoformat()
        preparadas.append({"name": c["name"], "arguments": args})
    return preparadas


def chamar_llm(mensagens: list[dict]) -> dict:
    """Fala com o Ollama e devolve algo simples: {'content': str, 'tool_calls': [...]}."""
    import ollama  # importado aqui para os testes rodarem sem o Ollama instalado

    resp = ollama.chat(
        model=MODELO,
        messages=mensagens,
        tools=tools.schemas_para(versao_prompt()),
        options={"temperature": TEMPERATURA, "seed": 0},
    )
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
        registrar({"sessao": self.sessao, "evento": "pedido", "texto": texto,
                   "modelo": MODELO, "prompt": versao_prompt()})

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
                usada = preparar_chamadas([chamada], texto)[0]
                resultado = tools.run_tool(usada["name"], usada["arguments"])
                evento = {
                    "sessao": self.sessao, "evento": "chamada_ferramenta", "passo": passo,
                    "ferramenta": usada["name"], "argumentos": usada["arguments"],
                    "resultado": resultado, "latencia_llm_ms": latencia_ms,
                }
                if usada["arguments"] != chamada["arguments"]:
                    evento["argumentos_do_modelo"] = chamada["arguments"]  # o que o codigo corrigiu
                registrar(evento)
                self.mensagens.append({
                    "role": "tool",
                    "tool_name": usada["name"],
                    "content": json.dumps(resultado, ensure_ascii=False),
                })

        registrar({"sessao": self.sessao, "evento": "limite_de_passos", "max_passos": MAX_PASSOS})
        return "Nao consegui concluir o pedido dentro do limite de passos."
