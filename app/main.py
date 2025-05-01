from fastapi import FastAPI

app = FastAPI()


@app.get("/")
async def read_root():
    return {"message": "Hello World"}

# Здесь позже можно добавить логику подключения к базе данных 