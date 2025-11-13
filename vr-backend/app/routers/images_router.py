from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from datetime import datetime, timezone
import uuid
import firebase_admin
from firebase_admin import credentials, firestore, storage
from dotenv import load_dotenv
import tempfile 
import replicate
import os

# Inicializar Firebase
cred = credentials.Certificate("/etc/secrets/serviceAccountKey.json")
firebase_admin.initialize_app(cred, {
    'storageBucket': 'vr-backend-24b89.firebasestorage.app'
})

# Router para manejar todas las operaciones relacionadas con imágenes
router = APIRouter(prefix="/imagenes", tags=["Imágenes"])


db = firestore.client()
bucket = storage.bucket()

load_dotenv()

# POST /imagenes/
@router.post("/")
async def subir_imagen(
    nombre_pieza: str = Form(...),
    descripcion: str = Form(...),
    imagen: UploadFile = File(...)
):
    """
    Endpoint para subir una nueva imagen al sistema.
    Recibe el nombre de la pieza, descripción y el archivo de imagen.
    """

    file_data = await imagen.read()

    unique_filename = f"images/{uuid.uuid4()}_{imagen.filename}"

    blob = bucket.blob(unique_filename)
    blob.upload_from_string(file_data, content_type=imagen.content_type)

    blob.make_public()

    image_url = blob.public_url

    mock_generated_url = "https://picsum.photos/601"
    # Construir registro en Firestore
    doc = {
        "nombre": nombre_pieza,
        "description": descripcion,
        "initialImageUrl": image_url,
        "generatedImageUrl": mock_generated_url,  # luego se actualizará cuando generes la versión IA
        "createdAt": datetime.now(timezone.utc).isoformat()
    }

    db.collection("galeria").add(doc)

    return {"message": "Registro creado correctamente", "data": doc}

# GET /imagenes/
@router.get("/")
async def listar_imagenes():
    """
    Endpoint para obtener la lista de todas las imágenes disponibles.
    Retorna un listado completo de imágenes en el sistema.
    """

    try:
        # Leer todos los documentos de la colección "images"
        docs = db.collection("galeria").stream()

        # Convertir cada documento en un diccionario
        imagenes = []
        for doc in docs:
            data = doc.to_dict()
            data["id"] = doc.id  # opcional, para identificar el documento
            imagenes.append(data)

        return {
            "message": "Listado de imágenes obtenido correctamente.",
            "total": len(imagenes),
            "data": imagenes
        }

    except Exception as e:
        return {"error": f"Ocurrió un error al obtener las imágenes: {str(e)}"}

# GET /imagenes/{image_id}
@router.get("/{image_id}")
async def obtener_imagen(image_id: str):
    """
    Endpoint para obtener los detalles de una imagen específica.
    Busca una imagen por su ID único y retorna su información.
    """
   
    try:
        # Buscar documento por ID
        doc_ref = db.collection("galeria").document(image_id)
        doc = doc_ref.get()

        # Verificar si existe
        if not doc.exists:
            raise HTTPException(status_code=404, detail=f"La imagen con ID '{imagen_id}' no existe.")

        # Convertir a diccionario y añadir el ID
        data = doc.to_dict()
        data["id"] = doc.id

        return {
            "message": "Imagen encontrada correctamente.",
            "data": data
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener la imagen: {str(e)}")

# PUT /imagenes/{image_id}
@router.put("/{image_id}")
async def actualizar_imagen(
    image_id: str,
    nombre_pieza: str = Form(...),
    descripcion: str = Form(...)
):
    """
    Endpoint para actualizar los metadatos de una imagen existente.
    Permite modificar el nombre y descripción de una imagen específica.
    """
    try:
        # Referencia al documento
        doc_ref = db.collection("galeria").document(image_id)
        doc = doc_ref.get()

        # Verificar si existe
        if not doc.exists:
            raise HTTPException(status_code=404, detail=f"La imagen con ID '{imagen_id}' no existe.")

        # Datos a actualizar
        data_update = {
            "nombre": nombre_pieza,
            "description": descripcion,
            "updatedAt": datetime.now(timezone.utc).isoformat()
        }

        # Actualizar en Firestore
        doc_ref.update(data_update)

        return {
            "message": "Imagen actualizada correctamente.",
            "updated_fields": data_update
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al actualizar la imagen: {str(e)}")

# DELETE /imagenes/{image_id}
@router.delete("/{image_id}")
async def eliminar_imagen(image_id: str):
    """
    Endpoint para eliminar una imagen del sistema.
    Remueve permanentemente una imagen usando su ID único.
    """
    try:
        # Referencia al documento
        doc_ref = db.collection("galeria").document(image_id)
        doc = doc_ref.get()

        # Verificar si el documento existe
        if not doc.exists:
            raise HTTPException(status_code=404, detail=f"La imagen con ID '{imagen_id}' no existe.")

        # Eliminar documento de Firestore
        doc_ref.delete()

        return {
            "message": "Imagen eliminada correctamente.",
            "id": image_id
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al eliminar la imagen: {str(e)}")

# POST /imagenes/generar_imagen_ia
@router.post("/generar_imagen_ia")
async def generar_imagen(
    prompt: str = Form(...), 
    imagen_id: str = Form(...),
    model: str = Form(...),  # "replicate" o "openai"
    style_description: str = Form(...)
):
    """
    Endpoint para generar una nueva imagen usando inteligencia artificial.
    Combina un prompt de texto con una imagen base para crear una nueva imagen.
    Parámetros:
    - prompt: Descripción de la imagen a generar
    - imagen_id: ID del registro en Firestore
    - model: "replicate" o "openai"
    """
    try:
        # Buscar el registro por ID
        doc_ref = db.collection("galeria").document(imagen_id)
        doc = doc_ref.get()
        
        # Verificar si existe
        if not doc.exists:
            raise HTTPException(status_code=404, detail=f"La imagen con ID '{imagen_id}' no existe.")
        
        # Obtener los datos del documento
        data = doc.to_dict()
        initial_image_url = data.get("initialImageUrl")
        
        if not initial_image_url:
            raise HTTPException(status_code=400, detail="La imagen no tiene una URL inicial válida.")
        
        # Importar las funciones del modelo
        from app.model.model import generar_imagen_replicate, generar_imagen_openai
        
        # Ejecutar el modelo seleccionado
        if model.lower() == "replicate":
            generated_image_url = generar_imagen_replicate(prompt, initial_image_url)
            model_name = "Replicate (Flux Kontext Pro)"
        elif model.lower() == "openai":
            generated_image_url = generar_imagen_openai(prompt, initial_image_url, style_description)
            model_name = "OpenAI (GPT-4o + DALL-E 3)"
        else:
            raise HTTPException(
                status_code=400, 
                detail="Model debe ser 'replicate' o 'openai'"
            )
        
        # Actualizar el registro en Firestore con la nueva URL generada
        doc_ref.update({
            "generatedImageUrl": generated_image_url,
            "updatedAt": datetime.now(timezone.utc).isoformat()
        })
        
        return {
            "message": f"Imagen generada correctamente usando {model_name}.",
            "imagen_id": imagen_id,
            "prompt": prompt,
            "generated_image_url": generated_image_url,
            "model_used": model_name
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al generar la imagen: {str(e)}")