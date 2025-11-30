import logging, json
from datetime import datetime, timezone
logging.basicConfig(level=logging.INFO, format='%(message)s')
class Observability:
    @staticmethod
    def log(event, payload=None, contains_pii=False):
        safe_payload = {'detail': '[REDACTED]'} if contains_pii else (payload or {})
        record = {
            'ts': datetime.now(timezone.utc).isoformat(),
            'event': event,
            'payload': safe_payload,
        }
        logging.info(json.dumps(record))
