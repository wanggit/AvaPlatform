#!/bin/bash
# 旧版原型启动脚本：只启动 web 目录下的前端原型。
set -e

cd "$(dirname "$0")/web"

if [ ! -d "node_modules" ]; then
  echo "Installing dependencies..."
  npm install
fi

echo "Starting AI Digital Employee Platform prototype..."
npx vite --host 0.0.0.0
