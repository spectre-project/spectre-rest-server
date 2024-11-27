# encoding: utf-8
import json

from pydantic import BaseModel
from sqlalchemy import select

from dbsession import async_session
from endpoints import sql_db_only
from helper import KeyValueStore
from models.Block import Block
from server import app, spectred_client

MAXHASH_CACHE = (0, 0)


class BlockHeader(BaseModel):
    hash: str = "e6641454e16cff4f232b899564eeaa6e480b66069d87bee6a2b2476e63fcd887"
    timestamp: str = "1656450648874"
    difficulty: float = 1212312312
    daaScore: int = 19984482
    blueScore: int = 18483232


class HashrateResponse(BaseModel):
    hashrate: float = 12000132


class MaxHashrateResponse(BaseModel):
    hashrate: float = 12000132
    blockheader: BlockHeader


@app.get(
    "/info/hashrate",
    response_model=HashrateResponse | str,
    tags=["Spectre network info"],
)
async def get_hashrate(stringOnly: bool = False):
    """
    Returns the current hashrate for Spectre network in TH/s.
    """

    resp = await spectred_client.request("getBlockDagInfoRequest")
    hashrate = resp["getBlockDagInfoResponse"]["difficulty"] * 2
    hashrate_in_th = hashrate / 1e12

    if not stringOnly:
        return {"hashrate": hashrate_in_th}

    else:
        return f"{hashrate_in_th:.01f}"


@app.get(
    "/info/hashrate/max",
    response_model=MaxHashrateResponse,
    tags=["Spectre network info"],
)
@sql_db_only
async def get_max_hashrate():
    """
    Tracks the maximum hashrate observed incrementally by using the highest difficulty block since the
    last recorded bluescore, effectively updating an "all-time high" whenever a new max is found.
    """
    maxhash_last_value = json.loads(
        (await KeyValueStore.get("maxhash_last_value")) or "{}"
    )
    maxhash_last_bluescore = int(
        (await KeyValueStore.get("maxhash_last_bluescore")) or 0
    )
    print(f"Start at {maxhash_last_bluescore}")

    async with async_session() as s:
        block = (
            await s.execute(
                select(Block)
                .filter(Block.blue_score > maxhash_last_bluescore)
                .order_by(Block.difficulty.desc())
                .limit(1)
            )
        ).scalar()

    hashrate_new = block.difficulty * 2
    hashrate_old = maxhash_last_value.get("blockheader", {}).get("difficulty", 0) * 2

    await KeyValueStore.set("maxhash_last_bluescore", str(block.blue_score))

    if hashrate_new > hashrate_old:
        response = {
            "hashrate": hashrate_new / 1e12,
            "blockheader": {
                "hash": block.hash,
                "timestamp": block.timestamp.isoformat(),
                "difficulty": block.difficulty,
                "daaScore": block.daa_score,
                "blueScore": block.blue_score,
            },
        }
        await KeyValueStore.set("maxhash_last_value", json.dumps(response))
        return response

    return maxhash_last_value
