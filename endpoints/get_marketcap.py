# encoding: utf-8

from pydantic import BaseModel

from helper import get_spr_price
from server import app, spectred_client


class MarketCapResponse(BaseModel):
    marketcap: int = 12000132


@app.get(
    "/info/marketcap",
    response_model=MarketCapResponse | str,
    tags=["Spectre network info"],
)
async def get_marketcap(stringOnly: bool = False):
    """
    Get $SPR price and market cap. Price info is from coingecko.com
    """
    spr_price = await get_spr_price()
    resp = await spectred_client.request("getCoinSupplyRequest")
    mcap = round(
        float(resp["getCoinSupplyResponse"]["circulatingSompi"]) / 1e8 * spr_price
    )

    if not stringOnly:
        return {"marketcap": mcap}
    else:
        if mcap < 1e9:
            return f"{round(mcap / 1e6, 1)}M"
        else:
            return f"{round(mcap / 1e9, 1)}B"
