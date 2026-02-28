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

# 🔥 MODELOS
MODELO_RAPIDO = "llama-3.1-8b-instant"
MODELO_PRO = "llama-3.3-70b-versatile" 
MODELO_VISION = "llama-3.2-11b-vision-preview"

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
    if not texto or len(texto) < 10: return "General"
    try:
        prompt = f"Categoriza este documento en una sola palabra (Finanzas, Legal, RRHH, Proyectos, Charlas). Texto: {texto[:1500]}"
        res = client_ai.chat.completions.create(messages=[{"role": "user", "content": prompt}], model=MODELO_RAPIDO)
        cat = res.choices[0].message.content.strip().title().replace(".", "")
        return cat if cat in ["Finanzas", "Legal", "RRHH", "Proyectos", "Charlas"] else "General"
    except: return "General"

@app.post("/importar/")
async def importar_documento(file: UploadFile = File(...), db: Session = Depends(get_db)):
    usuario = db.query(Usuario).first()
    if not usuario:
        usuario = Usuario(username="admin", email="admin@demo.com", password_hash="1234")
        db.add(usuario); db.commit(); db.refresh(usuario)

    ruta_guardado = os.path.join(UPLOAD_DIR, file.filename)
    contenido_binario = await file.read()
    with open(ruta_guardado, "wb") as buffer:
        buffer.write(contenido_binario)

    texto_extraido = ""
    excel_grid = [] # Garantizamos que sea una lista
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
                filas = []
                texto_extraido += f"\n--- HOJA: {sheet.title} ---\n"
                for row in sheet.iter_rows(values_only=True):
                    fila_str = [str(c) if c is not None else " " for c in row]
                    filas.append(fila_str)
                    texto_extraido += " | ".join(fila_str) + "\n"
                # Añadimos estructura segura
                excel_grid.append({"hoja": sheet.title, "filas": filas})
                
        elif extension in ["jpg", "jpeg", "png"]:
            b64_img = base64.b64encode(contenido_binario).decode('utf-8')
            res_v = client_ai.chat.completions.create(
                messages=[{"role": "user", "content": [{"type": "text", "text": "Extrae el texto de esta imagen."}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}}]}],
                model=MODELO_VISION
            )
            texto_extraido = res_v.choices[0].message.content
            
    except Exception as e:
        texto_extraido = f"⚠️ ERROR AL PROCESAR: {e}"

    categoria = categorizar_con_ia(texto_extraido)
    metadatos = {
        "extension": extension, 
        "categoria": categoria,
        "excel_grid": excel_grid 
    }
    
    nuevo_doc = Documento(
        nombre_archivo=file.filename,
        nombre_normalizado=normalizar_texto(file.filename),
        ruta_archivo=ruta_guardado,
        contenido_texto=texto_extraido,
        contenido_normalizado=normalizar_texto(texto_extraido),
        metadatos=json.dumps(metadatos),
        user_id=usuario.id
    )
    db.add(nuevo_doc); db.commit()
    return {"mensaje": "OK"}

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
        if query and d.contenido_texto:
            clean_o = d.contenido_texto.replace("\n", " ")
            clean_n = normalizar_texto(clean_o)
            matches = list(re.finditer(re.escape(normalizar_texto(query)), clean_n))
            for match in matches[:5]:
                start, end = max(0, match.start() - 50), min(len(clean_o), match.end() + 50)
                frags.append(clean_o[start:end])
                
        final.append({
            "id": d.id, "nombre_archivo": d.nombre_archivo, 
            "metadatos": m, "fragmentos": frags, "coincidencias": len(frags), "texto_completo": d.contenido_texto
        })
    return {"total_encontrados": consulta.count(), "resultados": final}

@app.get("/documentos/{doc_id}/resumir")
async def resumir_documento(doc_id: int, db: Session = Depends(get_db)):
    doc = db.query(Documento).filter(Documento.id == doc_id).first()
    res = client_ai.chat.completions.create(messages=[{"role": "user", "content": f"Resume esto en 3 puntos clave:\n{doc.contenido_texto[:3000]}"}], model=MODELO_PRO)
    return {"resumen": res.choices[0].message.content}

@app.delete("/documentos/{doc_id}")
async def eliminar_documento(doc_id: int, db: Session = Depends(get_db)):
    doc = db.query(Documento).filter(Documento.id == doc_id).first()
    if os.path.exists(doc.ruta_archivo): os.remove(doc.ruta_archivo)
    db.delete(doc); db.commit()
    return {"mensaje": "OK"}