#!/bin/bash
set -e
cd "$(dirname "$0")"

if ! command -v python3 >/dev/null 2>&1; then
  echo "未找到 Python 3。请先安装 Python 3，再重新打开本文件。"
  read -r -p "按回车键退出..."
  exit 1
fi

if [ ! -x .venv/bin/python3 ]; then
  python3 -m venv .venv
fi

if [ ! -f .venv/.pinhaoti-ready ]; then
  echo "首次启动：正在安装拼好题所需组件，请稍候..."
  if ! .venv/bin/python3 -m pip install --disable-pip-version-check --index-url https://pypi.org/simple -r requirements.txt; then
    echo "组件安装失败。请检查网络后重试。"
    read -r -p "按回车键退出..."
    exit 1
  fi
  touch .venv/.pinhaoti-ready
fi

.venv/bin/python3 -m pinhaoti.web
