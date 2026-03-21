#!/usr/bin/env python3
"""
===== CLI 方式 =====
传统的命令行工具：Agent 通过 subprocess 调用此脚本，
解析 stdout 的文本输出来获取结果。

用法:
  python obs_cli.py health <service_name>
  python obs_cli.py alerts [--service <name>] [--severity <level>]
  python obs_cli.py list-services
"""

import argparse
import json
import sys
import os

# 让 import 能找到 backend
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from backend.observability_service import get_service_health, get_recent_alerts, list_services


def main():
    parser = argparse.ArgumentParser(description="Observability CLI Tool")
    subparsers = parser.add_subparsers(dest="command")

    # health 子命令
    health_parser = subparsers.add_parser("health", help="Check service health")
    health_parser.add_argument("service", type=str, help="Service name")

    # alerts 子命令
    alerts_parser = subparsers.add_parser("alerts", help="Get recent alerts")
    alerts_parser.add_argument("--service", type=str, default=None)
    alerts_parser.add_argument("--severity", type=str, default=None)

    # list-services 子命令
    subparsers.add_parser("list-services", help="List all services")

    args = parser.parse_args()

    if args.command == "health":
        result = get_service_health(args.service)
        print(json.dumps(result, indent=2))

    elif args.command == "alerts":
        result = get_recent_alerts(args.service, args.severity)
        print(json.dumps(result, indent=2, default=str))

    elif args.command == "list-services":
        result = list_services()
        print(json.dumps(result, indent=2))

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
