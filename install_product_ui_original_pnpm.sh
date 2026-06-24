#!/usr/bin/env bash
set -euo pipefail
ROOT="${1:-/root/edge-ai-deploy-kit}"
UI="$ROOT/product-ui"
ORIG="$ROOT/edgeai-product-ui-productized/product-ui"

if [ ! -d "$UI" ]; then
  echo "[ERROR] product-ui not found: $UI" >&2
  exit 1
fi

cd "$UI"
echo "[1/8] Stop previous npm/node processes"
pkill -f "npm install" 2>/dev/null || true
pkill -f "pnpm install" 2>/dev/null || true
pkill -f "next dev" 2>/dev/null || true

TS="$(date +%Y%m%d_%H%M%S)"
echo "[2/8] Backup current files"
[ -f package.json ] && cp package.json "package.json.bak.$TS"
[ -f components/BenchmarkPanel.tsx ] && cp components/BenchmarkPanel.tsx "components/BenchmarkPanel.tsx.bak.$TS"

# Restore the original visual chart component if the extracted source folder is still present.
if [ -f "$ORIG/components/BenchmarkPanel.tsx" ]; then
  echo "[3/8] Restore original Recharts BenchmarkPanel.tsx"
  cp "$ORIG/components/BenchmarkPanel.tsx" components/BenchmarkPanel.tsx
else
  echo "[3/8] Original extracted BenchmarkPanel not found; keeping current component"
fi

# Strictly restore the original package.json structure: keeps recharts and latest versions.
echo "[4/8] Restore original package.json with Recharts"
cat > package.json <<'JSON'
{
  "name": "edgeai-product-ui",
  "version": "0.2.0",
  "private": true,
  "scripts": {
    "dev": "next dev -H 0.0.0.0 -p 3000",
    "build": "next build",
    "start": "next start -H 0.0.0.0 -p 3000",
    "typecheck": "tsc --noEmit",
    "check": "npm run typecheck"
  },
  "dependencies": {
    "@types/node": "latest",
    "@types/react": "latest",
    "@types/react-dom": "latest",
    "autoprefixer": "latest",
    "clsx": "latest",
    "lucide-react": "latest",
    "next": "latest",
    "postcss": "latest",
    "react": "latest",
    "react-dom": "latest",
    "recharts": "latest",
    "tailwindcss": "latest",
    "typescript": "latest"
  },
  "devDependencies": {}
}
JSON

cat > .npmrc <<'NPMRC'
registry=https://registry.npmmirror.com/
audit=false
fund=false
progress=true
fetch-retries=5
fetch-retry-mintimeout=20000
fetch-retry-maxtimeout=120000
fetch-timeout=600000
prefer-online=true
maxsockets=4
NPMRC

echo "[5/8] Install pnpm from mirror if missing"
if ! command -v pnpm >/dev/null 2>&1; then
  npm install -g pnpm --registry=https://registry.npmmirror.com --no-audit --no-fund
fi

pnpm config set registry https://registry.npmmirror.com
pnpm config set network-timeout 600000
pnpm config set fetch-timeout 600000
pnpm config set child-concurrency 2
pnpm config set prefer-frozen-lockfile false

echo "[6/8] Clean old install state"
rm -rf node_modules package-lock.json pnpm-lock.yaml yarn.lock
# Do not remove the whole pnpm store; keeping it helps retry.

echo "[7/8] Install dependencies using pnpm"
pnpm install --reporter=append-only

echo "[8/8] Typecheck"
pnpm run typecheck

echo "DONE. Start frontend with:"
echo "  cd $UI && pnpm dev"
