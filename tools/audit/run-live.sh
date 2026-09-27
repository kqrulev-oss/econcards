#!/usr/bin/env bash
# Проверка сайта целиком (по умолчанию — живого): адреса, пути, офлайн, скорость, обход всех ссылок и кнопок.
# Ничего не записывает на сервер (см. lib.cjs). Итог — $OUT/report.md.
#   bash tools/audit/run-live.sh [BASE]
#   QUICK=1 — без обхода всех кнопок (он самый долгий, ~30–60 мин)
set -u
cd "$(dirname "$0")/../.."
export BASE="${1:-${BASE:-https://econcards.kqrulev.workers.dev}}"
export OUT="${OUT:-$PWD/tools/audit/out/$(date +%Y%m%d-%H%M)}"
export NODE_PATH="${NODE_PATH:-$(npm root -g)}"
export NODE_USE_ENV_PROXY=1   # встроенный fetch в Node идёт через HTTPS_PROXY, если он задан
mkdir -p "$OUT"
echo "Проверяю $BASE → $OUT"

node tools/audit/http.mjs 2>&1 | tee "$OUT/http.log"
for w in 375 1280; do node tools/audit/journeys.cjs "$w" light 2>&1 | tee "$OUT/journeys-$w.log"; done
node tools/audit/journeys.cjs 375 dark 2>&1 | tee "$OUT/journeys-375-dark.log"
node tools/audit/offline.cjs 375 2>&1 | tee "$OUT/offline.log"

# Медленная сеть: свой прокси с задержкой (останавливаем по PID)
TPORT="${TPORT:-8899}" node tools/audit/throttle-proxy.mjs > "$OUT/throttle.log" 2>&1 &
TP=$!
sleep 1
THROTTLE_PROXY="http://127.0.0.1:${TPORT:-8899}" node tools/audit/perf.cjs 375 2>&1 | tee "$OUT/perf.log"
kill "$TP" 2>/dev/null

if [ -z "${QUICK:-}" ]; then
  for p in guest guest-draft library; do
    for w in 375 1280; do node tools/audit/crawl.cjs "$p" "$w" > "$OUT/crawl-$p-$w.log" 2>&1; tail -1 "$OUT/crawl-$p-$w.log"; done
  done
fi

node tools/audit/report.cjs > "$OUT/report.md"
echo "Готово: $OUT/report.md"
