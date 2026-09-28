# Как перезаписать `assets/cli-demo.gif`

GIF записан с помощью [vhs](https://github.com/charmbracelet/vhs) на открытом корпусе из
бенчмарка (577 BSL-файлов, Connector, YAxUnit, xUnitFor1C). Результаты в ролике — настоящий
вывод CLI, ничего не дорисовано.

```bash
# 1. Установить CLI и скачать корпус (точные commit SHA из манифеста)
python3.11 -m venv .venv && .venv/bin/python -m pip install .
.venv/bin/python scripts/fetch_corpus.py \
  --sources studies/oss-bsl-corpus-2026-08-10/sources.json \
  --target corpus --manifest /tmp/corpus-manifest.json

# 2. Записать ролик (нужны vhs, ttyd, ffmpeg и Chromium)
vhs scripts/demo/demo.tape
```

`play.sh` сам «набирает» команды: vhs некорректно вводит кириллицу через эмуляцию клавиатуры.
Каталог `corpus/` в Git не добавляется.
