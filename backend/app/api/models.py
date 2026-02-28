"""模型接口：提供可用模型列表，供前端切换。"""

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.model_service import get_available_chat_models, get_default_chat_model

router = APIRouter()


class ModelOption(BaseModel):
    """单个可选模型。"""

    model_id: str
    display_name: str
    provider: str
    model_name: str


class ModelListResponse(BaseModel):
    """模型列表响应。"""

    default_model_id: str
    models: list[ModelOption]


@router.get("/models", response_model=ModelListResponse)
def list_models() -> ModelListResponse:
    """返回可切换模型列表。"""

    available = get_available_chat_models()
    default_model = get_default_chat_model()
    return ModelListResponse(
        default_model_id=default_model.model_id,
        models=[
            ModelOption(
                model_id=item.model_id,
                display_name=item.display_name,
                provider=item.provider,
                model_name=item.model_name,
            )
            for item in available
        ],
    )

