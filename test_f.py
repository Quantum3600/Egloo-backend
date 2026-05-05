import asyncio
from app.ai.digest_ai import extract_action_items

fake_chunks = [
    {
        'content': 'Can you reply to Rohit about the new launch date?',
        'chunk_metadata': {'source_type': 'slack', 'sender': 'manager'}
    },
    {
        'content': 'The design review is due tomorrow morning.',
        'chunk_metadata': {'source_type': 'gmail', 'sender': 'designer@co.com'}
    },
]

async def test():
    items = await extract_action_items(fake_chunks)
    for item in items:
        print(f"Task: {item['task']}")
        print(f"  Urgency: {item['urgency']}")
        print(f"  Due: {item['due_hint']}")
        print()

asyncio.run(test())
