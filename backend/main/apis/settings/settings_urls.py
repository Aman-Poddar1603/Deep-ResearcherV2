from typing import NoReturn

from fastapi import APIRouter, HTTPException, Response, status

from main.apis.models.settings import SettingsPatch, SettingsRecord
from main.src.settings import settings_orchestrator

router = APIRouter(prefix="/settings", tags=["settings"])

settings_view = settings_orchestrator.SettingsOrchestrator()


def _raise_settings_http_error(action: str, exc: Exception) -> NoReturn:
    if isinstance(exc, HTTPException):
        raise exc
    if isinstance(exc, ValueError):
        detail = str(exc) or f"Invalid request for {action.lower()}"
        status_code = (
            status.HTTP_409_CONFLICT
            if "already exists" in detail.lower()
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(status_code=status_code, detail=detail) from exc
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Failed to {action.lower()}",
    ) from exc


@router.get("/", response_model=SettingsRecord)
def get_settings() -> SettingsRecord:
    try:
        return settings_view.getSettings()
    except Exception as exc:
        _raise_settings_http_error("Fetch settings", exc)


@router.post("/", response_model=SettingsRecord, status_code=status.HTTP_201_CREATED)
def create_settings(payload: SettingsRecord) -> SettingsRecord:
    try:
        return settings_view.createSettings(payload)
    except Exception as exc:
        _raise_settings_http_error("Create settings", exc)


@router.put("/", response_model=SettingsRecord)
def replace_settings(payload: SettingsRecord) -> SettingsRecord:
    try:
        return settings_view.updateSettings(payload)
    except Exception as exc:
        _raise_settings_http_error("Replace settings", exc)


@router.patch("/", response_model=SettingsRecord)
def patch_settings(payload: SettingsPatch) -> SettingsRecord:
    try:
        return settings_view.patchSettings(payload)
    except Exception as exc:
        _raise_settings_http_error("Patch settings", exc)


@router.delete("/", status_code=status.HTTP_204_NO_CONTENT)
def delete_settings() -> Response:
    try:
        settings_view.deleteSettings()
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as exc:
        _raise_settings_http_error("Delete settings", exc)
