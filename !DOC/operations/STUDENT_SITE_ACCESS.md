# Доступ к EGE Mentor для ученицы

Сайт работает через Tailscale. Это как закрытая семейная сеть: ссылка открывается
только на устройствах, где Tailscale включен и устройство добавлено в нашу сеть.

## Что нажимать

1. Установи Tailscale:
   - iPhone/iPad: https://tailscale.com/download/ios
   - Android: https://tailscale.com/download/android
   - Windows: https://tailscale.com/download/windows
   - Общая страница: https://tailscale.com/download

2. Открой приложение Tailscale.

3. Нажми `Sign in` / `Войти`.

4. Не вводи логин и пароль родителя. Родитель пришлет invite/share-ссылку
   Tailscale или скажет, каким твоим аккаунтом войти: Google, Apple, Microsoft
   или passkey.

5. Если приложение просит подтвердить VPN-подключение, нажми `Allow` /
   `Разрешить`.

6. Проверь, что Tailscale включен. В приложении должно быть состояние вроде
   `Connected` / `Подключено`.

7. Открой сайт:
   - Главная: http://100.113.226.52:8088
   - Программа: http://100.113.226.52:8088/program
   - Сегодня: http://100.113.226.52:8088/daily
   - Срез: http://100.113.226.52:8088/slice
   - Повторение: http://100.113.226.52:8088/review
   - Визуализация по векторам: http://100.113.226.52:8088/theory/00000000-0000-0000-0000-000000005012

8. Telegram-бот:
   - https://t.me/egemathandinformbot
   - В боте можно нажать `/today`, `/slice`, `/progress`, `/ready`.

## Если сайт не открылся

1. Проверь, что Tailscale включен.
2. Закрой и снова открой Tailscale.
3. Открой ссылку еще раз: http://100.113.226.52:8088
4. Если не открывается, напиши родителю: `Tailscale включен, сайт не открывается`.

## Для родителя

Не передавать ученице свой логин/пароль Tailscale. Лучше один из двух вариантов:

1. Самый аккуратный: ученица входит в Tailscale своим аккаунтом, а родитель
   шарит ей только серверную машину `badmaev` из Tailscale admin console.
2. Простой семейный вариант: родитель приглашает ученицу в свой tailnet как
   обычного пользователя без admin-прав.

Текущий рабочий адрес сайта:

```text
http://100.113.226.52:8088
```

На машине с сервером проверка:

```powershell
curl.exe http://100.113.226.52:8088/api/health
docker compose ps
docker compose exec -T bot printenv PUBLIC_FRONTEND_BASE_URL VITE_OPERATOR_MODE_AVAILABLE
```

Ожидаемо:

```text
{"status":"healthy"}
PUBLIC_FRONTEND_BASE_URL=http://100.113.226.52:8088
VITE_OPERATOR_MODE_AVAILABLE=false
```
