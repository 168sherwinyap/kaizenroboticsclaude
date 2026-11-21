# Shared by the .sh launchers. Source it after cd-ing to the repository root.
#   $PY       the Python to use: .venv (made by ./setup.sh) if present, else python3
#   open_url  opens a URL in Chrome or Edge, because the browser apps need Web
#             Serial and Safari and Firefox do not have it

if [ -x .venv/bin/python ]; then
  PY="$PWD/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PY=python3
else
  PY=python
fi

open_url() {
  if [ "$(uname)" = "Darwin" ]; then
    open -a "Google Chrome" "$1" 2>/dev/null \
      || open -a "Microsoft Edge" "$1" 2>/dev/null \
      || { echo "Chrome or Edge not found. Open $1 in one of them: Safari and Firefox cannot connect to the board."; open "$1"; }
  elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$1"
  fi
}
