#!/usr/bin/env bash
# ЛР: замените имя файла на свою фамилию, если требует преподаватель (например Иванов2.sh)
set -euo pipefail

OUT="testfile.sh"
cat > "$OUT" <<'EOS'
#!/usr/bin/env bash
echo "testfile.sh: OK"
EOS
chmod +x "$OUT"
echo "Создан $OUT"
echo "--- длинный список файлов (текущий каталог) ---"
ls -la
