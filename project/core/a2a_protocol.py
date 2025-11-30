import uuid
from datetime import datetime, timezone

def create_message(sender, receiver, payload):
    return {
        'task_id': str(uuid.uuid4()),
        'sender': sender,
        'receiver': receiver,
        'payload': payload,
        'timestamp': datetime.now(timezone.utc).isoformat()
    }
