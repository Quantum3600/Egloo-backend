import asyncio
from app.ai.digest_ai import cluster_into_topics

fake_chunks = [
    {
        'content': 'Project Alpha launch delayed to May 10 due to QA bugs',
        'chunk_metadata': {'source_type': 'gmail', 'sender': 'rohit@co.com', 'subject': 'Launch update'}
    },
    {
        'content': 'Budget for Q2 approved by CFO — 120k confirmed',
        'chunk_metadata': {'source_type': 'gmail', 'sender': 'cfo@co.com', 'subject': 'Budget'}
    },
    {
        'content': 'Please review the Figma mockups before EOD today',
        'chunk_metadata': {'source_type': 'slack', 'sender': 'designer', 'subject': ''}
    },
]

async def test():
    topics = await cluster_into_topics(fake_chunks)
    for t in topics:
        print(f"Topic: {t['name']}")
        print(f"  Summary: {t['summary']}")
        print()

asyncio.run(test())
