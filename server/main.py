import os
import json
import re
import unicodedata

from fastapi import FastAPI, Query, File, UploadFile, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from PyPDF2 import PdfReader
import docx
import openpyxl
from fastapi.middleware.cors import CORSMiddleware

from database import SessionLocal, Documento, Usuario, get_db
from groq import Groq

app = FastAPI(title="Sardiñas na Nube Enterprise AI")

MODELO_RAPIDO = "llama-3.1-8b-instant"
MODELO_PRO = "llama-3.3-70b-versatile" 

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
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

def normalizar_texto(texto: str) -> str:
    if not texto: return ""
    texto = unicodedata.normalize("NFD", texto)
    return texto.encode("ascii", "ignore").decode("utf-8").lower()

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
    extension = file.filename.split(".")[-1].lower()

    try:
        if extension == "pdf":
            reader = PdfReader(ruta_guardado)
            texto_extraido = "\n".join([page.extract_text() or "" for page in reader.pages])
        elif extension in ["doc", "docx"]:
            doc = docx.Document(ruta_guardado)
            texto_extraido = "\n".join([p.text for p in doc.paragraphs])
        elif extension in ["xls", "xlsx"]:
            wb = openpyxl.load_workbook(ruta_guardado, data_only=True)
            for sheet in wb.worksheets:
                for row in sheet.iter_rows(values_only=True):
                    texto_extraido += " ".join([str(c) for c in row if c is not None]) + "\n"
    except Exception as e:
        print("Error extracción:", e)

    categoria_final = "General"
    if len(texto_extraido) > 100:
        longitud = len(texto_extraido)
        muestreo = f"{texto_extraido[:1200]}\n[...]\n{texto_extraido[longitud//2-500:longitud//2+500]}\n[...]\n{texto_extraido[-1200:]}"
        
        try:
            prompt_cat = f"Clasifica en una palabra (Finanzas, Legal, RRHH, Proyectos, Charlas): {muestreo}"
            res_cat = client_ai.chat.completions.create(
                messages=[{"role": "user", "content": prompt_cat}], 
                model=MODELO_RAPIDO
            )
            sugerencia = res_cat.choices[0].message.content.strip().title()
            if sugerencia in ["Finanzas", "Legal", "Rrhh", "Proyectos", "Charlas"]:
                categoria_final = "RRHH" if sugerencia == "Rrhh" else sugerencia
        except: pass

    metadatos = {"tamano_bytes": len(contenido), "extension": extension, "categoria": categoria_final}
    nuevo_doc = Documento(
        nombre_archivo=file.filename,
        nombre_normalizado=normalizar_texto(file.filename),
        ruta_archivo=ruta_guardado,
        contenido_texto=texto_extraido,
        contenido_normalizado=normalizar_texto(texto_extraido),
        metadatos=json.dumps(metadatos),
        user_id=usuario.id
    )
    db.add(nuevo_doc)
    db.commit()
    db.refresh(nuevo_doc)
    return {"mensaje": "OK", "id": nuevo_doc.id}

@app.put("/documentos/{doc_id}")
async def actualizar_documento(doc_id: int, payload: dict, db: Session = Depends(get_db)):
    doc = db.query(Documento).filter(Documento.id == doc_id).first()
    if not doc: raise HTTPException(status_code=404)
    
    if "nombre_archivo" in payload:
        doc.nombre_archivo = payload["nombre_archivo"]
        doc.nombre_normalizado = normalizar_texto(payload["nombre_archivo"])
    if "contenido_texto" in payload:
        doc.contenido_texto = payload["contenido_texto"]
        doc.contenido_normalizado = normalizar_texto(payload["contenido_texto"])
    if "categoria" in payload:
        m = json.loads(doc.metadatos)
        m["categoria"] = payload["categoria"]
        doc.metadatos = json.dumps(m)
        
    db.commit()
    return {"status": "success"}

@app.get("/documentos/")
def buscar_y_navegar(query: str = None, categoria: str = None, skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    consulta = db.query(Documento)
    if query:
        q_norm = normalizar_texto(query)
        consulta = consulta.filter((Documento.nombre_normalizado.like(f"%{q_norm}%")) | (Documento.contenido_normalizado.like(f"%{q_norm}%")))
    if categoria and categoria != "Todas":
        consulta = consulta.filter(Documento.metadatos.like(f'%"{categoria}"%'))

    total = consulta.count()
    resultados = consulta.offset(skip).limit(limit).all()
    final = []
    for doc in resultados:
        m = json.loads(doc.metadatos)
        frags = []
        if doc.contenido_texto and query:
            clean_n = normalizar_texto(doc.contenido_texto.replace("\n", " "))
            clean_o = doc.contenido_texto.replace("\n", " ")
            matches = list(re.finditer(re.escape(normalizar_texto(query)), clean_n))
            for match in matches:
                start, end = max(0, match.start() - 50), min(len(clean_o), match.end() + 50)
                frags.append(clean_o[start:end])

        final.append({
            "id": doc.id, "nombre_archivo": doc.nombre_archivo, "metadatos": m,
            "fragmentos": frags, "coincidencias": len(frags), "texto_completo": doc.contenido_texto
        })
    return {"total_encontrados": total, "pagina_actual": (skip // limit) + 1, "resultados": final}

@app.get("/documentos/{doc_id}/resumir")
async def resumir_documento(doc_id: int, db: Session = Depends(get_db)):
    doc = db.query(Documento).filter(Documento.id == doc_id).first()
    prompt = f"Resume este documento corporativo en 3 puntos clave con emojis:\n{doc.contenido_texto[:4500]}"
    try:
        res = client_ai.chat.completions.create(messages=[{"role": "user", "content": prompt}], model=MODELO_PRO)
        return {"resumen": res.choices[0].message.content}
    except Exception as e: return {"resumen": f"Error IA: {str(e)}"}

@app.delete("/documentos/{doc_id}")
async def eliminar_documento(doc_id: int, db: Session = Depends(get_db)):
    doc = db.query(Documento).filter(Documento.id == doc_id).first()
    if os.path.exists(doc.ruta_archivo): os.remove(doc.ruta_archivo)
    db.delete(doc)
    db.commit()
    return {"mensaje": "OK"}