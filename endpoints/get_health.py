# encoding: utf-8
import hashlib
from typing import List

from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from dbsession import async_session
from endpoints.get_virtual_chain_blue_score import current_blue_score_data
from models.Block import Block
from server import app, spectred_client


class SpectredResponse(BaseModel):
    spectredHost: str = ""
    serverVersion: str = "0.3.14"
    isUtxoIndexed: bool = True
    isSynced: bool = True
    p2pId: str = "1231312"
    blueScore: int = 101065625


class DBCheckStatus(BaseModel):
    isSynced: bool = True
    blueScore: int | None
    blueScoreDiff: int | None


class HealthResponse(BaseModel):
    spectredServers: List[SpectredResponse]
    database: DBCheckStatus


@app.get("/info/health", response_model=HealthResponse, tags=["Spectre network info"])
async def health_state():
    """
    Checks node and database health by comparing blue score and sync status.
    Returns health details or 503 if the database lags by 1,000+ blocks or all nodes are not synced.
    """
    current_blue_score_node = current_blue_score_data.get("blue_score")

    try:
        async with async_session() as s:
            last_blue_score_db = (
                await s.execute(
                    select(Block.blue_score).order_by(Block.blue_score.desc()).limit(1)
                )
            ).scalar()
        if last_blue_score_db is None or current_blue_score_node is None:
            db_check_status = DBCheckStatus(
                isSynced=False, blueScore=last_blue_score_db
            )
        else:
            blue_score_diff = abs(current_blue_score_node - last_blue_score_db)
            isSynced = blue_score_diff < 1000
            db_check_status = DBCheckStatus(
                isSynced=isSynced,
                blueScore=last_blue_score_db,
                blueScoreDiff=blue_score_diff,
            )
    except Exception:
        db_check_status = DBCheckStatus(isSynced=False)

    await spectred_client.initialize_all()

    spectreds = [
        {
            "spectredHost": f"SPECTRED_HOST_{i + 1}",
            "serverVersion": spectred.server_version,
            "isUtxoIndexed": spectred.is_utxo_indexed,
            "isSynced": spectred.is_synced,
            "p2pId": hashlib.sha256(spectred.p2p_id.encode()).hexdigest(),
            "blueScore": current_blue_score_node,
        }
        for i, spectred in enumerate(spectred_client.spectreds)
    ]
    result = {
        "spectredServers": spectreds,
        "database": db_check_status.dict(),
    }

    if not db_check_status.isSynced or not any(
        spectred["isSynced"] for spectred in spectreds
    ):
        raise HTTPException(status_code=503, detail=result)

    return result
