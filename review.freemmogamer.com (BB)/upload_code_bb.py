import subprocess
import threading
import re
import sys
import os


current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)


from models import AgentModel, Status, AgentType, DBSession


AGENT_NAME = "review.freemmogamer.com"
RUN = True
MAX_PAGES = 4   # Автостоп пагінації process_revlist після N сторінок (0 або None — вимкнути)
MAX_EMITS = 50  # Автостоп виконання після N емітів (0 або None — вимкнути)


REMOTE_HOST = "trknvsky@agentdev1.eu.testfreaks.com"
LOCAL_FILE = f"{AGENT_NAME} (BB)/new_{AGENT_NAME}.py"
REMOTE_FILE_PATH = f"test/{AGENT_NAME}.py"
REMOTE_OUTPUT_PATH = f"test/{AGENT_NAME}.txt"
LOCAL_OUTPUT_PATH = f"{AGENT_NAME} (BB)/{AGENT_NAME}.txt"


def disable_pagination(code: str) -> str:
    return re.sub(r'^(\s*)next_url\s*=\s*', r'\1next_url = None  # ', code, flags=re.MULTILINE)


def upload_code_only(code: str, msg: str = None):
    try:
        subprocess.run(
            ["ssh", REMOTE_HOST, f"cat > {REMOTE_FILE_PATH}"],
            input=code,
            text=True,
            encoding="utf-8",
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10
        )
        if msg:
            sys.stderr.write(f"\n[AUTO] {msg}\n")
            sys.stderr.flush()
    except Exception as e:
        sys.stderr.write(f"\n[AUTO] Помилка при оновленні файлу на сервері: {e}\n")
        sys.stderr.flush()


def stop_remote_process(process):
    if process:
        try:
            process.terminate()
            process.wait(timeout=2)
        except:
            try:
                process.kill()
            except:
                pass
    try:
        subprocess.run(
            ["ssh", REMOTE_HOST, "pkill -9 -f 'agent test/' || true"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=3
        )
    except:
        pass


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
                agent.extra_time = False
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
    pagination_stopped = [False]
    is_pro = "review.type = 'pro'" in content or 'review.type = "pro"' in content
    try:
        # Запускаємо процес SSH (автостоп пагінації тільки для PRO агентів)
        use_auto_stop = run and bool(MAX_PAGES) and is_pro
        process = subprocess.Popen(
            ["ssh", REMOTE_HOST, remote_command],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE if run else subprocess.DEVNULL,
            stderr=subprocess.PIPE if use_auto_stop else None,
            text=True,
            encoding="utf-8"
        )

        # Передаємо оброблений контент через stdin в ssh
        process.stdin.write(content)
        process.stdin.close()

        # Якщо увімкнено автостоп пагінації, читаємо stderr у фоновому потоці
        stderr_thread = None
        if use_auto_stop:
            def watch_stderr():
                revlist_pages = 0
                for err_line in iter(process.stderr.readline, ""):
                    sys.stderr.write(err_line)
                    sys.stderr.flush()
                    if not pagination_stopped[0] and "Run process_revlist " in err_line:
                        revlist_pages += 1
                        if revlist_pages >= MAX_PAGES:
                            pagination_stopped[0] = True
                            threading.Thread(
                                target=upload_code_only,
                                args=(
                                    disable_pagination(content),
                                    f"Пагінацію вимкнено на сервері ({REMOTE_FILE_PATH}) — переходимо до process_review."
                                ),
                                daemon=True
                            ).start()

            stderr_thread = threading.Thread(target=watch_stderr, daemon=True)
            stderr_thread.start()

        # Якщо RUN = True, читаємо потік виводу наживо та пишемо локально
        if run:
            emits_count = 0
            with open(LOCAL_OUTPUT_PATH, "w", encoding="utf-8") as local_out:
                for line in iter(process.stdout.readline, ""):
                    # 1. Друкуємо в термінал наживо
                    # sys.stdout.write(line)
                    # sys.stdout.flush()

                    # 2. Записуємо у локальний файл логів
                    local_out.write(line)
                    local_out.flush()

                    # 3. Перевіряємо ліміт емітів
                    if line.startswith("EMIT:"):
                        emits_count += 1
                        if MAX_EMITS and emits_count >= MAX_EMITS:
                            print(f"\n[AUTO] Досягнуто ліміту емітів ({emits_count}) — зупиняємо виконання...")
                            stop_remote_process(process)
                            break

        process.wait()
        if stderr_thread:
            stderr_thread.join(timeout=2)

    except KeyboardInterrupt:
        print("\n" + "-" * 50)
        print("Виконання перервано користувачем (Ctrl+C). Зупиняємо процес на сервері...")
        if run:
            stop_remote_process(process)
        elif process:
            try:
                process.terminate()
                process.wait(timeout=2)
            except:
                pass

    finally:
        if pagination_stopped[0]:
            upload_code_only(content, f"Оригінальний файл (з пагінацією) відновлено на сервері ({REMOTE_FILE_PATH}).")

        print("-" * 50)
        if run:
            print(f"Лог успішно збережено локально: '{LOCAL_OUTPUT_PATH}'.")
        else:
            print(f"Файл успішно передано та збережено на сервері у '{REMOTE_FILE_PATH}' (без запуску).")
        print("Роботу завершено.")

if __name__ == "__main__":
    main()