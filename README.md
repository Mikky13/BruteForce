# BruteForce — учебный брутфорс форм авторизации

Небольшой инструмент для проверки устойчивости форм логина к перебору паролей.
Писался для лабораторий [PortSwigger Web Security Academy](https://portswigger.net/web-security)
и собственных тестовых стендов.

> ⚠️ **Только для систем, которые принадлежат вам или на тестирование которых есть письменное разрешение.**
> Перебор паролей на чужих ресурсах — это противоправное действие, а не «пентест».

## Возможности

- **Автопоиск формы** — сам находит `action`, метод и имена полей (`--auto-form`).
- **Формат тела запроса** — обычный `form-urlencoded` или JSON (`--json`).
- **Многопоточность** — пул потоков, отправка пачками, ранний выход при первом успехе.
- **Гибкие условия успеха**: текст на странице, редирект (302/303/307), код ответа.
- **Обход простых защит**: ротация `User-Agent` (`--rotate-ua`) и `X-Forwarded-For` (`--rotate-ip`).
- **Прокси, куки, свои заголовки, задержка между запросами.**

## Установка

```bash
git clone https://github.com/<user>/BruteForce.git
cd BruteForce

python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

pip install -r requirements.txt
```

## Использование

Минимум:

```bash
python brutforce.py -u "https://target.com/login" -w sample_wordlist.txt --user admin
```

Лаба PortSwigger (форма с ошибкой «Invalid username or password»):

```bash
python brutforce.py -u "https://<lab-id>.web-security-academy.net/login" \
  -w sample_wordlist.txt \
  --user wiener \
  --fail-string "Invalid username or password" \
  --check-redirect
```

Автопоиск формы, список логинов, JSON, прокси через Burp:

```bash
python brutforce.py -u "https://target.com/api/login" \
  -w wordlist.txt --userlist users.txt \
  --auto-form --json --check-redirect \
  -t 10 --proxy http://127.0.0.1:8080 \
  -o found.txt
```

### Основные параметры

| Параметр | Описание |
|---|---|
| `-u, --url` | URL формы входа или API |
| `-w, --wordlist` | файл со словарём паролей |
| `--user` / `--userlist` | один логин или файл со списком |
| `-t, --threads` | число потоков (по умолчанию 10) |
| `--auto-form` | автоматически найти форму и поля |
| `--json` | отправлять данные как JSON |
| `--fail-string` | текст ошибки, означающий неудачную попытку |
| `--success-string` | текст, означающий успех |
| `--check-redirect` | считать успехом редирект на другую страницу |
| `--success-code` | ожидаемый код успеха (по умолчанию 200) |
| `--rotate-ua` / `--rotate-ip` | ротация User-Agent / X-Forwarded-For |
| `-H, --header` | свой заголовок, можно несколько раз |
| `-c, --cookie` | стартовые куки |
| `--delay` | задержка между запросами, сек |
| `--proxy` | прокси, например `http://127.0.0.1:8080` |
| `-o, --output` | файл для сохранения найденных пар |

## Словари

В репозитории лежит только `sample_wordlist.txt` для демонстрации.
Реальные словари скачиваются отдельно:

- `rockyou.txt` — в составе Kali Linux (`/usr/share/wordlists/`).
- [SecLists](https://github.com/danielmiessler/SecLists) — `Passwords/` и `Usernames/`.

## Ограничения

- Нет обхода CAPTCHA и двухфакторной аутентификации.
- Нет автоматического определения rate-limit и подстройки скорости.
- Успех определяется эвристиками (`--fail-string`, редирект, код ответа) — под каждую форму их надо подбирать руками.

## Лицензия

MIT — см. [LICENSE](LICENSE).
