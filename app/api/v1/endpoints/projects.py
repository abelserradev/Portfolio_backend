from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse

from app.core.dependencies import get_project_service
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse
from app.services.project import ProjectService

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("/", response_model=List[ProjectResponse])
async def list_projects(
    service: Annotated[ProjectService, Depends(get_project_service)],
    skip: Annotated[int, Query(ge=0, le=50_000)] = 0,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
):
    return await service.get_projects(skip=skip, limit=limit)

@router.get(
    "/{project_id}",
    response_model=ProjectResponse,
    responses={404: {"description": "Proyecto no disponible"}}
)
async def get_project(
    project_id: int,
    service: Annotated[ProjectService, Depends(get_project_service)]
):
    project = await service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Proyecto no disponible")
    return project

@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_in: ProjectCreate,
    service: Annotated[ProjectService, Depends(get_project_service)]
):
    return await service.create_project(project_in.model_dump())

@router.put(
    "/{project_id}",
    response_model=ProjectResponse,
    responses={404: {"description": "Proyecto no encontrado"}}
)
async def update_project(
    project_id: int,
    project_in: ProjectUpdate,
    service: Annotated[ProjectService, Depends(get_project_service)]
):
    project = await service.update_project(project_id, project_in.model_dump(exclude_unset=True))
    if not project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    return project

@router.get("/{project_id}/visit", response_class=RedirectResponse, responses={404: {"description": "Proyecto no disponible"}})
async def visit_project(
    project_id: int,
    service: Annotated[ProjectService, Depends(get_project_service)]
):
    project = await service.increment_visits(project_id)
    if not project or not project.live_url:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado o sin URL en vivo")
    return RedirectResponse(project.live_url)

@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"description": "Proyecto no encontrado"}}
)
async def delete_project(
    project_id: int,
    service: Annotated[ProjectService, Depends(get_project_service)]
):
    deleted = await service.delete_project(project_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")