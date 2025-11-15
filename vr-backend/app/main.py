from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import images_router

# Crear la aplicación FastAPI con título descriptivo
app = FastAPI(title="VR Backend API")

# Agregar middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrar router de imágenes
app.include_router(images_router.router)

@app.get("/")
def root():
    """
    Endpoint raíz para verificar que la API está funcionando correctamente.
    """
    return {"message": "API VR Backend funcionando correctamente"}