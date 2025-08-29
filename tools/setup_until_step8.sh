#!/usr/bin/env bash
# Automate docs/setup.md steps 1–8 on Ubuntu 24.04
# - Installs deps
# - Configures PostgreSQL + PostGIS + imports JMA districts
# - Installs Dragonfly and configures systemd (6379/6380)
# - Sets up Python venv and installs deps
# - Prepares .env
# - Starts servers in background and performs initial data update
# - Uploads weather report to Report server

set -euo pipefail

# ------------ Config (override via env) ------------
DB_USER=${DB_USER:-wip}
DB_PASS=${DB_PASS:-wippass}
DB_NAME=${DB_NAME:-weather_forecast_map}
PGHOST=${PGHOST:-127.0.0.1}
JMA_ZIP_URL=${JMA_ZIP_URL:-"https://www.data.jma.go.jp/developer/gis/20190125_AreaForecastLocalM_1saibun_GIS.zip"}
AREA_CODE=${AREA_CODE:-130010}
PROJECT_ROOT=$(cd "$(dirname "$0")/.." && pwd)
LOG_DIR="$PROJECT_ROOT/logs"

APT_PACKAGES=(
  git curl build-essential cmake pkg-config \
  python3 python3-venv python3-pip \
  postgresql postgresql-contrib postgis gdal-bin \
  libpq-dev \
  jq unzip wget
)

REDIS_DATA_PORT=${REDIS_DATA_PORT:-6379}
REDIS_LOG_PORT=${REDIS_LOG_PORT:-6380}

echo "[setup] Starting setup (steps 1–8)"

needsudo() {
  if [ "${EUID:-$(id -u)}" -ne 0 ]; then echo sudo; else echo; fi
}

SUDO=$(needsudo)

have() { command -v "$1" >/dev/null 2>&1; }

# ------------ Step 2: Install packages ------------
if have apt-get; then
  echo "[setup] Installing required packages via apt-get"
  $SUDO apt-get update -y
  DEBIAN_FRONTEND=noninteractive $SUDO apt-get install -y "${APT_PACKAGES[@]}"
else
  echo "[warn] apt-get not found. Please run on Ubuntu/Debian-compatible system."
  exit 1
fi

# ------------ Step 3: PostgreSQL + PostGIS ------------
echo "[setup] Enabling and starting PostgreSQL"
$SUDO systemctl enable --now postgresql || true

echo "[setup] Creating PostgreSQL role and database (idempotent)"
psql_exec() {
  PGPASSWORD=${DB_PASS} psql -h "$PGHOST" -U "$DB_USER" -d "$DB_NAME" -v ON_ERROR_STOP=1 -c "$1"
}

# Create role if not exists (as postgres superuser)
$SUDO -u postgres bash -lc "psql -tc \"SELECT 1 FROM pg_roles WHERE rolname='${DB_USER}'\" | grep -q 1 || psql -c \"CREATE ROLE ${DB_USER} WITH LOGIN PASSWORD '${DB_PASS}';\""
# Ensure CREATEDB
$SUDO -u postgres psql -c "ALTER ROLE ${DB_USER} CREATEDB;" || true

# Create database if not exists and add extensions
$SUDO -u postgres bash -lc "psql -tc \"SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'\" | grep -q 1 || psql -c \"CREATE DATABASE ${DB_NAME} OWNER ${DB_USER};\""

PGPASSWORD=${DB_PASS} psql -h "$PGHOST" -U "$DB_USER" -d "$DB_NAME" -v ON_ERROR_STOP=1 <<'SQL'
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
SQL

