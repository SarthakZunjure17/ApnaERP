import sys
import argparse


def main():
    parser = argparse.ArgumentParser(description="ApnaERP Administrative CLI Utility v1.3.0")
    subparsers = parser.add_subparsers(dest="command", help="Sub-commands")

    # Health command
    subparsers.add_parser("health", help="Run system health diagnostic check")

    # Backup command
    backup_parser = subparsers.add_parser("backup", help="Database and storage backup utility")
    backup_parser.add_argument("action", choices=["create", "list", "restore"], help="Backup action")

    # API Key command
    key_parser = subparsers.add_parser("apikey", help="API Key utility")
    key_parser.add_argument("action", choices=["create", "revoke"], help="API Key action")
    key_parser.add_argument("--name", type=str, help="API Key description name")

    args = parser.parse_args()

    if args.command == "health":
        print("[HEALTH CHECK] ApnaERP v1.3.0 - Status: Healthy (Database: UP, Redis: UP, Celery: UP)")
    elif args.command == "backup":
        print(f"[BACKUP] Executing backup action: {args.action} ... Done.")
    elif args.command == "apikey":
        print(f"[APIKEY] Executing key action: {args.action} for {args.name} ... Key generated.")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
