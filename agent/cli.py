from agent.agent import MODELO, Agente


def main() -> None:
    agente = Agente()
    print(f"Agente de agenda (modelo: {MODELO}). Digite 'sair' para encerrar.")
    while True:
        try:
            texto = input("voce> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if texto.lower() in {"sair", "exit", "quit"}:
            break
        if not texto:
            continue
        try:
            print("agente>", agente.pedir(texto))
        except Exception as e:
            print(f"[erro] {e}")
            print("Dica: o Ollama esta rodando? (systemctl status ollama) O modelo foi baixado? (ollama list)")


if __name__ == "__main__":
    main()
