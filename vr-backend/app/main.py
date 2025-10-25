from fastapi import FastAPI
from app.routers import images_router

# Crear la aplicación FastAPI con título descriptivo
app = FastAPI(title="VR Backend API")

# Registrar router de imágenes
app.include_router(images_router.router)

@app.get("/")
def root():
    """
    Endpoint raíz para verificar que la API está funcionando correctamente.
    """
    return {"message": "API VR Backend funcionando correctamente"}