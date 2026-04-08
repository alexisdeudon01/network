#!/usr/bin/with-contenv bash
set -euo pipefail

CONFIG_PATH=/data/options.json
ENV_PATH=/data/.env
BIN_DIR=/opt/fritzbox-agent/bin
MCP_BIN="${BIN_DIR}/fritz-mcp"
MCP_RELEASE_BASE="https://github.com/kambriso/fritzbox-mcp-server/releases/latest/download"

mkdir -p "${BIN_DIR}" /data /var/log/fritzbox-agent

log() {
  echo "[fritzbox-network-agent] $*"
}

read_option() {
  local key="$1"
  jq -r --arg k "$key" '.[$k] // empty' "${CONFIG_PATH}"
}

detect_arch() {
  case "$(uname -m)" in
    x86_64) echo "linux-amd64" ;;
    aarch64|arm64) echo "linux-arm64" ;;
    *)
      log "Unsupported architecture: $(uname -m)"
      exit 1
      ;;
  esac
}

download_mcp() {
  local arch="$1"
  local tmp_bin="${MCP_BIN}.tmp"
  local checksums="${BIN_DIR}/checksums.txt"
  local asset="fritz-mcp-${arch}"

  if [[ -x "${MCP_BIN}" ]]; then
    log "fritz-mcp binary already present; skipping download"
    return
  fi

  log "Downloading ${asset}"
  curl -fL "${MCP_RELEASE_BASE}/${asset}" -o "${tmp_bin}"
  curl -fL "${MCP_RELEASE_BASE}/checksums.txt" -o "${checksums}"

  local expected
  expected="$(awk -v f="${asset}" '$2==f {print $1}' "${checksums}")"
  if [[ -z "${expected}" ]]; then
    log "Could not find checksum for ${asset}"
    exit 1
  fi

  local actual
  actual="$(sha256sum "${tmp_bin}" | awk '{print $1}')"
  if [[ "${actual}" != "${expected}" ]]; then
    log "Checksum mismatch for ${asset}: expected ${expected}, got ${actual}"
    exit 1
  fi

  mv "${tmp_bin}" "${MCP_BIN}"
  chmod +x "${MCP_BIN}"
  log "fritz-mcp installed at ${MCP_BIN}"
}

write_env() {
  local fritz_host fritz_port fritz_username fritz_password ha_url ha_token
  fritz_host="$(read_option fritz_host)"
  fritz_port="$(read_option fritz_port)"
  fritz_username="$(read_option fritz_username)"
  fritz_password="$(read_option fritz_password)"
  ha_url="$(read_option ha_url)"
  ha_token="$(read_option ha_token)"

  cat > "${ENV_PATH}" <<ENV
FRITZ_HOST=${fritz_host}
FRITZ_PORT=${fritz_port}
FRITZ_USERNAME=${fritz_username}
FRITZ_PASSWORD=${fritz_password}
HA_URL=${ha_url}
HA_TOKEN=${ha_token}
AUTO_REFRESH_SECONDS=$(read_option auto_refresh_seconds)
MCP_BINARY=${MCP_BIN}
MCP_HOST=0.0.0.0
MCP_PORT=8098
FLASK_HOST=0.0.0.0
FLASK_PORT=8099
ENV
  chmod 600 "${ENV_PATH}"
  cp "${ENV_PATH}" /opt/fritzbox-agent/.env
}

main() {
  if [[ ! -f "${CONFIG_PATH}" ]]; then
    log "Missing ${CONFIG_PATH}; are you running in Home Assistant add-on runtime?"
    exit 1
  fi

  local arch
  arch="$(detect_arch)"
  download_mcp "${arch}"
  write_env

  log "Starting services"
  exec s6-svscan /etc/services.d
}

main "$@"
