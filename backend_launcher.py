import uvicorn

from app.main1 import app
from app.database.database import init_database


if __name__ == "__main__":

    init_database()

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        reload=False
    )