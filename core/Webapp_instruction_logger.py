import json
from datetime import datetime
from typing import Any, Dict


class WebappInstructionLogger:
    """
    Temporary sink for webapp instructions.
    For now it only prints every instruction received from the web interface.
    """

    def log_raw_instruction(self, raw_message: str) -> None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        try:
            parsed: Dict[str, Any] = json.loads(raw_message)
        except json.JSONDecodeError:
            print(f"[WebAppInstruction][{timestamp}] raw={raw_message}")
            return

        page = parsed.get("page", "unknown")
        action = parsed.get("action", "unknown")
        payload = parsed.get("payload", {})
        sent_at = parsed.get("timestamp", "unknown")
        print(
            f"[WebAppInstruction][{timestamp}] "
            f"page={page} action={action} payload={payload} sent_at={sent_at}"
        )
