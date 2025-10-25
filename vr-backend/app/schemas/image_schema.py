from pydantic import BaseModel, Field

class ImagenData(BaseModel):
    id: str
    name: str
    description: str
    initialImageUrl: str
    generatedImageUrl: str
    createdAt: datetime.datetime

class ImageBase(BaseModel):
    """
    Modelo base para validar datos de imágenes.
    Define la estructura básica que deben tener los datos de una imagen.
    """
    nombre_pieza: str = Field(..., description="Nombre de la pieza o imagen")
    descripcion: str = Field(..., description="Descripción breve de la imagen")
