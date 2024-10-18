# encoding: utf-8

from pydantic import BaseModel

from server import app, spectred_client
from fastapi.responses import PlainTextResponse


class CoinSupplyResponse(BaseModel):
    circulatingSupply: str = "1000900697580640180"
    maxSupply: str = "2900000000000000000"


@app.get(
    "/info/coinsupply", response_model=CoinSupplyResponse, tags=["Spectre network info"]
)
async def get_coinsupply():
    """
    Get $SPR coin supply information
    """
    resp = await spectred_client.request("getCoinSupplyRequest")
    return {
        "circulatingSupply": resp["getCoinSupplyResponse"]["circulatingSompi"],
        "totalSupply": resp["getCoinSupplyResponse"]["circulatingSompi"],
        "maxSupply": resp["getCoinSupplyResponse"]["maxSompi"],
    }


@app.get(
    "/info/coinsupply/circulating",
    tags=["Spectre network info"],
    response_class=PlainTextResponse,
)
async def get_circulating_coins(in_billion: bool = False):
    """
    Get circulating amount of $SPR coin as numerical value
    """
    resp = await spectred_client.request("getCoinSupplyRequest")
    coins = str(float(resp["getCoinSupplyResponse"]["circulatingSompi"]) / 100000000)
    if in_billion:
        return str(round(float(coins) / 1000000000, 2))
    else:
        return coins


@app.get(
    "/info/coinsupply/total",
    tags=["Spectre network info"],
    response_class=PlainTextResponse,
)
async def get_total_coins():
    """
    Get total amount of $SPR coin as numerical value
    """
    resp = await spectred_client.request("getCoinSupplyRequest")
    return str(float(resp["getCoinSupplyResponse"]["circulatingSompi"]) / 100000000)


@app.get(
    "/info/coinsupply/max",
    tags=["Spectre network info"],
    response_class=PlainTextResponse,
)
async def get_max_coins():
    """
    Get maximum amount of $SPR coin as numerical value
    """
    resp = await spectred_client.request("getCoinSupplyRequest")
    return str(float(resp["getCoinSupplyResponse"]["maxSompi"]) / 100000000)
