import subprocess
import sys
import os


current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)


from models import AgentModel, Status, AgentType, DBSession


AGENT_NAME = "reviews.undgretel.com"


REMOTE_HOST = "trknvsky@agentdev1.eu.testfreaks.com"
LOCAL_FILE = f"{AGENT_NAME} (BB)/new_{AGENT_NAME}.py"
REMOTE_FILE_PATH = f"test/{AGENT_NAME}.py"
REMOTE_OUTPUT_PATH = f"test/{AGENT_NAME}.txt"
LOCAL_OUTPUT_PATH = f"{AGENT_NAME} (BB)/{AGENT_NAME}.txt"


def main():
    print(f"1. Читання локального файлу '{LOCAL_FILE}' (без змін локально)...")
    try:
        with open(LOCAL_FILE, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        print(f"Помилка: Локальний файл '{LOCAL_FILE}' не знайдено.")
        return

    # Заміни "на льоту" у вмісті файлу перед відправкою
    content = content.replace(
        "(data: Response, context: dict[str, str], session: Session)",
        "(data, context, session)"
    ).replace(
        "(context: dict[str, str], session: Session)",
        "(context, session)"
    )

    with DBSession() as session:
        agent = session.query(AgentModel).filter(
            AgentModel.name == AGENT_NAME,
            AgentModel.status.in_([Status.in_progress, Status.qc, Status.running]),
        ).one_or_none()
        if agent:
            agent.status = Status.running
            agent.new_code = content
            agent.agent_type = AgentType.BIG
            agent.extra_time = False
            agent.paused = False
            session.commit()

    # Формуємо команду: записуємо файл, запускаємо mockrun у фоновому режимі через &,
    # щоб можна було перехопити його PID і коректно зупинити при обриві зв'язку (Ctrl+C)
    remote_command = (
        f"cat > {REMOTE_FILE_PATH} && "
        f"mockrun.py {REMOTE_FILE_PATH} | tee {REMOTE_OUTPUT_PATH}"
    )

    print(f"2. Передача файлу на {REMOTE_HOST} та запуск (для зупинки натисніть Ctrl+C)...")
    print("-" * 50)

    process = None
    try:
        # Запускаємо процес SSH
        process = subprocess.Popen(
            ["ssh", REMOTE_HOST, remote_command],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,  # Перехоплюємо stdout для локального запису
            stderr=subprocess.STDOUT, # Об'єднуємо помилки з виводом, щоб бачити все
            text=True,
            encoding="utf-8"
        )

        # Передаємо оброблений контент через stdin в ssh
        process.stdin.write(content)
        process.stdin.close()

        # Відкриваємо локальний файл для дозапису логів наживо
        with open(LOCAL_OUTPUT_PATH, "w", encoding="utf-8") as local_out:
            # Читаємо потік віддаленого виводу рядок за рядком у реальному часі
            for line in iter(process.stdout.readline, ""):
                # 1. Друкуємо в локальний термінал (можна додати нумерацію чи залишити як є)
                sys.stdout.write(line)
                sys.stdout.flush()

                # 2. Одразу записуємо цей же рядок у локальний файл
                local_out.write(line)
                local_out.flush()

        process.wait()

    except KeyboardInterrupt:
        print("\n" + "-" * 50)
        print("Виконання перервано користувачем (Ctrl+C). Зупиняємо процес на сервере...")
        if process:
            try:
                process.terminate()
                process.wait(timeout=2)
            except:
                try:
                    process.kill()
                except:
                    pass

        # Примусово завершуємо віддалені процеси mockrun/agent для цього користувача, щоб вони не висіли
        try:
            subprocess.run(
                ["ssh", REMOTE_HOST, "pkill -9 -f 'agent test/' || true"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=3
            )
        except:
            pass

    finally:
        print("-" * 50)
        print(f"Лог успішно збережено локально: '{LOCAL_OUTPUT_PATH}'.")
        print("Роботу завершено.")

if __name__ == "__main__":
    main()