# ------------ Step 3.4: Import JMA districts ------------
TMPDIR=$(mktemp -d)
echo "[setup] Downloading JMA district shapefile to $TMPDIR"
(
  cd "$TMPDIR"
  wget -O jma_area.zip "$JMA_ZIP_URL"
  unzip -o jma_area.zip -d jma_area
  SHP_FILE=$(ls -1 jma_area/*.shp 2>/dev/null | head -n1 || true)
  if [ -z "$SHP_FILE" ]; then
    echo "[error] No .shp found under $TMPDIR/jma_area. Aborting." >&2
    exit 1
  fi
  echo "[setup] Found shapefile: $SHP_FILE"
  echo "[setup] Converting shapefile to SQL (SRID 6668)"
  shp2pgsql -W utf-8 -D -I -s 6668 "$SHP_FILE" public.jma_districts_raw > jma_insert.sql
  echo "[setup] Importing into PostgreSQL"
  PGPASSWORD=${DB_PASS} psql -h "$PGHOST" -U "$DB_USER" -d "$DB_NAME" -f jma_insert.sql
)

echo "[setup] Normalizing table to expected schema: public.districts(geom, code)"
PGPASSWORD=${DB_PASS} psql -h "$PGHOST" -U "$DB_USER" -d "$DB_NAME" -v ON_ERROR_STOP=1 <<'SQL'
DO $$
DECLARE
  has_raw bool;
  has_districts bool;
  candidate text;
BEGIN
  SELECT EXISTS (
    SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='jma_districts_raw'
  ) INTO has_raw;

  SELECT EXISTS (
    SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='districts'
  ) INTO has_districts;

  IF has_raw AND NOT has_districts THEN
    EXECUTE 'ALTER TABLE public.jma_districts_raw RENAME TO districts';
  END IF;

  -- Ensure geom exists; if different name, try to rename most common variants
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name='districts' AND column_name='geom'
  ) THEN
    -- Common default from shp2pgsql is "geom"
    -- If not present, try "wkb_geometry" or "geometry"
    IF EXISTS (
      SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name='districts' AND column_name='wkb_geometry'
    ) THEN
      EXECUTE 'ALTER TABLE public.districts RENAME COLUMN wkb_geometry TO geom';
    ELSIF EXISTS (
      SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name='districts' AND column_name='geometry'
    ) THEN
      EXECUTE 'ALTER TABLE public.districts RENAME COLUMN geometry TO geom';
    END IF;
  END IF;

  -- Ensure code column exists and populated from a likely source
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name='districts' AND column_name='code'
  ) THEN
    EXECUTE 'ALTER TABLE public.districts ADD COLUMN code text';
  END IF;

  -- Try to populate code from likely columns (case-insensitive matches)
  FOR candidate IN
    SELECT column_name
    FROM information_schema.columns
    WHERE table_schema='public' AND table_name='districts'
      AND lower(column_name) IN (
        'code','areacode','area_code','区分コード','区域コード','一次細分コード','市町村コード','コード'
      )
  LOOP
    EXECUTE format('UPDATE public.districts SET code = %I::text WHERE code IS NULL OR code = ''''''''', candidate);
  END LOOP;

  -- Enforce basic index
  IF NOT EXISTS (
    SELECT 1 FROM pg_indexes WHERE schemaname='public' AND indexname='districts_geom_gist'
  ) THEN
    EXECUTE 'CREATE INDEX districts_geom_gist ON public.districts USING gist (geom)';
  END IF;
END $$;
SQL

# ------------ Step 4: Dragonfly install + systemd ------------
echo "[setup] Installing Dragonfly (Redis-compatible)"
(
  cd /tmp
  wget -O dragonfly_amd64.deb https://dragonflydb.gateway.scarf.sh/latest/dragonfly_amd64.deb
  $SUDO apt-get install -y ./dragonfly_amd64.deb
)

echo "[setup] Creating Dragonfly data dirs"
$SUDO mkdir -p "/var/lib/dragonfly/${REDIS_DATA_PORT}" "/var/lib/dragonfly/${REDIS_LOG_PORT}"

echo "[setup] Writing systemd units"
DFLY_BIN=$([ -x /usr/bin/dragonfly ] && echo /usr/bin/dragonfly || echo dragonfly)

sudo tee /etc/systemd/system/dragonfly-${REDIS_DATA_PORT}.service >/dev/null <<EOF
[Unit]
Description=Dragonfly (data) on ${REDIS_DATA_PORT}
After=network.target

[Service]
ExecStart=${DFLY_BIN} --port=${REDIS_DATA_PORT} --dir=/var/lib/dragonfly/${REDIS_DATA_PORT}
Restart=always
LimitNOFILE=100000

[Install]
WantedBy=multi-user.target
EOF

sudo tee /etc/systemd/system/dragonfly-${REDIS_LOG_PORT}.service >/dev/null <<EOF
[Unit]
Description=Dragonfly (log pubsub) on ${REDIS_LOG_PORT}
After=network.target

[Service]
ExecStart=${DFLY_BIN} --port=${REDIS_LOG_PORT} --dir=/var/lib/dragonfly/${REDIS_LOG_PORT}
Restart=always
LimitNOFILE=100000

[Install]
WantedBy=multi-user.target
EOF

echo "[setup] Enabling Dragonfly services"
$SUDO systemctl daemon-reload
$SUDO systemctl enable --now dragonfly-${REDIS_DATA_PORT} dragonfly-${REDIS_LOG_PORT}
$SUDO systemctl --no-pager --full status dragonfly-${REDIS_DATA_PORT} || true

# ------------ Step 5: Python venv + deps ------------
echo "[setup] Preparing Python virtualenv and installing dependencies"
cd "$PROJECT_ROOT"
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
pip install -e .[all]

# ------------ Step 6: .env ------------
if [ ! -f .env ]; then
  echo "[setup] Creating .env from .env.example"
  cp .env.example .env
else
  echo "[setup] .env already exists; keeping current values"
fi

# Ensure ports in .env align with docs defaults if not present
grep -q '^MAP_HTTP_PORT=' .env || echo 'MAP_HTTP_PORT=8000' >> .env
grep -q '^WEATHER_API_PORT=' .env || echo 'WEATHER_API_PORT=8001' >> .env
grep -q '^REDIS_PORT=' .env || echo "REDIS_PORT=${REDIS_DATA_PORT}" >> .env
grep -q '^LOG_REDIS_PORT=' .env || echo "LOG_REDIS_PORT=${REDIS_LOG_PORT}" >> .env

# ------------ Step 7: Start servers and initialize data ------------
mkdir -p "$LOG_DIR"
echo "[setup] Starting servers in background (logs in $LOG_DIR)"
(
  set -m
  nohup python python/launch_server.py --apps     > "$LOG_DIR/apps.log"     2>&1 &
  nohup python python/launch_server.py --report   > "$LOG_DIR/report.log"   2>&1 &
  nohup python python/launch_server.py --location > "$LOG_DIR/location.log" 2>&1 &
  nohup python python/launch_server.py --query    > "$LOG_DIR/query.log"    2>&1 &
  nohup python python/launch_server.py --weather  > "$LOG_DIR/weather.log"  2>&1 &
)

echo "[setup] Waiting for APIs to become ready..."
sleep 5

echo "[setup] Forcing initial data update from JMA"
curl -fsS -X POST http://localhost:8001/api/update/weather || true
curl -fsS -X POST http://localhost:8001/api/update/disaster || true

echo "[setup] Health check"
curl -fsS http://localhost:8001/api/health || true

# ------------ Step 8: Upload weather to Report server ------------
echo "[setup] Fetching latest weather for area ${AREA_CODE}"
read WC TEMP POP < <(curl -fsS "http://localhost:8000/api/weather?area_code=${AREA_CODE}" | jq -r '[.weather,.temperature,.precipitation_prob] | @tsv')
echo "[setup] weather=$WC temp=$TEMP pop=$POP"

echo "[setup] Sending report to Report server"
python python/client.py --report \
  --area "${AREA_CODE}" \
  --weather "${WC:-}" \
  --pops "${POP:-}" \
  --temp "${TEMP:-}"

echo "[setup] Done. Check $LOG_DIR/*.log for server outputs."

