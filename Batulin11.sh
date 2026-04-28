#!/usr/bin/env bash
set -euo pipefail

OUT="testfile.sh"
cat > "$OUT" <<'EOS'
#!/usr/bin/env bash
echo "testfile.sh: OK"
EOS
chmod +x "$OUT"
echo "Создан $OUT"
echo
ls -la
