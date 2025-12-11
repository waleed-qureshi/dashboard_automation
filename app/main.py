from fastapi import FastAPI
from .api import router
from .db import init_db

app = FastAPI(title="AI ReportsTeam Performance")


@app.on_event('startup')
def startup_event():
    init_db()


app.include_router(router, prefix='/api')
