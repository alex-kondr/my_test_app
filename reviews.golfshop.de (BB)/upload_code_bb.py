import subprocess
import sys
import os


current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)


from models import AgentModel, Status, AgentType, DBSession


AGENT_NAME = "reviews.golfshop.de"
RUN = True


REMOTE_HOST = "trknvsky@agentdev1.eu.testfreaks.com"
LOCAL_FILE = f"{AGENT_NAME} (BB)/new_{AGENT_NAME}.py"
REMOTE_FILE_PATH = f"test/{AGENT_NAME}.py"
REMOTE_OUTPUT_PATH = f"test/{AGENT_NAME}.txt"
LOCAL_OUTPUT_PATH = f"{AGENT_NAME} (BB)/{AGENT_NAME}.txt"


def main(run: bool = RUN):
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

    if run:
        with DBSession() as session:
            agent = session.query(AgentModel).filter(
                AgentModel.name == AGENT_NAME,
                AgentModel.status.in_([Status.in_progress, Status.qc, Status.running]),
            ).one_or_none()
            if agent:
                agent.status = Status.running
                agent.new_code = content
                agent.agent_type = AgentType.BIG
                agent.extra_time = True
                agent.paused = False
                session.commit()

    # Формуємо команду: записуємо файл, запускаємо mockrun у фоновому режимі через &,
    # щоб можна було перехопити його PID і коректно зупинити при обриві зв'язку (Ctrl+C)
    remote_command = f"cat > {REMOTE_FILE_PATH}"
    if run:
        remote_command += f" && mockrun.py {REMOTE_FILE_PATH} | tee {REMOTE_OUTPUT_PATH}"

    action_label = "та запуск" if run else "та збереження на сервері"
    print(f"2. Передача файлу на {REMOTE_HOST} {action_label} (для зупинки натисніть Ctrl+C)...")
    print("-" * 50)

    process = None
    try:
        # Запускаємо процес SSH
        process = subprocess.Popen(
            ["ssh", REMOTE_HOST, remote_command],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE if run else subprocess.DEVNULL,
            stderr=None,
            text=True,
            encoding="utf-8"
        )

        # Передаємо оброблений контент через stdin в ssh
        process.stdin.write(content)
        process.stdin.close()

        # Якщо RUN = True, читаємо потік виводу наживо та пишемо локально
        if run:
            with open(LOCAL_OUTPUT_PATH, "w", encoding="utf-8") as local_out:
                for line in iter(process.stdout.readline, ""):
                    # 1. Друкуємо в термінал наживо
                    # sys.stdout.write(line)
                    # sys.stdout.flush()

                    # 2. Записуємо у локальний файл логів
                    local_out.write(line)
                    local_out.flush()

        process.wait()

    except KeyboardInterrupt:
        print("\n" + "-" * 50)
        print("Виконання перервано користувачем (Ctrl+C). Зупиняємо процес на сервері...")
        if process:
            try:
                process.terminate()
                process.wait(timeout=2)
            except:
                try:
                    process.kill()
                except:
                    pass

        # Примусово завершуємо віддалені процеси, якщо вони запускалися
        if run:
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
        if run:
            print(f"Лог успішно збережено локально: '{LOCAL_OUTPUT_PATH}'.")
        else:
            print(f"Файл успішно передано та збережено на сервері у '{REMOTE_FILE_PATH}' (без запуску).")
        print("Роботу завершено.")

if __name__ == "__main__":
    main()