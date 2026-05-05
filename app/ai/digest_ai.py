from typing import List, Dict, Any, Tuple
from app.ai.llm_router import call_llm_simple


# ─── System prompt for digest generation ─────────────────────────────────────

DIGEST_SYSTEM_PROMPT = """You are PenGo, an intelligent assistant for the
Egloo second brain app. You help knowledge workers stay on top of their
information by generating clear, concise, actionable daily summaries.

Rules:
- Be concise and direct — busy professionals have no time for fluff
- Always ground your output in the provided content
- Never invent information not present in the input
- Format output as clean JSON when asked — no markdown, no code fences
- Extract genuine action items — not vague suggestions
- Name topics clearly so the user instantly knows what they are about"""


# ─── Step A: Cluster chunks into topics ──────────────────────────────────────

async def cluster_into_topics(
    chunks: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Ask the LLM to group chunks into 3-7 distinct topic clusters.

    Returns list of topic dicts:
    [
        {
            "name": "Project Alpha Launch",
            "summary": "Team discussed delaying launch to May 10...",
            "chunk_indices": [0, 2, 5, 7],
            "source_types": ["gmail", "slack"],
            "item_count": 4
        },
        ...
    ]
    """
    if not chunks:
        return []

    # Build a compact representation of chunks for the prompt
    chunk_summaries = []
    for i, chunk in enumerate(chunks[:100]):  # Cap at 100 for prompt size
        meta = chunk.get("chunk_metadata", {}) or {}
        source = meta.get("source_type", "unknown")
        subject = meta.get("subject", "")
        sender = meta.get("sender", "")
        preview = chunk["content"][:150].replace("\n", " ")

        line = f"[{i}] {source.upper()}"
        if sender:
            line += f" from {sender}"
        if subject:
            line += f" — {subject}"
        line += f": {preview}"
        chunk_summaries.append(line)

    chunks_text = "\n".join(chunk_summaries)

    prompt = f"""Below are {len(chunk_summaries)} items from a person's
emails, Slack messages, and documents from the last 24 hours.

{chunks_text}

Group these items into 3 to 7 distinct topics.
For each topic provide a clear name, a 1-2 sentence summary,
the indices of chunks that belong to it, and which source types
are involved.

Respond with ONLY valid JSON. No explanation. No markdown. No code fences.
Format exactly like this:
{{
  "topics": [
    {{
      "name": "Topic name here",
      "summary": "1-2 sentence summary of what happened on this topic",
      "chunk_indices": [0, 3, 7],
      "source_types": ["gmail", "slack"],
      "item_count": 3
    }}
  ]
}}"""

    try:
        response, model = await call_llm_simple(
            prompt=prompt,
            system=DIGEST_SYSTEM_PROMPT,
        )

        # Clean response — strip any accidental markdown
        cleaned = response.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            cleaned = "\n".join(
                l for l in lines
                if not l.startswith("```")
            )

        import json
        data = json.loads(cleaned)
        topics = data.get("topics", [])
        print(f"[INFO] Clustered into {len(topics)} topics using {model}")
        return topics

    except Exception as e:
        print(f"[WARNING] Topic clustering failed: {e}")
        # Fallback: single topic with everything
        return [
            {
                "name": "Today's Activity",
                "summary": f"Activity from {len(chunks)} items across your sources.",
                "chunk_indices": list(range(min(len(chunks), 100))),
                "source_types": list({
                    (c.get("chunk_metadata") or {}).get("source_type", "unknown")
                    for c in chunks
                }),
                "item_count": len(chunks),
            }
        ]


# ─── Step B: Extract action items ────────────────────────────────────────────

async def extract_action_items(
    chunks: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Ask the LLM to find tasks, requests, and deadlines.

    Returns list of action item dicts:
    [
        {
            "task": "Reply to Rohit about launch date",
            "source_type": "gmail",
            "sender": "rohit@company.com",
            "urgency": "high",
            "due_hint": "today"
        },
        ...
    ]
    """
    if not chunks:
        return []

    # Build text for action item extraction
    content_lines = []
    for i, chunk in enumerate(chunks[:80]):
        meta = chunk.get("chunk_metadata", {}) or {}
        source = meta.get("source_type", "unknown")
        sender = meta.get("sender", "")
        preview = chunk["content"][:200].replace("\n", " ")
        line = f"[{source.upper()}]"
        if sender:
            line += f" {sender}:"
        line += f" {preview}"
        content_lines.append(line)

    content_text = "\n".join(content_lines)

    prompt = f"""Review these messages and documents from the last 24 hours:

{content_text}

Extract all action items — things the user needs to do, reply to,
review, or decide on. Include tasks explicitly assigned to the user,
requests waiting for a response, and upcoming deadlines mentioned.

Respond with ONLY valid JSON. No explanation. No markdown. No code fences.
Format exactly like this:
{{
  "action_items": [
    {{
      "task": "Clear description of what needs to be done",
      "source_type": "gmail",
      "sender": "person who sent it or empty string",
      "urgency": "high or medium or low",
      "due_hint": "today or this week or no deadline or specific date"
    }}
  ]
}}

If no action items found, return {{"action_items": []}}"""

    try:
        response, model = await call_llm_simple(
            prompt=prompt,
            system=DIGEST_SYSTEM_PROMPT,
        )

        cleaned = response.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            cleaned = "\n".join(
                l for l in lines
                if not l.startswith("```")
            )

        import json
        data = json.loads(cleaned)
        items = data.get("action_items", [])
        print(f"[OK] Extracted {len(items)} action items using {model}")
        return items

    except Exception as e:
        print(f"[WARNING] Action item extraction failed: {e}")
        return []


# ─── Step C: Generate full narrative summary ─────────────────────────────────

async def generate_summary(
    topics: List[Dict[str, Any]],
    action_items: List[Dict[str, Any]],
    chunk_count: int,
    source_types: List[str],
) -> str:
    """
    Generate a concise executive summary paragraph for the digest.
    2-4 sentences. The user reads this first.
    """
    if not topics:
        return (
            "No significant activity found in the last 24 hours. "
            "PenGo has nothing to report. 🐧"
        )

    topics_text = "\n".join(
        f"- {t['name']}: {t['summary']}" for t in topics
    )
    actions_text = (
        "\n".join(f"- {a['task']}" for a in action_items[:5])
        if action_items
        else "None"
    )
    sources_str = ", ".join(set(source_types))

    prompt = f"""Write a 2-4 sentence executive summary for a knowledge worker's
daily digest. Be direct and useful.

Topics covered today:
{topics_text}

Key action items:
{actions_text}

Total items processed: {chunk_count}
Sources: {sources_str}

Write the summary now. Plain text only. No bullet points. No headers."""

    try:
        summary, model = await call_llm_simple(
            prompt=prompt,
            system=DIGEST_SYSTEM_PROMPT,
        )
        print(f"[OK] Summary generated using {model}")
        return summary.strip()
    except Exception as e:
        print(f"[WARNING] Summary generation failed: {e}")
        topic_names = ", ".join(t["name"] for t in topics[:3])
        return (
            f"Today PenGo found activity across {len(topics)} topics: "
            f"{topic_names}. "
            f"There are {len(action_items)} action items requiring attention."
        )
