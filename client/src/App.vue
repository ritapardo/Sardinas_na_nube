<script setup>
import { ref, onMounted, watch } from 'vue'

const documentos = ref([])
const totalEncontrados = ref(0)
const paginaActual = ref(1)
const limite = 10
const queryBusqueda = ref('')
const categoriaSeleccionada = ref('Todas')
const archivoSeleccionado = ref(null)
const subiendo = ref(false)

const modalVisible = ref(false)
const docEnEdicion = ref(null)
const modoEdicion = ref(false)

const resumienDocId = ref(null)
const resumenTexto = ref('')
const cargandoResumen = ref(false)
const fragmentosVisibles = ref({}) 
const API_URL = 'http://127.0.0.1:8000'

const carpetas = [
  { nombre: 'Todas', color: 'bg-blue-100 text-blue-600', svg: '<path d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />' },
  { nombre: 'General', color: 'bg-cyan-100 text-cyan-600', svg: '<path d="M4 6a2 2 0 012-2h12a2 2 0 012 2v12a2 2 0 01-2 2H6a2 2 0 01-2-2V6zm4 4h8m-8 4h8" />' },
  { nombre: 'Finanzas', color: 'bg-green-100 text-green-600', svg: '<path d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />' },
  { nombre: 'Legal', color: 'bg-red-100 text-red-600', svg: '<path d="M3 6l3 1m0 0l-3 9a5.002 5.002 0 006.001 0M6 7l3 9M6 7l6-2m6 2l3-1m-3 1l-3 9a5.002 5.002 0 01-6.001 0M18 7l-3 9m3-9l-6-2m0-2v2m0 16V5m0 16H9m3 0h3" />' },
  { nombre: 'RRHH', color: 'bg-orange-100 text-orange-600', svg: '<path d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />' },
  { nombre: 'Proyectos', color: 'bg-indigo-100 text-indigo-600', svg: '<path d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />' },
  { nombre: 'Software', color: 'bg-purple-100 text-purple-600', svg: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />' }
]

const buscarDocumentos = async (reset = false) => {
  if (reset) paginaActual.value = 1
  const skip = (paginaActual.value - 1) * limite
  let url = `${API_URL}/documentos/?skip=${skip}&limit=${limite}&_t=${Date.now()}`
  if (queryBusqueda.value) url += `&query=${encodeURIComponent(queryBusqueda.value)}`
  if (categoriaSeleccionada.value !== 'Todas') url += `&categoria=${encodeURIComponent(categoriaSeleccionada.value)}`
  
  const res = await fetch(url); 
  const data = await res.json();
  documentos.value = data.resultados;
  totalEncontrados.value = data.total_encontrados;
  
  documentos.value.forEach(doc => {
    if (fragmentosVisibles.value[doc.id] === undefined) {
      fragmentosVisibles.value[doc.id] = 5;
    }
  });
}

let tId = null
watch(queryBusqueda, () => { clearTimeout(tId); tId = setTimeout(() => buscarDocumentos(true), 350) })

const abrirLector = (doc) => { 
  docEnEdicion.value = JSON.parse(JSON.stringify(doc)); 
  modalVisible.value = true; 
  modoEdicion.value = false;
}

const guardarCambios = async () => {
  const payload = {
    nombre_archivo: docEnEdicion.value.nombre_archivo,
    contenido_texto: docEnEdicion.value.texto_completo
  };

  if (docEnEdicion.value.metadatos.extension.toLowerCase().includes('xls') && docEnEdicion.value.metadatos.excel_grid) {
    payload.excel_grid = docEnEdicion.value.metadatos.excel_grid;
  }

  if (docEnEdicion.value.metadatos.html_preview) {
    const editorEl = document.querySelector('.docx-render-container');
    if (editorEl) {
      payload.html_preview = editorEl.innerHTML;     
      payload.contenido_texto = editorEl.innerText;  
    }
  }

  const res = await fetch(`${API_URL}/documentos/${docEnEdicion.value.id}`, {
    method: 'PUT', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });

  if (res.ok) {
    const data = await res.json(); 
    alert(`Guardado. Categoría IA: ${data.nueva_categoria}`);
    modalVisible.value = false; 
    buscarDocumentos(true);
  }
}

const descargarArchivo = (id) => window.open(`${API_URL}/documentos/${id}/descargar`, '_blank')

const resaltarBusqueda = (texto, query) => {
  if (!query) return texto
  const regex = new RegExp(`(${query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi')
  return texto.replace(regex, '<mark class="bg-yellow-200 text-black px-0.5 rounded font-bold">$1</mark>')
}

const manejarArchivo = (e) => { if (e.target.files.length > 0) archivoSeleccionado.value = e.target.files[0] }

const subirDocumento = async () => {
  if (!archivoSeleccionado.value) return
  subiendo.value = true
  const fd = new FormData(); fd.append("file", archivoSeleccionado.value)
  await fetch(`${API_URL}/importar/`, { method: 'POST', body: fd })
  archivoSeleccionado.value = null; subiendo.value = false; buscarDocumentos(true)
}

const eliminarDocumento = async (id) => { if(confirm("¿Eliminar?")) { await fetch(`${API_URL}/documentos/${id}`, {method:'DELETE'}); buscarDocumentos() } }

const generarResumen = async (id) => {
  if (resumienDocId.value === id) {
    resumienDocId.value = null;
    resumenTexto.value = "";
    return;
  }

  resumienDocId.value = id; 
  resumenTexto.value = "🤖 Analizando..."; 
  cargandoResumen.value = true;
  
  try {
    const res = await fetch(`${API_URL}/documentos/${id}/resumir`); 
    const data = await res.json();
    resumenTexto.value = data.resumen;
  } catch (error) {
    resumenTexto.value = "Error al generar el resumen.";
  } finally {
    cargandoResumen.value = false;
  }
}

const seleccionarCarpeta = (n) => { categoriaSeleccionada.value = n; buscarDocumentos(true) }
const cambiarPagina = (d) => { paginaActual.value += d; buscarDocumentos() }

onMounted(() => buscarDocumentos())
</script>

<template>
  <div class="min-h-screen bg-gray-50 p-4 md:p-8 font-sans text-gray-900 leading-tight">
    <div class="w-full mx-auto grid grid-cols-1 lg:grid-cols-4 gap-8">
      
      <aside class="space-y-6">
        <div class="bg-white p-6 rounded-3xl shadow-sm border border-gray-200 sticky top-8">
          <div class="flex items-center gap-3 mb-8 cursor-pointer" @click="queryBusqueda=''; seleccionarCarpeta('Todas')">
            <svg class="w-10 h-10 text-blue-600" fill="currentColor" viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 14.5v-9l6 4.5-6 4.5z"/></svg>
            <h1 class="text-xl font-black leading-none">Sardiñas <br><span class="text-blue-600 text-[10px]">na nube</span></h1>
          </div>
          <div class="space-y-4">
              <label for="fileInput" class="flex flex-col items-center justify-center w-full h-32 border-2 border-dashed border-gray-200 rounded-2xl cursor-pointer bg-gray-50 hover:bg-blue-50 transition-all text-center px-4 group">
                  <svg class="w-8 h-8 text-gray-300 group-hover:text-blue-400 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"/></svg>
                  <p class="text-[10px] text-gray-500 font-bold truncate w-full px-2">{{ archivoSeleccionado ? archivoSeleccionado.name : 'Importar PDF, Excel, Foto...' }}</p>
              </label>
              <input id="fileInput" type="file" class="hidden" @change="manejarArchivo" />
              <button @click="subirDocumento" :disabled="subiendo || !archivoSeleccionado" class="w-full bg-blue-600 py-4 rounded-2xl font-bold text-white shadow-lg active:scale-95 disabled:opacity-30 uppercase text-[10px] tracking-widest transition-all">
                {{ subiendo ? 'Procesando IA...' : 'Indexar Archivo' }}
              </button>
          </div>
        </div>
      </aside>

      <main class="lg:col-span-3 space-y-8">
        <div class="bg-white p-4 rounded-3xl shadow-sm border flex gap-4 focus-within:ring-2 ring-blue-100 transition-all">
          <input v-model="queryBusqueda" placeholder="Buscar texto en archivos, fotos o excels..." class="flex-1 bg-transparent px-4 py-2 outline-none font-medium text-lg" />
          <div class="bg-gray-100 text-gray-400 px-4 py-3 rounded-2xl text-[10px] font-black flex items-center shadow-inner">LIVE</div>
        </div>

        <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-7 gap-4">
          <button v-for="f in carpetas" :key="f.nombre" @click="seleccionarCarpeta(f.nombre)" :class="[ 'p-4 rounded-2xl border-2 transition-all transform hover:-translate-y-1 flex flex-col items-center group', categoriaSeleccionada === f.nombre ? 'border-blue-500 bg-white shadow-md' : 'border-transparent bg-white/60 hover:bg-white' ]">
            <div :class="['w-12 h-12 rounded-2xl flex items-center justify-center mb-3 shadow-sm transition-transform group-hover:scale-110', f.color]"><svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" v-html="f.svg"></svg></div>
            <p class="text-[11px] font-black uppercase tracking-widest text-gray-800">{{ f.nombre }}</p>
          </button>
        </div>

        <div class="space-y-6">
          <div v-for="doc in documentos" :key="doc.id" class="bg-white p-6 rounded-3xl shadow-sm border hover:shadow-lg transition-all tarjeta-documento">
            <div class="flex flex-col md:flex-row md:items-center gap-3 mb-6">
              <div class="w-16 h-16 rounded-2xl flex items-center justify-center text-white font-black shrink-0 shadow-md" 
                   :class="{'bg-red-500': doc.metadatos.extension.toLowerCase().includes('pdf'), 'bg-blue-500': doc.metadatos.extension.toLowerCase().includes('doc'), 'bg-green-500': doc.metadatos.extension.toLowerCase().includes('xls'), 'bg-orange-500': ['jpg','png','jpeg'].some(ext => doc.metadatos.extension.toLowerCase().includes(ext)), 'bg-gray-600': ['txt', 'md', 'json', 'py', 'js', 'csv'].includes(doc.metadatos.extension), 'bg-gray-700': true}">
                <span class="text-xs uppercase">{{ doc.metadatos.extension }}</span>
              </div>
              <div class="flex-1 min-w-0 pr-10 text-left">
                <h3 class="font-bold text-xl hover:text-blue-600 cursor-pointer" @click="abrirLector(doc)">{{ doc.nombre_archivo }}</h3>
                <div class="flex items-center gap-3 mt-2">
                    <span class="text-[9px] font-black uppercase text-blue-600 bg-blue-50 px-3 py-1 rounded-full border border-blue-100 shadow-sm">{{ doc.metadatos.categoria }}</span>
                    <span class="text-[10px] text-gray-500 font-bold flex items-center gap-1">
                    <svg class="w-3 h-3" fill="currentColor" viewBox="0 0 20 20"><path d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z"/></svg> {{ doc.autor }}</span>
                    <span class="text-[10px] text-gray-500 font-bold flex items-center gap-1">
                        <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>
                        {{ doc.fecha }}
                    </span>
                    <span class="text-[10px] text-gray-400 font-bold italic">Coincidencias: {{ doc.coincidencias }}</span>
                </div>
              </div>
              <div class="flex gap-2">
                <button @click="abrirLector(doc)" class="p-3 bg-gray-50 text-gray-600 rounded-2xl hover:bg-gray-200 transition-colors" title="Ver / Editar"><svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/></svg></button>
                <button @click="descargarArchivo(doc.id)" class="p-3 bg-blue-50 text-blue-600 rounded-2xl hover:bg-blue-100 transition-colors" title="Descargar"><svg class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24"><path d="m12 16l-5-5l1.4-1.45l2.6 2.6V4h2v8.15l2.6-2.6L17 11zm-6 4q-.825 0-1.412-.587T4 18v-3h2v3h12v-3h2v3q0 .825-.587 1.413T18 20z"/></svg></button>
                <button @click="generarResumen(doc.id)" :class="resumienDocId === doc.id ? 'bg-purple-600 text-white' : 'bg-purple-50 text-purple-600'" class="px-5 py-3 rounded-2xl font-bold text-xs hover:bg-purple-100 flex items-center gap-2 border border-purple-100 shadow-sm transition-all">
                    <span v-if="cargandoResumen && resumienDocId === doc.id" class="animate-spin w-3 h-3 border-2 border-white border-t-transparent rounded-full"></span>
                    {{ resumienDocId === doc.id && !cargandoResumen ? 'Ocultar Resumen' : 'Resumen IA' }}
                </button>
                <button @click="eliminarDocumento(doc.id)" class="p-3 bg-red-50 text-red-400 rounded-2xl hover:bg-red-100 transition-colors"><svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg></button>
              </div>
            </div>

            <div v-if="doc.fragmentos.length > 0" class="space-y-4 bg-gray-50 p-6 rounded-2xl border-l-4 border-blue-500 mb-6 shadow-inner">
              <div v-for="(f, i) in doc.fragmentos.slice(0, fragmentosVisibles[doc.id])" 
                :key="i" 
                class="text-sm italic text-gray-700 leading-relaxed border-b border-gray-200 last:border-0 pb-3" 
                v-html="'... ' + resaltarBusqueda(f, queryBusqueda) + ' ...'">
              </div>

              <div class="flex justify-between items-center pt-2">
                <button v-if="doc.fragmentos.length > fragmentosVisibles[doc.id]" 
                  @click="fragmentosVisibles[doc.id] += 10" 
                  class="text-[10px] font-black text-blue-600 uppercase tracking-widest hover:text-blue-800 transition-colors">
                Mostrar más coincidencias (+{{ Math.min(10, doc.fragmentos.length - fragmentosVisibles[doc.id]) }}) ↓
                </button>
                <span class="text-[9px] font-bold text-gray-400 uppercase">
                  Viendo {{ Math.min(fragmentosVisibles[doc.id], doc.fragmentos.length) }} de {{ doc.fragmentos.length }}
                </span>
              </div>
            </div>

            <div v-if="resumienDocId === doc.id" class="p-6 bg-gradient-to-br from-purple-50 to-white rounded-2xl border border-purple-100 shadow-inner mt-4">
                <p class="text-sm text-purple-900 leading-loose whitespace-pre-wrap font-medium italic">{{ resumenTexto }}</p>
            </div>
          </div>
        </div>
      </main>
    </div>

    <div v-if="modalVisible" class="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-4 md:p-12 animate-in fade-in duration-300">
      <div class="bg-white w-full max-w-6xl h-full rounded-[40px] shadow-2xl flex flex-col overflow-hidden">
        
        <div class="p-8 border-b flex justify-between items-center bg-white shrink-0 shadow-sm">
          <div class="flex items-center gap-6 flex-1 pr-10">
            <div class="w-12 h-12 rounded-2xl text-white flex items-center justify-center shadow-lg font-black text-xs uppercase"
                 :class="{'bg-red-500': docEnEdicion.metadatos.extension.toLowerCase().includes('pdf'), 'bg-blue-500': docEnEdicion.metadatos.extension.toLowerCase().includes('doc'), 'bg-green-500': docEnEdicion.metadatos.extension.toLowerCase().includes('xls'), 'bg-orange-500': ['jpg','png','jpeg'].some(ext => docEnEdicion.metadatos.extension.toLowerCase().includes(ext)), 'bg-blue-600': true}">
              {{ docEnEdicion.metadatos.extension }}
            </div>
            <input v-model="docEnEdicion.nombre_archivo" class="text-2xl font-black border-b-2 border-transparent focus:border-blue-500 outline-none w-full max-w-lg bg-transparent" />
          </div>
          <div class="flex gap-3">
            <button v-if="!docEnEdicion.metadatos.extension.toLowerCase().includes('pdf')" @click="guardarCambios" class="bg-blue-600 text-white px-8 py-3 rounded-2xl font-bold hover:bg-blue-700 active:scale-95 transition-all shadow-lg uppercase text-[10px] tracking-widest">
              Guardar e Indexar
            </button>
            <button @click="modalVisible = false" class="bg-gray-100 text-gray-500 p-3 rounded-2xl hover:bg-gray-200 transition-all">
              <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" /></svg>
            </button>
          </div>
        </div>

        <div class="flex-1 flex overflow-hidden bg-gray-50">
          
          <div v-if="docEnEdicion.metadatos.extension.toLowerCase().includes('pdf')" class="w-full h-full p-6">
            <iframe :src="`${API_URL}/uploads/${docEnEdicion.nombre_archivo}`" class="w-full h-full rounded-3xl border-none shadow-lg bg-white"></iframe>
          </div>

          <template v-else>
            <div class="w-1/2 border-r border-gray-200 p-6 flex flex-col">
              <p class="text-[10px] font-black text-gray-400 uppercase tracking-widest mb-4">Vista Previa Original</p>
              <div class="flex-1 bg-white rounded-3xl border border-gray-200 shadow-inner overflow-hidden relative">
                  
                  <div v-if="docEnEdicion.metadatos.extension.toLowerCase().includes('xls')" class="w-full h-full overflow-auto p-4 bg-gray-100/30">
                      <template v-if="docEnEdicion.metadatos.excel_grid && docEnEdicion.metadatos.excel_grid.length > 0">
                          <div v-for="(hoja, hIndex) in docEnEdicion.metadatos.excel_grid" :key="hIndex" class="mb-8">
                              <h4 class="font-bold text-blue-700 text-xs mb-3 uppercase tracking-widest bg-blue-100 inline-block px-3 py-1 rounded-lg border border-blue-200">
                                  Hoja: {{ hoja.hoja || 'Desconocida' }}
                              </h4>
                              <div class="overflow-x-auto border border-gray-200 rounded-xl shadow-sm">
                                  <table class="min-w-full text-[10px] font-mono border-collapse bg-white">
                                      <tbody>
                                          <tr v-for="(row, i) in hoja.filas" :key="i" class="border-b border-gray-100 hover:bg-gray-50 transition-colors">
                                              <td v-for="(cell, j) in row" :key="j" class="border-r border-gray-100 p-0 min-w-[120px] align-top relative">
                                                <input v-if="modoEdicion" v-model="hoja.filas[i][j]" class="w-full h-full min-h-[40px] px-4 py-2 bg-transparent outline-none focus:bg-blue-50 focus:ring-2 focus:ring-blue-400 text-gray-900 transition-all font-medium" />
                                                <div v-else class="w-full h-full min-h-[40px] px-4 py-2 whitespace-nowrap text-gray-700">{{ cell }}</div>
                                              </td>
                                          </tr>
                                      </tbody>
                                  </table>
                              </div>
                          </div>
                      </template>
                  </div>

                  <div v-else-if="['jpg','jpeg','png'].some(ext => docEnEdicion.metadatos.extension.toLowerCase().includes(ext))" class="w-full h-full flex items-center justify-center p-8 bg-gray-100/50">
                      <img :src="`${API_URL}/uploads/${docEnEdicion.nombre_archivo}`" class="max-w-full max-h-full object-contain shadow-2xl rounded-2xl border border-gray-200" />
                  </div>

                  <div v-else class="w-full h-full p-8 overflow-y-auto flex justify-center bg-gray-100/30">
                      <div class="bg-white shadow-xl w-full max-w-2xl min-h-full p-12 font-serif text-gray-800 whitespace-pre-wrap text-sm leading-relaxed relative">
                        
                        <div v-if="docEnEdicion.metadatos.html_preview" 
                          v-html="docEnEdicion.metadatos.html_preview" 
                          :contenteditable="modoEdicion"
                          class="docx-render-container transition-all outline-none"
                          :class="{'ring-4 ring-blue-400 bg-blue-50/50 p-6 rounded-2xl shadow-lg': modoEdicion}">
                        </div>

                        <div v-else class="whitespace-pre-wrap text-sm leading-relaxed">
                          {{ docEnEdicion.texto_completo || 'Este documento parece estar vacío o es ilegible.' }}
                        </div>
                      </div>
                  </div>
              </div>
            </div>

            <div class="w-1/2 p-6 flex flex-col">
              <div class="flex justify-between items-center mb-4">
                  <p class="text-[10px] font-black text-gray-400 uppercase tracking-widest">Contenido Extraído</p>
                  <button @click="modoEdicion = !modoEdicion" class="text-[10px] font-black text-blue-600 uppercase border border-blue-100 px-4 py-2 rounded-xl hover:bg-blue-50 transition-all shadow-sm">
                      {{ modoEdicion ? 'Bloquear Edición' : 'Editar Celdas / Texto' }}
                  </button>
              </div>
              <div class="flex-1 bg-white rounded-3xl border border-gray-200 shadow-inner p-8 overflow-y-auto">
                  
                  <div v-if="docEnEdicion.metadatos.extension.toLowerCase().includes('xls')" class="w-full h-full text-sm font-mono text-gray-600 leading-relaxed whitespace-pre-wrap">
                      <template v-for="(hoja, hIdx) in docEnEdicion.metadatos.excel_grid" :key="hIdx">
                          <p class="text-xs text-gray-400 mt-4 mb-1">--- {{ hoja.hoja }} ---</p>
                          <div v-for="(fila, fIdx) in hoja.filas" :key="fIdx">
                              {{ fila.join(' | ') }}
                          </div>
                      </template>
                  </div>
                  
                  <div v-else-if="modoEdicion && docEnEdicion.metadatos.html_preview" class="w-full h-full flex flex-col items-center justify-center text-center text-blue-600 bg-blue-50 p-6 rounded-2xl border-2 border-dashed border-blue-200">
                    <svg class="w-12 h-12 mb-4 animate-bounce" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"></path></svg>
                    <p class="font-bold text-lg mb-2">Modo Visual Activo</p>
                    <p class="text-sm font-medium opacity-80">Edita el texto directamente sobre el folio de la izquierda. Las imágenes y el formato se mantendrán intactos.</p>
                  </div>

                  <textarea v-else-if="modoEdicion" v-model="docEnEdicion.texto_completo" class="w-full h-full outline-none text-sm font-mono leading-relaxed resize-none bg-transparent text-gray-800 focus:ring-2 focus:ring-blue-100 p-4 rounded-xl"></textarea>
                  
                  <div v-else class="w-full h-full text-sm text-gray-600 leading-loose whitespace-pre-wrap font-medium" 
                       :class="(docEnEdicion.texto_completo || '').includes('ERROR') ? 'text-red-500 font-bold' : ''">
                      {{ docEnEdicion.texto_completo || 'No se encontró texto.' }}
                  </div>
              </div>
            </div>
          </template>

        </div>
      </div>
    </div>

  </div>
</template>

<style>
@import 'https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css';

mark { 
    background-color: #fef08a !important; 
    color: black !important; 
    padding: 0 4px; 
    border-radius: 4px; 
    border-bottom: 2px solid #facc15; 
}

.tarjeta-documento { 
    animation: fadeInSlide 0.4s ease-out forwards; 
}

@keyframes fadeInSlide { 
    from { opacity: 0; transform: translateY(30px); } 
    to { opacity: 1; transform: translateY(0); } 
}

::-webkit-scrollbar { 
    width: 6px; 
}

::-webkit-scrollbar-thumb { 
    background: #cbd5e0; 
    border-radius: 10px; 
}

.docx-render-container {
    width: 100%;
}

.docx-render-container img {
    max-width: 100% !important;
    height: auto !important;
    display: block;
    margin: 1.5rem auto;
    border-radius: 8px;
    box-shadow: 0 4px 10px rgba(0,0,0,0.1);
}

.docx-render-container p {
    margin-bottom: 1rem;
    line-height: 1.6;
    word-break: break-word;
}

.docx-render-container h1, 
.docx-render-container h2,
.docx-render-container h3 {
    font-weight: bold;
    margin-top: 1.5rem;
    margin-bottom: 0.5rem;
    color: #1a202c;
}

.docx-render-container img {
    user-select: none;
}
</style>