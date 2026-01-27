from enum import Enum

from fastapi import APIRouter, Depends, Request

from hippobox.core.settings import SETTINGS
from hippobox.errors.knowledge import KnowledgeException
from hippobox.errors.service import exceptions_to_http
from hippobox.models.knowledge import KnowledgeForm, KnowledgeResponse, KnowledgeUpdate
from hippobox.models.user import UserResponse
from hippobox.services.knowledge import KnowledgeService, get_knowledge_service
from hippobox.utils.auth import get_current_user

router = APIRouter()


class OperationID(str, Enum):
    search_knowledge = "search_knowledge"
    create_knowledge = "create_knowledge"
    get_knowledge_list = "get_knowledge_list"
    get_knowledge_by_title = "get_knowledge_by_title"
    get_knowledge_by_topic = "get_knowledge_by_topic"
    get_knowledge_by_tag = "get_knowledge_by_tag"
    update_knowledge = "update_knowledge"
    delete_knowledge = "delete_knowledge"


# -----------------------------
# Search
# -----------------------------
@router.get(
    "/search",
    response_model=list[KnowledgeResponse],
    operation_id=OperationID.search_knowledge,
    include_in_schema=SETTINGS.VDB_ENABLED,
)
async def search_knowledge(
    query: str,
    topic: str | None = None,
    tag: str | None = None,
    limit: int = 1,
    current_user: UserResponse = Depends(get_current_user),
    service: KnowledgeService = Depends(get_knowledge_service),
):
    """
    Search stored knowledge entries.

    ### Args:

        query (str): Semantic search query.
        topic (str | None = None): Optional topic filter.
        tag (str | None = None): Optional tag filter.
        limit (int = 1): Number of search results to return.

    ### Returns:

        knowledge (KnowledgeResponse): The successfully retrieved knowledge object.

    This endpoint performs vector similarity search on Qdrant
    and returns ranked knowledge entries.
    """
    try:
        return await service.search(
            user_id=current_user.id,
            query=query,
            topic=topic,
            tag=tag,
            limit=limit,
        )
    except KnowledgeException as e:
        raise exceptions_to_http(e)


# -----------------------------
# Post
# -----------------------------
@router.post("/", response_model=KnowledgeResponse, operation_id=OperationID.create_knowledge)
async def create_knowledge(
    request: Request,
    form: KnowledgeForm,
    current_user: UserResponse = Depends(get_current_user),
    service: KnowledgeService = Depends(get_knowledge_service),
):
    """
    Create a new knowledge entry.

    The input should include:
    - topic: A category or domain of the knowledge
    - tags: Keyword list
    - title: Short title summarizing the content
    - content: The full text or note to be stored

    ### Returns:

        knowledge (KnowledgeResponse): The successfully created knowledge object.

    This endpoint stores the entry in SQL and generates an embedding
    which is then indexed into Qdrant for similarity search.
    """
    try:
        return await service.create_knowledge(current_user.id, form)
    except KnowledgeException as e:
        raise exceptions_to_http(e)


# -----------------------------
# Get: List All
# -----------------------------
@router.get("/list", response_model=list[KnowledgeResponse], operation_id=OperationID.get_knowledge_list)
async def get_knowledge_list(
    current_user: UserResponse = Depends(get_current_user),
    service: KnowledgeService = Depends(get_knowledge_service),
):
    """
    Retrieve all stored knowledge entries.

    ### Returns:

        List of all knowledge entries sorted by creation date.

    Useful for browsing or building UI item lists.
    """
    try:
        return await service.get_knowledge_list(current_user.id)
    except KnowledgeException as e:
        raise exceptions_to_http(e)


# -----------------------------
# Get: By ID
# -----------------------------
@router.get("/{knowledge_id}", response_model=KnowledgeResponse)
async def get_knowledge(
    knowledge_id: int,
    current_user: UserResponse = Depends(get_current_user),
    service: KnowledgeService = Depends(get_knowledge_service),
):
    """
    Retrieve a single knowledge entry by its numeric ID.

    ### Returns:

        knowledge retrieved by own id.

    This endpoint is used for:
    - Detailed page views
    - Fetching a specific note
    - MCP tool consumption by ID
    """
    try:
        return await service.get_knowledge(current_user.id, knowledge_id)
    except KnowledgeException as e:
        raise exceptions_to_http(e)


# -----------------------------
# Get: By Title
# -----------------------------
@router.get("/title/{title}", response_model=KnowledgeResponse, operation_id=OperationID.get_knowledge_by_title)
async def get_knowledge_by_title(
    title: str,
    current_user: UserResponse = Depends(get_current_user),
    service: KnowledgeService = Depends(get_knowledge_service),
):
    """
    Retrieve a knowledge entry by its exact title.

    Useful when:
    - Titles are unique identifiers
    - MCP invokes tool with natural language title
    """
    try:
        return await service.get_by_title(current_user.id, title)
    except KnowledgeException as e:
        raise exceptions_to_http(e)


# -----------------------------
# Get: By Topic
# -----------------------------
@router.get("/topic/{topic}", response_model=list[KnowledgeResponse], operation_id=OperationID.get_knowledge_by_topic)
async def get_by_topic(
    topic: str,
    current_user: UserResponse = Depends(get_current_user),
    service: KnowledgeService = Depends(get_knowledge_service),
):
    """
    Retrieve all knowledge entries under a specific topic.
    Topics group entries into categories.

    Examples:
    - 'docker'
    - 'fastapi'
    - 'database'
    """
    try:
        return await service.get_by_topic(current_user.id, topic)
    except KnowledgeException as e:
        raise exceptions_to_http(e)


# -----------------------------
# Get: By Tag
# -----------------------------
@router.get("/tag/{tag}", response_model=list[KnowledgeResponse], operation_id=OperationID.get_knowledge_by_tag)
async def get_by_tag(
    tag: str,
    current_user: UserResponse = Depends(get_current_user),
    service: KnowledgeService = Depends(get_knowledge_service),
):
    """
    Retrieve all knowledge entries associated with a given tag.
    Tags represent keyword-level grouping, separate from topics.

    Examples:
    - 'server'
    - 'llm'
    - 'react'
    """
    try:
        return await service.get_by_tag(current_user.id, tag)
    except KnowledgeException as e:
        raise exceptions_to_http(e)


# -----------------------------
# Update
# -----------------------------
@router.put("/{knowledge_id}", response_model=KnowledgeResponse, operation_id=OperationID.update_knowledge)
async def update_knowledge(
    knowledge_id: int,
    form: KnowledgeUpdate,
    current_user: UserResponse = Depends(get_current_user),
    service: KnowledgeService = Depends(get_knowledge_service),
):
    """
    Update an existing knowledge entry.

    Updatable fields:
    - title
    - content
    - topic
    - tags

    After updating SQL, the embedding is regenerated
    and re-indexed into Qdrant.
    """
    try:
        return await service.update_knowledge(current_user.id, knowledge_id, form)
    except KnowledgeException as e:
        raise exceptions_to_http(e)


# -----------------------------
# Delete
# -----------------------------
@router.delete("/{knowledge_id}", operation_id=OperationID.delete_knowledge)
async def delete_knowledge(
    knowledge_id: int,
    current_user: UserResponse = Depends(get_current_user),
    service: KnowledgeService = Depends(get_knowledge_service),
):
    """
    Delete a knowledge entry.

    Removes:
    - SQL row
    - Embedding vector from Qdrant index
    """
    try:
        await service.delete_knowledge(current_user.id, knowledge_id)
        return {"status": "success", "id": knowledge_id}
    except KnowledgeException as e:
        raise exceptions_to_http(e)
