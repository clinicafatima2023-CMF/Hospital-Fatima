import sqlite3
import os
import re
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
from fastapi.responses import FileResponse

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "farmacia_hospital.db")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# [Aquí iría todo el código que ya teníamos de las funciones, 
# asegúrate de incluir la base de datos igual que antes]

@app.get("/")
def pagina_principal():
    return FileResponse(os.path.join(BASE_DIR, "index.html"))

# (Asegúrate de copiar el resto de tus funciones aquí abajo)

# Para que Render pueda ejecutar FastAPI:
application = app