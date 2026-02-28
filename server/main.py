import os
import json
import re
from fastapi import FastAPI, Query, File, UploadFile, Depends, HTTPException
from sqlalchemy.orm import Session
from PyPDF2 import PdfReader
import docx  
import openpyxl
from fastapi.middleware.cors import CORSMiddleware
from database import SessionLocal, Documento, Usuario, get_db
from groq import Groq 

app = FastAPI(title="Sardiñas na Nube AI API")

client_ai = Groq(api_key="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")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    
    try:
        if extension == "pdf":
            reader = PdfReader(ruta_guardado)
            for page in reader.pages:
                texto_extraido += (page.extract_text() or "") + "\n"
        elif extension in ["doc", "docx"]:
            doc = docx.Document(ruta_guardado)
            for para in doc.paragraphs:
                texto_extraido += para.text + "\n"
        elif extension in ["xls", "xlsx"]:
            wb = openpyxl.load_workbook(ruta_guardado, data_only=True)
            for sheet in wb.worksheets:
                for row in sheet.iter_rows(values_only=True):
                    texto_extraido += " ".join([str(c) for c in row if c is not None]) + "\n"
        elif extension in ["txt", "csv", "md"]:
            with open(ruta_guardado, "r", encoding="utf-8", errors="ignore") as f:
                texto_extraido = f.read()
    except Exception as e:
        print(f"Error extrayendo texto: {e}")

    metadatos = {
        "tamano_bytes": len(contenido),
        "extension": extension,
        "categoria": "General" 
    }

    texto_min = texto_extraido.lower()
    
    if texto_extraido.strip():
        try:
            prompt_cat = f"Clasifica este texto en UNA sola palabra de estas categorías (Finanzas, Legal, RRHH, Proyectos, Charlas, General): {texto_extraido[:800]}"
            res_cat = client_ai.chat.completions.create(
                messages=[{"role": "user", "content": prompt_cat}],
                model="llama3-8b-8192",
            )
            categoria_sugerida = res_cat.choices[0].message.content.strip().title()
            if categoria_sugerida in ["Finanzas", "Legal", "Rrhh", "Proyectos", "Charlas"]:
                metadatos["categoria"] = "RRHH" if categoria_sugerida == "Rrhh" else categoria_sugerida
        except Exception as e:
            if any(p in texto_min for p in ["factura", "presupuesto", "€"]): metadatos["categoria"] = "Finanzas"
            elif any(p in texto_min for p in ["contrato", "ley"]): metadatos["categoria"] = "Legal"
            elif any(p in texto_min for p in ["charla", "ponencia"]): metadatos["categoria"] = "Charlas"

    nuevo_doc = Documento(
        nombre_archivo=file.filename,
        ruta_archivo=ruta_guardado,
        contenido_texto=texto_extraido,
        metadatos=json.dumps(metadatos), 
        user_id=usuario.id
    )
    db.add(nuevo_doc)
    db.commit()
    db.refresh(nuevo_doc)
    return {"mensaje": "OK", "id": nuevo_doc.id}

@app.get("/documentos/{doc_id}/resumir")
async def resumir_documento(doc_id: int, db: Session = Depends(get_db)):
    doc = db.query(Documento).filter(Documento.id == doc_id).first()
    if not doc or not doc.contenido_texto:
        raise HTTPException(status_code=404, detail="Documento no encontrado o sin texto legible")

    try:
        prompt_res = f"Resume este documento en 3 puntos clave muy directos. Usa emojis corporativos. Sé breve: {doc.contenido_texto[:3500]}"
        
        completion = client_ai.chat.completions.create(
            messages=[{"role": "user", "content": prompt_res}],
            model="llama-3.1-8b-instant",
        )
        return {"resumen": completion.choices[0].message.content}
    except Exception as e:
        return {"resumen": f"⚠️ Error al conectar con el cerebro de IA: {str(e)}"}

@app.get("/documentos/")
def buscar_y_navegar(
    query: str = None, 
    categoria: str = None, 
    skip: int = Query(0), 
    limit: int = Query(10),
    db: Session = Depends(get_db)
):
    consulta = db.query(Documento)
    
    if query:
        termino = f"%{query}%"
        consulta = consulta.filter((Documento.nombre_archivo.like(termino)) | (Documento.contenido_texto.like(termino)))
    
    if categoria and categoria != "Todas":
        consulta = consulta.filter(Documento.metadatos.like(f'%"categoria": "{categoria}"%'))
        
    total = consulta.count()
    resultados = consulta.offset(skip).limit(limit).all()
    
    final = []
    for doc in resultados:
        m = json.loads(doc.metadatos)
        frags = []
        coincidencias = 0
        
        if doc.contenido_texto and query:
            clean = doc.contenido_texto.replace('\n', ' ')
            matches = list(re.finditer(query, clean, re.IGNORECASE))
            coincidencias = len(matches)
            for match in matches[:5]:
                start, end = max(0, match.start() - 45), min(len(clean), match.end() + 45)
                frags.append(clean[start:end])
        
        final.append({
            "id": doc.id,
            "nombre_archivo": doc.nombre_archivo,
            "metadatos": m, 
            "fragmentos": frags,
            "coincidencias": coincidencias 
        })
        
    return {
        "total_encontrados": total,
        "pagina_actual": (skip // limit) + 1,
        "resultados": final
    }