# encoding: utf-8

from pydantic import BaseModel

from helper import get_spr_price
from server import app, spectred_client


class MarketCapResponse(BaseModel):
    marketcap: int


@app.get("/info/marketcap", response_model=MarketCapResponse, tags=["Spectre network info"])
async def get_marketcap(stringOnly: bool = False):
    """
    Get $SPR price and market cap. Price info is from coinpaprika.com
    """
    spr_price = await get_spr_price()
    resp = await spectred_client.request("getCoinSupplyRequest")
    mcap = round(float(resp["getCoinSupplyResponse"]["circulatingSompi"]) / 100000000 * spr_price)

    if not stringOnly:
        return {
            "marketcap": mcap
        }
    else:
        if mcap < 1000000000:
            return f"{round(mcap / 1000000, 1)}M"
        else:
            return f"{round(mcap / 1000000000, 1)}B"
