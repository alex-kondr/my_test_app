import subprocess
import sys
import os


current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)


from models import AgentModel, Status, AgentType, DBSession


REMOTE_HOST = "trknvsky@agentdev1.eu.testfreaks.com"
LOCAL_FILE = "reviews.highend-hifi-shop.de (BB)/new_reviews.highend-hifi-shop.de.py"
REMOTE_FILE_PATH = "test/reviews.highend-hifi-shop.de.py"
REMOTE_OUTPUT_PATH = "test/reviews.highend-hifi-shop.de.txt"
LOCAL_OUTPUT_PATH = "reviews.highend-hifi-shop.de (BB)/reviews.highend-hifi-shop.de.txt"


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
            AgentModel.name == "reviews.highend-hifi-shop.de",
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
        f"mockrun.py {REMOTE_FILE_PATH} | tee {REMOTE_OUTPUT_PATH} | awk '{{print \"\"; print NR \": \" $0; print \"\"; fflush()}}'"
    )

    print(f"2. Передача файлу на {REMOTE_HOST} та запуск (для зупинки натисніть Ctrl+C)...")
    print("-" * 50)

    process = None
    try:
        # Запускаємо процес SSH
        process = subprocess.Popen(
            ["ssh", REMOTE_HOST, remote_command],
            stdin=subprocess.PIPE,
            stdout=None,
            stderr=None,
            text=True,
            encoding="utf-8"
        )

        # Передаємо оброблений контент через stdin в ssh
        process.stdin.write(content)
        process.stdin.close()

        # Чекаємо завершення виконання процесу
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
        print("3. Копіювання віддаленого файлу локально...")
        try:
            subprocess.run(
                ["scp", f"{REMOTE_HOST}:{REMOTE_OUTPUT_PATH}", LOCAL_OUTPUT_PATH],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5
            )
            print(f"   - Файл успішно збережено: '{LOCAL_OUTPUT_PATH}'")
        except Exception as e:
            print(f"   - Помилка при копіюванні через scp: {e}")

        print("-" * 50)
        print("Роботу завершено.")

if __name__ == "__main__":
    main()