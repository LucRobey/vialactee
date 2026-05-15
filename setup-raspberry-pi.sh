#!/usr/bin/env bash
#
# Vialactée — one-time Raspberry Pi deployment
#
# Run once on the Pi (as the user that will run Main.py):
#   chmod +x setup-raspberry-pi.sh
#   ./setup-raspberry-pi.sh
#
# Or bootstrap without a local copy:
#   curl -fsSL https://raw.githubusercontent.com/LucRobey/vialactee/main/setup-raspberry-pi.sh -o setup-raspberry-pi.sh
#   chmod +x setup-raspberry-pi.sh && ./setup-raspberry-pi.sh
#
# This script:
#   1. Stops any running Vialactée processes
#   2. Removes previous Vialactée project folders and virtualenvs
#   3. Clones (or updates) https://github.com/LucRobey/vialactee.git
#   4. Creates a Python venv, installs dependencies, builds python_btrack
#   5. Installs Node.js deps for wabb-interface (used by Main.py on first launch)
#
# Override defaults:
#   VIALACTEE_HOME=~/projects/vialactee VIALACTEE_BRANCH=main ./setup-raspberry-pi.sh

set -euo pipefail

REPO_URL="${VIALACTEE_REPO_URL:-https://github.com/LucRobey/vialactee.git}"
BRANCH="${VIALACTEE_BRANCH:-main}"
INSTALL_DIR="${VIALACTEE_HOME:-${HOME}/vialactee}"
VENV_DIR="${INSTALL_DIR}/.venv"

# Previous install locations to remove (add paths here if you used others).
LEGACY_DIRS=(
  "${HOME}/vialactee"
  "${HOME}/vialactée"
  "${HOME}/Vialactee"
  "${HOME}/vialactee-old"
  "${HOME}/projects/vialactee"
  "/opt/vialactee"
)

log() { printf '\n[%s] %s\n' "$(date '+%H:%M:%S')" "$*"; }
die() { printf '\nERROR: %s\n' "$*" >&2; exit 1; }

require_command() {
  command -v "$1" >/dev/null 2>&1 || die "Missing command: $1"
}

stop_vialactee_processes() {
  log "Stopping running Vialactée / Main.py processes..."
  pkill -f '[Mm]ain\.py' 2>/dev/null || true
  pkill -f 'vialactee' 2>/dev/null || true
  pkill -f 'wabb-interface' 2>/dev/null || true
  pkill -f 'vite.*5173' 2>/dev/null || true
  sleep 1
}

remove_legacy_installations() {
  log "Removing previous Vialactée project folders..."
  local dir
  for dir in "${LEGACY_DIRS[@]}"; do
  [[ -z "${dir}" ]] && continue
  if [[ -d "${dir}" ]]; then
    if [[ "${dir}" == "${INSTALL_DIR}" ]]; then
      log "  (skip active target) ${dir}"
      continue
    fi
    log "  rm -rf ${dir}"
    rm -rf "${dir}"
  fi
  done

  # Drop stray virtualenvs named after the project.
  rm -rf "${HOME}/.virtualenvs/vialactee" 2>/dev/null || true
  rm -rf "${HOME}/venv-vialactee" 2>/dev/null || true
}

install_system_packages() {
  log "Installing system packages (sudo required)..."
  require_command sudo
  sudo apt-get update -qq
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
    git \
    curl \
    python3 \
    python3-venv \
    python3-pip \
    python3-dev \
    build-essential \
    libportaudio2 \
    portaudio19-dev \
    libatlas-base-dev \
    pkg-config \
    nodejs \
    npm
}

ensure_node() {
  if command -v node >/dev/null 2>&1 && command -v npm >/dev/null 2>&1; then
    log "Node.js $(node -v), npm $(npm -v)"
    return
  fi
  die "Node.js/npm not available after apt install."
}

clone_or_update_repo() {
  log "Fetching code from ${REPO_URL} (branch: ${BRANCH})..."
  require_command git

  if [[ -d "${INSTALL_DIR}/.git" ]]; then
    log "Existing git repo at ${INSTALL_DIR} — resetting to origin/${BRANCH}..."
    git -C "${INSTALL_DIR}" fetch origin
    git -C "${INSTALL_DIR}" checkout "${BRANCH}"
    git -C "${INSTALL_DIR}" reset --hard "origin/${BRANCH}"
    git -C "${INSTALL_DIR}" clean -fdx
  else
    rm -rf "${INSTALL_DIR}"
    git clone --branch "${BRANCH}" --depth 1 "${REPO_URL}" "${INSTALL_DIR}"
  fi
}

setup_python_environment() {
  log "Creating Python virtual environment..."
  require_command python3
  python3 -m venv "${VENV_DIR}"
  # shellcheck disable=SC1091
  source "${VENV_DIR}/bin/activate"
  python -m pip install --upgrade pip wheel setuptools

  log "Installing Python dependencies..."
  pip install \
    numpy \
    sounddevice \
    aiohttp \
    pillow \
    cython

  # NeoPixels on GPIO (HardwareFactory "rpi" mode).
  pip install \
    adafruit-blinka \
    adafruit-circuitpython-neopixel

  log "Building python_btrack (Cython)..."
  pushd "${INSTALL_DIR}/python_btrack" >/dev/null
  python setup.py build_ext --inplace
  popd >/dev/null

  # Convenience: run Main.py without activating venv manually.
  cat > "${INSTALL_DIR}/run-vialactee.sh" <<EOF
#!/usr/bin/env bash
set -euo pipefail
cd "${INSTALL_DIR}"
source "${VENV_DIR}/bin/activate"
export PYTHONPATH="${INSTALL_DIR}:${INSTALL_DIR}/python_btrack:\${PYTHONPATH:-}"
exec python Main.py "\$@"
EOF
  chmod +x "${INSTALL_DIR}/run-vialactee.sh"
}

setup_web_interface() {
  log "Installing wabb-interface npm dependencies..."
  pushd "${INSTALL_DIR}/wabb-interface" >/dev/null
  npm install
  popd >/dev/null
}

print_summary() {
  local ip
  ip="$(hostname -I 2>/dev/null | awk '{print $1}')"
  cat <<EOF

================================================================================
 Vialactée Raspberry Pi setup complete
================================================================================
  Project path : ${INSTALL_DIR}
  Virtual env  : ${VENV_DIR}
  Run command  : ${INSTALL_DIR}/run-vialactee.sh

  Web UI (after Main.py starts):
    http://${ip:-<PI_IP>}:5173

  See connect.md in the repo for network troubleshooting.

  Optional: add to ~/.bashrc:
    alias vialactee='${INSTALL_DIR}/run-vialactee.sh'
================================================================================
EOF
}

main() {
  if [[ "$(uname -s)" != "Linux" ]]; then
    die "This script must run on Linux (Raspberry Pi OS)."
  fi

  log "Vialactée setup — target: ${INSTALL_DIR}"
  stop_vialactee_processes
  remove_legacy_installations
  install_system_packages
  ensure_node
  clone_or_update_repo
  setup_python_environment
  setup_web_interface
  print_summary
}

main "$@"
