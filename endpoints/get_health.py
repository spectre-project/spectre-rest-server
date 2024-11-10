# encoding: utf-8
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict

from pydantic import BaseModel
from sqlalchemy import select

from dbsession import async_session
from models.Transaction import Transaction
from server import app, spectred_client
from endpoints.get_virtual_chain_blue_score import current_blue_score_data


class SpectredResponse(BaseModel):
    spectredHost: str = ""
    serverVersion: str = "0.3.14"
    isUtxoIndexed: bool = True
    isSynced: bool = True
    p2pId: str = "1231312"


class HealthResponse(BaseModel):
    spectredServers: List[SpectredResponse]
    currentBlueScore: int = None
    dbCheck: Dict[str, str]  # report database status


@app.get("/info/health", response_model=HealthResponse, tags=["Spectre network info"])
async def health_state():
    """
    Checks health by verifying node sync status, the recency of the latest block in
    the database, and returns each node's status, version, and the current blue score.

    If the database check fails, `dbCheck` will show an "error" status and relevant
    message. If the latest block is older than 10 minutes, it will indicate an outdated
    status. Otherwise, the status is marked as "valid".
    """
    await spectred_client.initialize_all()

    spectreds = []

    # dbCheck status
    db_check_status = {"status": "valid", "message": "Database is up-to-date"}

    # check the recency of the latest transaction's block time in the database
    try:
        async with async_session() as s:
            last_block_time = (
                await s.execute(
                    select(Transaction.block_time)
                    .limit(1)
                    .order_by(Transaction.block_time.desc())
                )
            ).scalar()

        time_diff = datetime.now() - datetime.fromtimestamp(last_block_time / 1000)

        if time_diff > timedelta(minutes=10):
            db_check_status = {
                "status": "error",
                "message": "Block age older than 10 minutes",
            }
    except Exception:
        db_check_status = {"status": "error", "message": "Database unavailable"}

    for i, spectred_info in enumerate(spectred_client.spectreds):
        spectreds.append(
            {
                "isSynced": spectred_info.is_synced,
                "isUtxoIndexed": spectred_info.is_utxo_indexed,
                "p2pId": hashlib.sha256(spectred_info.p2p_id.encode()).hexdigest(),
                "spectredHost": f"SPECTRED_HOST_{i + 1}",
                "serverVersion": spectred_info.server_version,
            }
        )

    current_blue_score = current_blue_score_data.get("blue_score")

    return {
        "spectredServers": spectreds,
        "currentBlueScore": current_blue_score,
        "dbCheck": db_check_status,
    }
