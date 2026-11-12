"""Avalia a DECISAO do modelo: dada uma frase, ele escolheu a ferramenta e os argumentos certos?

Roda so a primeira chamada ao modelo (sem executar ferramentas), entao e mais rapido e deterministico.
Uso (da raiz do projeto):
    python -m avaliacao.rodar --limite 3     # teste rapido
    python -m avaliacao.rodar                # todos os casos
    JARVIS_PROMPT=v1 python -m avaliacao.rodar   # v1, v2 ou v3 (v3: datas extraidas por codigo)
    JARVIS_MODEL=outro-modelo python -m avaliacao.rodar
"""
import argparse
import json
import sys
import time
import unicodedata
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

from agent import agent as ag
from agent import tools
from avaliacao.casos import CASOS

HOJE_FIXO = date(2026, 11, 11)  # quarta-feira; as datas esperadas nos casos partem daqui
PADROES = {"list_tasks": {"scope": "open"}}  # valores que a propria ferramenta assume se omitidos


def normalizar(texto) -> str:
    texto = unicodedata.normalize("NFD", str(texto).lower())
    return "".join(c for c in texto if unicodedata.category(c) != "Mn")


def arg_confere(esperado, real) -> bool:
    if esperado is None:
        return real in (None, "")
    if isinstance(esperado, dict):
        return normalizar(esperado["contem"]) in normalizar(real if real is not None else "")
    return str(real).strip() == str(esperado)


def avaliar_caso(esperado: dict, chamadas: list[dict]) -> dict:
    """Compara a decisao do modelo com o esperado."""
    tool = esperado["tool"]
    if tool is None:
        ok = len(chamadas) == 0
        return {"tool_ok": ok, "args_ok": ok, "passou": ok}
    tool_ok = len(chamadas) == 1 and chamadas[0]["name"] == tool
    if not tool_ok:
        return {"tool_ok": False, "args_ok": False, "passou": False}
    reais = {**PADROES.get(tool, {}), **chamadas[0]["arguments"]}
    args_ok = all(arg_confere(v, reais.get(k)) for k, v in esperado["args"].items())
    return {"tool_ok": True, "args_ok": args_ok, "passou": args_ok}


def resumir(resultados: list[dict]) -> dict:
    total = len(resultados)
    com_args = [r for r in resultados if r["esperado"]["tool"] and r["tool_ok"] and r["esperado"]["args"]]
    por_cat = defaultdict(lambda: [0, 0])
    for r in resultados:
        por_cat[r["categoria"]][1] += 1
        por_cat[r["categoria"]][0] += r["passou"]
    return {
        "total": total,
        "acertos": sum(r["passou"] for r in resultados),
        "escolha_de_ferramenta": sum(r["tool_ok"] for r in resultados),
        "argumentos_certos": f'{sum(r["args_ok"] for r in com_args)}/{len(com_args)}',
        "latencia_media_s": round(sum(r["latencia_ms"] for r in resultados) / max(total, 1) / 1000, 1),
        "por_categoria": {c: f"{a}/{n}" for c, (a, n) in por_cat.items()},
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limite", type=int, default=None, help="roda so os N primeiros casos")
    args = parser.parse_args()

    tools.hoje = lambda: HOJE_FIXO  # data fixa para o resultado ser reproduzivel
    casos = CASOS[: args.limite] if args.limite else CASOS
    prompt = ag.versao_prompt()
    print(f"Modelo: {ag.MODELO} | prompt: {prompt} | temperatura: {ag.TEMPERATURA:g} | casos: {len(casos)}\n", flush=True)

    resultados, erros_seguidos = [], 0
    for caso in casos:
        mensagens = [
            {"role": "system", "content": ag.prompt_sistema()},
            {"role": "user", "content": caso["frase"]},
        ]
        inicio = time.perf_counter()
        try:
            resposta = ag.chamar_llm(mensagens)
            do_modelo = resposta["tool_calls"]
            chamadas = ag.preparar_chamadas(do_modelo, caso["frase"])  # igual ao que o agente executaria
            texto, erro = resposta["content"], None
            erros_seguidos = 0
        except Exception as e:
            do_modelo, chamadas, texto, erro = [], [], "", str(e)
            erros_seguidos += 1
        ms = round((time.perf_counter() - inicio) * 1000)

        if erro:
            veredito = {"tool_ok": False, "args_ok": False, "passou": False}
        else:
            veredito = avaliar_caso(caso["esperado"], chamadas)
        resultados.append({
            "id": caso["id"], "categoria": caso["categoria"], "frase": caso["frase"],
            "esperado": caso["esperado"], "chamadas_do_modelo": do_modelo, "chamadas": chamadas, "texto": texto,
            "erro": erro, "latencia_ms": ms, **veredito,
        })
        marca = "OK  " if veredito["passou"] else "ERRO"
        print(f"{marca} {caso['id']} ({ms / 1000:.0f}s) {caso['frase']}", flush=True)
        if erro:
            print(f"     [erro do modelo] {erro}", flush=True)
        if erros_seguidos >= 2:
            sys.exit("Dois erros seguidos ao chamar o modelo. O Ollama esta rodando? (systemctl status ollama)")

    resumo = resumir(resultados)
    print("\n=== Resumo ===")
    print(f"Acertos: {resumo['acertos']}/{resumo['total']}")
    print(f"Ferramenta certa: {resumo['escolha_de_ferramenta']}/{resumo['total']}")
    print(f"Argumentos certos (quando a ferramenta estava certa): {resumo['argumentos_certos']}")
    print(f"Latencia media por decisao: {resumo['latencia_media_s']}s")
    for cat, valor in resumo["por_categoria"].items():
        print(f"  {cat}: {valor}")

    falhas = [r for r in resultados if not r["passou"]]
    if falhas:
        print("\n=== Falhas ===")
        for r in falhas:
            fez = [f'{c["name"]}({c["arguments"]})' for c in r["chamadas"]] or ["nenhuma ferramenta"]
            print(f'{r["id"]} "{r["frase"]}"\n   esperado: {r["esperado"]}\n   modelo:   {fez}')

    pasta = Path("avaliacao/resultados")
    pasta.mkdir(parents=True, exist_ok=True)
    sufixo = "_parcial" if args.limite else ""
    nome = f'{ag.MODELO.replace(":", "-")}_{prompt}_t{ag.TEMPERATURA:g}{sufixo}.json'
    saida = {"modelo": ag.MODELO, "prompt": prompt, "temperatura": ag.TEMPERATURA, "data": datetime.now(timezone.utc).isoformat(),
             "resumo": resumo, "casos": resultados}
    (pasta / nome).write_text(json.dumps(saida, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nResultado salvo em avaliacao/resultados/{nome}")


if __name__ == "__main__":
    main()
