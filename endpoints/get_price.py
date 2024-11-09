# encoding: utf-8

from pydantic import BaseModel
from starlette.responses import PlainTextResponse

from helper import get_spr_price, get_spr_market_data
from server import app


class PriceResponse(BaseModel):
    price: float = 0.0314


@app.get(
    "/info/price", response_model=PriceResponse | str, tags=["Spectre network info"]
)
async def get_price(stringOnly: bool = False):
    """
    Returns the current price for Spectre in USD. Price info is from coingecko.com
    """
    if stringOnly:
        return PlainTextResponse(content=str(await get_spr_price()))

    return {"price": await get_spr_price()}


@app.get("/info/market-data", tags=["Spectre network info"], include_in_schema=False)
async def get_market_data():
    """
    Returns market data for Spectre.
    """
    return await get_spr_market_data()
