from typing import Any


def content_to_text(content: Any) -> str:
    """Convert LangChain message content blocks into plain text."""
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        text_parts = []
        for block in content:
            if isinstance(block, str):
                text_parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                text = block.get("text")
                if text:
                    text_parts.append(text)
        return "\n".join(text_parts)

    return str(content)
