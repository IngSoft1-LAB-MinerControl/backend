from fastapi import FastAPI

app = FastAPI(title="Agatha Christie's Death on the Cards")


@app.get("/")
def root():
    return {"msg": "Back levantado ahora falta agregarle todo"}
