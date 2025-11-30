import uuid
from datetime import datetime

def create_message(sender, receiver, payload):
    return {
        'task_id': str(uuid.uuid4()),
        'sender': sender,
        'receiver': receiver,
        'payload': payload,
        'timestamp': datetime.utcnow().isoformat()
    }
