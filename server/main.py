import os
import json
from fastapi import FastAPI, Query, File, UploadFile, Depends
from sqlalchemy.orm import Session
from PyPDF2 import PdfReader
import docx  
import openpyxl  

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
    nombre_partes = file.filename.split(".")
    extension = nombre_partes[-1].lower() if len(nombre_partes) > 1 else "sin_extension"
    
    metadatos = {
        "tamano_bytes": len(contenido),
        "extension": extension
    }
    
    try:
        if extension == "pdf":
            reader = PdfReader(ruta_guardado)
            metadatos["num_paginas"] = len(reader.pages)
            if reader.metadata:
                metadatos["autor"] = reader.metadata.get("/Author", "Desconocido")
            for page in reader.pages:
                texto_extraido += page.extract_text() + "\n"

        elif extension in ["doc", "docx"]:
            doc = docx.Document(ruta_guardado)
            metadatos["autor"] = doc.core_properties.author or "Desconocido"
            metadatos["fecha_creacion"] = str(doc.core_properties.created)
            for para in doc.paragraphs:
                texto_extraido += para.text + "\n"

        elif extension in ["xls", "xlsx"]:
            wb = openpyxl.load_workbook(ruta_guardado, data_only=True)
            metadatos["hojas"] = wb.sheetnames
            metadatos["autor"] = wb.properties.creator or "Desconocido"
            for sheet in wb.worksheets:
                for row in sheet.iter_rows(values_only=True):
                    fila_texto = " ".join([str(cell) for cell in row if cell is not None])
                    if fila_texto:
                        texto_extraido += fila_texto + "\n"
                        
        elif extension in ["txt", "csv", "md", "json", "html", "py"]:
            with open(ruta_guardado, "r", encoding="utf-8", errors="ignore") as f:
                texto_extraido = f.read()
                
        else:
            metadatos["nota"] = "Archivo guardado correctamente. Formato no procesable para leer texto interno."

    except Exception as e:
        
        metadatos["error_extraccion"] = f"No se pudo extraer texto: {str(e)}"

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
        "mensaje": "Documento procesado e importado",
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