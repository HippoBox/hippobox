from hippobox.models.knowledge import KnowledgeModel


def preprocess_content(knowledge: KnowledgeModel) -> str:
    """
    Build a markdown-formatted text for embedding,
    combining title, topic, tags, and original content.
    """

    title = knowledge.title
    topic = knowledge.topic
    tags = ", ".join(knowledge.tags)
    content = knowledge.content

    return f"""
# Title: {title}

## Topic: {topic}
## Tags: {tags}

{content}
""".strip()
