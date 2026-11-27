import subprocess


REMOTE_HOST = "trknvsky@agentdev1.eu.testfreaks.com"


def main():
    try:
        result = subprocess.run(
            ["ssh", REMOTE_HOST, "pkill -9 -f '[a]gent test/' || true"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            timeout=10,
        )
        if result.returncode == 0:
            print("Усі запущені процеси 'agent test/' на сервері зупинено.")
        else:
            print(f"Помилка при зупинці процесів: {result.stderr}")
    except Exception as e:
        print(f"Виникла помилка під час підключення: {e}")


if __name__ == "__main__":
    main()
