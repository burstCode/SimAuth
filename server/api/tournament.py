from fastapi import APIRouter
from config import AcRemoteConfig, save_tournament_config, config

router = APIRouter()


@router.get("/tournament")
def get_tournament() -> AcRemoteConfig:
    return config.ac_remote


@router.patch("/tournament")
def update_tournament(rc: AcRemoteConfig) -> AcRemoteConfig:
    save_tournament_config(rc)
    return config.ac_remote
