import os
import json
import re
import unicodedata
import base64

from fastapi import FastAPI, Query, File, UploadFile, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
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
MODELO_VISION = "llama-3.2-11b-vision-preview" # 🔥 Modelo para leer imágenes

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

def categorizar_con_ia(texto: str) -> str:
    if len(texto) < 10: return "General"
    try:
        prompt = f"Clasifica en una sola palabra (Finanzas, Legal, RRHH, Proyectos, Charlas): {texto[:2000]}"
        res = client_ai.chat.completions.create(messages=[{"role": "user", "content": prompt}], model=MODELO_RAPIDO)
        sugerencia = res.choices[0].message.content.strip().title()
        return sugerencia if sugerencia in ["Finanzas", "Legal", "RRHH", "Proyectos", "Charlas"] else "General"
    except: return "General"

@app.post("/importar/")
async def importar_documento(file: UploadFile = File(...), db: Session = Depends(get_db)):
    usuario = db.query(Usuario).first()
    ruta_guardado = os.path.join(UPLOAD_DIR, file.filename)
    contenido_binario = await file.read()
    with open(ruta_guardado, "wb") as buffer:
        buffer.write(contenido_binario)

    texto_extraido = ""
    extension = file.filename.split(".")[-1].lower()

    try:
        if extension == "pdf":
            reader = PdfReader(ruta_guardado)
            texto_extraido = "\n".join([p.extract_text() or "" for p in reader.pages])
        elif extension in ["doc", "docx"]:
            doc = docx.Document(ruta_guardado)
            texto_extraido = "\n".join([p.text for p in doc.paragraphs])
        elif extension in ["xls", "xlsx"]:
            wb = openpyxl.load_workbook(ruta_guardado, data_only=True)
            for sheet in wb.worksheets:
                texto_extraido += f"\n[Hoja: {sheet.title}]\n"
                for row in sheet.iter_rows(values_only=True):
                    # 🔥 Formato tabla para Excel
                    texto_extraido += " | ".join([str(c) if c is not None else "---" for c in row]) + "\n"
        elif extension in ["jpg", "jpeg", "png"]:
            # 🔥 IA de Visión para describir imágenes
            base64_image = base64.b64encode(contenido_binario).decode('utf-8')
            res_vision = client_ai.chat.completions.create(
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Describe detalladamente este documento o imagen corporativa. Extrae todo el texto que veas."},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]
                }],
                model=MODELO_VISION
            )
            texto_extraido = res_vision.choices[0].message.content
    except Exception as e:
        print(f"Error: {e}")

    categoria = categorizar_con_ia(texto_extraido)
    metadatos = {"tamano_bytes": len(contenido_binario), "extension": extension, "categoria": categoria}
    
    nuevo_doc = Documento(
        nombre_archivo=file.filename,
        nombre_normalizado=normalizar_texto(file.filename),
        ruta_archivo=ruta_guardado,
        contenido_texto=texto_extraido,
        contenido_normalizado=normalizar_texto(texto_extraido),
        metadatos=json.dumps(metadatos),
        user_id=usuario.id
    )
    db.add(nuevo_doc); db.commit(); db.refresh(nuevo_doc)
    return {"mensaje": "OK", "id": nuevo_doc.id}

@app.get("/documentos/{doc_id}/descargar")
async def descargar_documento(doc_id: int, db: Session = Depends(get_db)):
    doc = db.query(Documento).filter(Documento.id == doc_id).first()
    return FileResponse(path=doc.ruta_archivo, filename=doc.nombre_archivo)

@app.put("/documentos/{doc_id}")
async def actualizar_documento(doc_id: int, payload: dict, db: Session = Depends(get_db)):
    doc = db.query(Documento).filter(Documento.id == doc_id).first()
    if "contenido_texto" in payload:
        doc.contenido_texto = payload["contenido_texto"]
        doc.contenido_normalizado = normalizar_texto(payload["contenido_texto"])
        # 🔥 Recategorizar automáticamente tras editar
        m = json.loads(doc.metadatos)
        m["categoria"] = categorizar_con_ia(payload["contenido_texto"])
        doc.metadatos = json.dumps(m)
    if "nombre_archivo" in payload:
        doc.nombre_archivo = payload["nombre_archivo"]
        doc.nombre_normalizado = normalizar_texto(payload["nombre_archivo"])
    db.commit()
    return {"status": "success", "nueva_categoria": json.loads(doc.metadatos)["categoria"]}

@app.get("/documentos/")
def buscar_y_navegar(query: str = None, categoria: str = None, skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    consulta = db.query(Documento)
    if query:
        q = normalizar_texto(query)
        consulta = consulta.filter((Documento.nombre_normalizado.like(f"%{q}%")) | (Documento.contenido_normalizado.like(f"%{q}%")))
    if categoria and categoria != "Todas":
        consulta = consulta.filter(Documento.metadatos.like(f'%"{categoria}"%'))
    
    res = consulta.offset(skip).limit(limit).all()
    final = []
    for d in res:
        m = json.loads(d.metadatos)
        frags = []
        if query:
            clean_o = d.contenido_texto.replace("\n", " ")
            clean_n = normalizar_texto(clean_o)
            matches = list(re.finditer(re.escape(normalizar_texto(query)), clean_n))
            for match in matches[:5]:
                start, end = max(0, match.start() - 50), min(len(clean_o), match.end() + 50)
                frags.append(clean_o[start:end])
        final.append({"id": d.id, "nombre_archivo": d.nombre_archivo, "metadatos": m, "fragmentos": frags, "coincidencias": len(frags), "texto_completo": d.contenido_texto})
    return {"total_encontrados": consulta.count(), "resultados": final}

@app.get("/documentos/{doc_id}/resumir")
async def resumir_documento(doc_id: int, db: Session = Depends(get_db)):
    doc = db.query(Documento).filter(Documento.id == doc_id).first()
    prompt = f"Resume este documento corporativo en 3 puntos clave con emojis:\n{doc.contenido_texto[:4000]}"
    try:
        res = client_ai.chat.completions.create(messages=[{"role": "user", "content": prompt}], model=MODELO_PRO)
        return {"resumen": res.choices[0].message.content}
    except Exception as e: return {"resumen": f"Error IA: {str(e)}"}

@app.delete("/documentos/{doc_id}")
async def eliminar_documento(doc_id: int, db: Session = Depends(get_db)):
    doc = db.query(Documento).filter(Documento.id == doc_id).first()
    if os.path.exists(doc.ruta_archivo): os.remove(doc.ruta_archivo)
    db.delete(doc); db.commit()
    return {"mensaje": "OK"}