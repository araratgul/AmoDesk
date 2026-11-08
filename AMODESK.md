# AmoDesk

AmoDesk — удалённый доступ от Amobit на основе [RustDesk](https://github.com/rustdesk/rustdesk) (AGPL-3.0).

## Как устроен форк

- Ветка `master` повторяет upstream `rustdesk/rustdesk` без изменений.
- Ветка `amodesk` = `master` + каталог `amodesk/` + workflow `.github/workflows/amodesk-*.yml`.
- Бренд накладывается **во время сборки** скриптом [amodesk/rebrand.py](amodesk/rebrand.py) по [amodesk/brand.json](amodesk/brand.json). Исходники RustDesk не правятся, поэтому обновление с upstream — обычный rebase/merge.
- Если upstream поменял строку, которую мы заменяем, скрипт падает с понятной ошибкой, а не собирает клиент с частичным брендом.

## Сборка

GitHub Actions → **AmoDesk Windows** → Run workflow. Артефакт `amodesk-windows-x64` — `AmoDesk-<версия>-x64.exe`.
Тег `amodesk-v*` дополнительно публикует pre-release.

Переменные репозитория (Settings → Secrets and variables → Actions → Variables):

| Переменная | Пример |
|---|---|
| `AMODESK_RENDEZVOUS_SERVER` | `desk.amobit.io` |
| `AMODESK_RS_PUB_KEY` | содержимое `id_ed25519.pub` сервера |
| `AMODESK_API_SERVER` | `https://desk.amobit.io` |

Без них клиент ходит на публичные сервера RustDesk — только для проверки сборки.

Локально: `python amodesk/rebrand.py`, затем обычная сборка RustDesk. Откат: `git checkout -- . && git -C libs/hbb_common checkout -- .`.

## Обновление с upstream

```bash
git fetch upstream
git checkout master && git merge --ff-only upstream/master && git push origin master
git checkout amodesk && git merge master
```

## Лицензия

AGPL-3.0, как у RustDesk. Исходники AmoDesk-клиента публичны в этом репозитории; копирайты RustDesk сохранены.
