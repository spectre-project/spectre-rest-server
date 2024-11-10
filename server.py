# encoding: utf-8
import logging
import os
from typing import Optional

import fastapi.logger
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi_utils.tasks import repeat_every
from pydantic import BaseModel
from starlette.requests import Request
from starlette.responses import JSONResponse

from dbsession import async_session
from helper.LimitUploadSize import LimitUploadSize
from spectred.SpectredMultiClient import SpectredMultiClient

fastapi.logger.logger.setLevel(logging.WARNING)
_logger = logging.getLogger(__name__)

app = FastAPI(
    title="Spectre REST-API server",
    description="This server is to communicate with Spectre Network via REST-API",
    version=os.getenv("VERSION", "tbd"),
    contact={"name": "Spectre Network"},
    license_info={"name": "MIT LICENSE"},
)

app.add_middleware(GZipMiddleware, minimum_size=500)
app.add_middleware(LimitUploadSize, max_upload_size=200_000)  # ~1MB

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SpectredStatus(BaseModel):
    is_online: bool = False
    server_version: Optional[str] = None
    is_utxo_indexed: Optional[bool] = None
    is_synced: Optional[bool] = None


class DatabaseStatus(BaseModel):
    is_online: bool = False


class PingResponse(BaseModel):
    spectred: SpectredStatus = SpectredStatus()
    database: DatabaseStatus = DatabaseStatus()


@app.get("/ping", include_in_schema=False, response_model=PingResponse)
async def ping_server():
    """
    Ping Pong
    """
    result = PingResponse()

    error = False
    try:
        info = await spectred_client.spectreds[0].request("getInfoRequest")
        result.spectred.is_online = True
        result.spectred.server_version = info["getInfoResponse"]["serverVersion"]
        result.spectred.is_utxo_indexed = info["getInfoResponse"]["isUtxoIndexed"]
        result.spectred.is_synced = info["getInfoResponse"]["isSynced"]
    except Exception as err:
        _logger.error("Spectred health check failed %s", err)
        error = True

    if os.getenv("SQL_URI") is not None:
        async with async_session() as session:
            try:
                await session.execute("SELECT 1")
                result.database.is_online = True
            except Exception as err:
                _logger.error("Database health check failed %s", err)
                error = True

    if error or not result.spectred.is_synced:
        return JSONResponse(status_code=500, content=result.dict())

    return result


spectred_hosts = []

for i in range(100):
    try:
        spectred_hosts.append(os.environ[f"SPECTRED_HOST_{i + 1}"].strip())
    except KeyError:
        break

if not spectred_hosts:
    raise Exception("Please set at least SPECTRED_HOST_1 environment variable.")

spectred_client = SpectredMultiClient(spectred_hosts)


@app.exception_handler(Exception)
async def unicorn_exception_handler(request: Request, exc: Exception):
    await spectred_client.initialize_all()
    return JSONResponse(
        status_code=500,
        content={
            "message": "Internal server error"
            # "traceback": f"{traceback.format_exception(exc)}"
        },
    )


@app.on_event("startup")
@repeat_every(seconds=60)
async def periodical_blockdag():
    await spectred_client.initialize_all()
