from fastapi import APIRouter, Form, HTTPException
from openai import OpenAI
import replicate
import os
import requests
import tempfile
import random
from dotenv import load_dotenv

router = APIRouter()
load_dotenv()

# Inicializar clientes
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generar_imagen_replicate(prompt: str, image_url: str):
    """
    Genera una nueva imagen usando Replicate (Flux Kontext Pro).
    """
    try:
        output = replicate.run(
            "black-forest-labs/flux-kontext-pro",
            input={
                "prompt": prompt,
                "input_image": image_url,
                "aspect_ratio": "match_input_image",
                "output_format": "jpg",
                "safety_tolerance": 2,
                "prompt_upsampling": False
            }
        )
        
        # Extraer URL del output de Replicate
        if isinstance(output, list):
            first_output = output[0]
            if hasattr(first_output, 'url'):
                generated_url = first_output.url
            else:
                generated_url = str(first_output)
        else:
            if hasattr(output, 'url'):
                generated_url = output.url
            else:
                generated_url = str(output)
        
        return generated_url
        
    except Exception as e:
        raise ValueError(f"Error con Replicate: {str(e)}")

def generar_imagen_openai(prompt: str, image_url: str, style_description_model: str):
    """
    Genera una nueva imagen usando OpenAI (DALL·E 3).
    Primero analiza la imagen con GPT-4o y luego genera una nueva imagen.
    """
    try:
        # Paso 1: Analizar la imagen con GPT-4o para obtener descripción del estilo
        analysis_response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "user", "content": [
                    {"type": "text", "text": "Describe que es lo que hay en la imagen, como una referencia para despues ser usada como refenrecia para generar una nueva imagen con un estilo distinto::"},
                    {"type": "image_url", "image_url": {"url": image_url}}
                ]}
            ]
        )
        print(analysis_response)
        # Obtener la descripción del estilo
        style_description = analysis_response.choices[0].message.content
        
        # Paso 2: Generar imagen con DALL-E 3 usando la descripción del estilo + prompt
        enhanced_prompt = f"Basado en la descripcion de la imagen: {style_description}. {prompt}"
        
        response = openai_client.images.generate(
            model="dall-e-3",
            prompt=enhanced_prompt,
            size="1024x1024",
            style=style_description_model,
        )

        generated_url = response.data[0].url
        return generated_url
        
    except Exception as e:
        raise ValueError(f"Error con OpenAI: {str(e)}")

@router.post("/generar_imagen_ia")
async def generar_imagen(
    prompt: str = Form(...), 
    image_url: str = Form(...),
    model: str = Form(...)  # "replicate" o "openai"
):
    """
    Genera una nueva imagen usando IA.
    Parámetros:
    - prompt: Descripción de la imagen a generar
    - image_url: URL de la imagen base
    - model: "replicate" o "openai"
    """
    try:
        if model.lower() == "replicate":
            generated_url = generar_imagen_replicate(prompt, image_url)
            model_name = "Replicate (Flux Kontext Pro)"
        elif model.lower() == "openai":
            generated_url = generar_imagen_openai(prompt, image_url)
            model_name = "OpenAI (DALL-E 2)"
        else:
            raise HTTPException(
                status_code=400, 
                detail="Model debe ser 'replicate' o 'openai'"
            )

        return {
            "message": f"Imagen generada correctamente usando {model_name}.",
            "prompt": prompt,
            "input_image_url": image_url,
            "generated_image_url": generated_url,
            "model_used": model_name
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al generar la imagen: {str(e)}")
