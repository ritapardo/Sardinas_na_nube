import os
import json
from fastapi import FastAPI, Query, File, UploadFile, Depends
from sqlalchemy.orm import Session
from PyPDF2 import PdfReader

from database import SessionLocal, Documento, Usuario, get_db

app = FastAPI(title="Gestor Documental API")

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.post("/importar/")
async def importar_documento(file: UploadFile = File(...), db: Session = Depends(get_db)):
    usuario = db.query(Usuario).first()
    if not usuario:
        usuario = Usuario(username="admin", email="admin@demo.com", password_hash="1234")
        db.add(usuario)
        db.commit()
        db.refresh(usuario)

    ruta_guardado = os.path.join(UPLOAD_DIR, file.filename)
    with open(ruta_guardado, "wb") as buffer:
        contenido = await file.read()
        buffer.write(contenido)
    
    texto_extraido = ""
    metadatos = {
        "tamano_bytes": len(contenido),
        "extension": file.filename.split(".")[-1]
    }
    
    try:
        reader = PdfReader(ruta_guardado)
        metadatos["num_paginas"] = len(reader.pages)
        
        if reader.metadata:
            metadatos["autor"] = reader.metadata.get("/Author", "Desconocido")
            
        for page in reader.pages:
            texto_extraido += page.extract_text() + "\n"
            
    except Exception as e:
        return {"error": f"Hubo un problema leyendo el PDF: {str(e)}"}

    nuevo_documento = Documento(
        nombre_archivo=file.filename,
        ruta_archivo=ruta_guardado,
        contenido_texto=texto_extraido,
        metadatos=json.dumps(metadatos), 
        user_id=usuario.id
    )
    
    db.add(nuevo_documento)
    db.commit()
    db.refresh(nuevo_documento)

    return {
        "mensaje": "Documento importado correctamente",
        "documento_id": nuevo_documento.id,
        "metadatos_extraidos": metadatos
    }

@app.get("/documentos/")
def buscar_y_navegar(
    query: str = None, 
    skip: int = Query(0, description="Paginación: cuántos saltar"), 
    limit: int = Query(10, description="Paginación: cuántos devolver"),
    db: Session = Depends(get_db)
):
    """
    Este endpoint hace la magia de buscar, paginar y devolver metadatos.
    """
    consulta = db.query(Documento)
    
    if query:
        termino_busqueda = f"%{query}%"
        consulta = consulta.filter(
            (Documento.nombre_archivo.like(termino_busqueda)) | 
            (Documento.contenido_texto.like(termino_busqueda))
        )
        
    total_resultados = consulta.count()
    
    resultados = consulta.offset(skip).limit(limit).all()
    
    documentos_formateados = []
    for doc in resultados:
        metadatos_dict = json.loads(doc.metadatos) if doc.metadatos else {}
        
        documentos_formateados.append({
            "id": doc.id,
            "nombre_archivo": doc.nombre_archivo,
            "metadatos": metadatos_dict, 
            "fragmento": doc.contenido_texto[:150] + "..." if doc.contenido_texto else "Sin contenido legible."
        })
        
    return {
        "total_encontrados": total_resultados,
        "pagina_actual": (skip // limit) + 1,
        "resultados": documentos_formateados
    }