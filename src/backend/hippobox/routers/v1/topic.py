from typing import List

from fastapi import APIRouter, Body, Depends, Path

from hippobox.errors.service import exceptions_to_http
from hippobox.models.topic import TopicForm, TopicResponse, TopicUpdate
from hippobox.models.user import UserResponse
from hippobox.services.topic import TopicService, get_topic_service
from hippobox.utils.auth import get_current_user

router = APIRouter()


@router.get("", response_model=List[TopicResponse])
async def list_topics(
    current_user: UserResponse = Depends(get_current_user),
    service: TopicService = Depends(get_topic_service),
):
    """Retrieve all topics for the current user."""
    return await service.list_topics(current_user.id)


@router.post("", response_model=TopicResponse)
async def create_topic(
    form: TopicForm = Body(...),
    current_user: UserResponse = Depends(get_current_user),
    service: TopicService = Depends(get_topic_service),
):
    """Create a new topic."""
    try:
        return await service.create_topic(current_user.id, form.name)
    except Exception as e:
        raise exceptions_to_http(e)


@router.patch("/{topic_id}", response_model=TopicResponse)
async def update_topic(
    topic_id: int = Path(..., description="ID of the topic to update"),
    form: TopicUpdate = Body(...),
    current_user: UserResponse = Depends(get_current_user),
    service: TopicService = Depends(get_topic_service),
):
    """Update topic name."""
    try:
        return await service.update_topic(current_user.id, topic_id, form)
    except Exception as e:
        raise exceptions_to_http(e)


@router.delete("/{topic_id}")
async def delete_topic(
    topic_id: int = Path(..., description="ID of the topic to delete"),
    current_user: UserResponse = Depends(get_current_user),
    service: TopicService = Depends(get_topic_service),
):
    """Delete a topic. Knowledge entries are reassigned to the default topic."""
    try:
        await service.delete_topic(current_user.id, topic_id)
        return {"message": "Topic deleted successfully"}
    except Exception as e:
        raise exceptions_to_http(e)
