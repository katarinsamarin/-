from __future__ import annotations

import argparse
import json
import sys

from .config import Config
from .scraper import scrape
from .state import diff, load_state, save_state
from .telegram import format_changes, send_message


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    cfg = Config()
    snapshot = scrape(cfg.url, cfg.groups)

    print(json.dumps(snapshot, ensure_ascii=False, indent=2))

    old = load_state(cfg.state_file)

    # First run: create baseline without notification.
    if old is None:
        save_state(cfg.state_file, snapshot)
        print("No previous state: baseline created, notification skipped.")
        return 0

    added, changed, removed = diff(old, snapshot)

    if not (added or changed or removed):
        print("No changes.")
        save_state(cfg.state_file, snapshot)
        return 0

    message = format_changes(added, changed, removed)

    if args.dry_run:
        print("\n--- TELEGRAM PREVIEW ---\n")
        print(message)
    else:
        if not cfg.telegram_token or not cfg.telegram_chat_id:
            raise RuntimeError(
                "TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are required "
                "when changes are found."
            )
        # Telegram accepts up to 4096 chars. Split conservatively.
        chunks = []
        while len(message) > 3900:
            cut = message.rfind("\n\n", 0, 3900)
            if cut < 500:
                cut = 3900
            chunks.append(message[:cut])
            message = message[cut:].lstrip()
        if message:
            chunks.append(message)

        for chunk in chunks:
            send_message(cfg.telegram_token, cfg.telegram_chat_id, chunk)

    save_state(cfg.state_file, snapshot)
    return 0


if __name__ == "__main__":
    sys.exit(main())
