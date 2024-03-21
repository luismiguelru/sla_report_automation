from connect.eaas.core.decorators import unauthorized
from fastapi.routing import APIRouter
from starlette.responses import JSONResponse

shared_router = APIRouter()

@shared_router.get('/healthcheck')
@unauthorized()
def healthcheck():

    return JSONResponse(status_code=200, content={"status": "OK", "version": "1.0.0"})