# encoding: utf-8
import hashlib
from datetime import datetime, timedelta
from typing import List

from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from dbsession import async_session
from models.Transaction import Transaction
from server import app, spectred_client


class SpectredResponse(BaseModel):
    spectredHost: str = ""
    serverVersion: str = "0.3.14"
    isUtxoIndexed: bool = True
    isSynced: bool = True
    p2pId: str = "1231312"


class HealthResponse(BaseModel):
    spectredServers: List[SpectredResponse]


@app.get("/info/health", response_model=HealthResponse, tags=["Spectre network info"])
async def health_state():
    """
    Checks health by verifying transaction recency and node sync status.
    Returns each node's status and version.
    """
    await spectred_client.initialize_all()

    spectreds = []

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
        raise HTTPException(status_code=500, detail="Transactions not up to date")

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

    return {"spectredServers": spectreds}
