<script setup>
import { ref, onMounted } from 'vue'

const documentos = ref([])
const totalEncontrados = ref(0)
const paginaActual = ref(1)
const limite = 10
const queryBusqueda = ref('')
const categoriaSeleccionada = ref('Todas')
const archivoSeleccionado = ref(null)
const subiendo = ref(false)

const resumienDocId = ref(null)
const resumenTexto = ref('')
const cargandoResumen = ref(false)

const API_URL = 'http://127.0.0.1:8000'

const carpetas = [
  { nombre: 'Todas', icono: '📁', color: 'bg-blue-100 text-blue-600' },
  { nombre: 'Finanzas', icono: '💰', color: 'bg-green-100 text-green-600' },
  { nombre: 'Legal', icono: '⚖️', color: 'bg-red-100 text-red-600' },
  { nombre: 'RRHH', icono: '👥', color: 'bg-orange-100 text-orange-600' },
  { nombre: 'Proyectos', icono: '🚀', color: 'bg-indigo-100 text-indigo-600' },
  { nombre: 'Charlas', icono: '🎙️', color: 'bg-purple-100 text-purple-600' },
]

const buscarDocumentos = async (resetearPagina = false) => {
  if (resetearPagina) paginaActual.value = 1
  const skip = (paginaActual.value - 1) * limite
  
  let url = `${API_URL}/documentos/?skip=${skip}&limit=${limite}`
  if (queryBusqueda.value) url += `&query=${encodeURIComponent(queryBusqueda.value)}`
  if (categoriaSeleccionada.value !== 'Todas') url += `&categoria=${encodeURIComponent(categoriaSeleccionada.value)}`
  
  try {
    const res = await fetch(url)
    const data = await res.json()
    documentos.value = data.resultados
    totalEncontrados.value = data.total_encontrados
  } catch (err) {
    console.error("Error en la búsqueda:", err)
  }
}

const seleccionarCarpeta = (nombre) => {
  categoriaSeleccionada.value = nombre
  buscarDocumentos(true)
}

const manejarArchivo = (e) => { archivoSeleccionado.value = e.target.files[0] }

const subirDocumento = async () => {
  if (!archivoSeleccionado.value) return alert("Por favor, selecciona un archivo primero")
  subiendo.value = true
  const fd = new FormData()
  fd.append("file", archivoSeleccionado.value)
  
  try {
    const res = await fetch(`${API_URL}/importar/`, { method: 'POST', body: fd })
    if (res.ok) {
      alert("¡Documento importado y categorizado por IA con éxito!")
      archivoSeleccionado.value = null
      document.getElementById('fileInput').value = ''
      buscarDocumentos(true)
    }
  } catch (err) {
    alert("Error al conectar con el servidor")
  } finally {
    subiendo.value = false
  }
}

const generarResumen = async (docId) => {
  if (cargandoResumen.value) return 
  
  resumienDocId.value = docId
  resumenTexto.value = "🤖 La IA está analizando el contenido para generar un resumen..."
  cargandoResumen.value = true
  
  try {
    const res = await fetch(`${API_URL}/documentos/${docId}/resumir`)
    if (!res.ok) throw new Error("Fallo en la IA")
    
    const data = await res.json()
    resumenTexto.value = data.resumen
  } catch (err) {
    resumenTexto.value = "❌ No se pudo generar el resumen. Revisa la conexión."
  } finally {
    cargandoResumen.value = false
  }
}

const cambiarPagina = (delta) => {
  paginaActual.value += delta
  buscarDocumentos()
}

onMounted(() => buscarDocumentos())
</script>

<template>
  <div class="min-h-screen bg-gray-50 p-4 md:p-8 font-sans text-gray-900">
    <div class="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-4 gap-8">
      
      <aside class="space-y-6">
        <div class="bg-white p-6 rounded-3xl shadow-sm border border-gray-200 sticky top-8">
          <div class="flex items-center gap-3 mb-8">
            <span class="text-4xl">🐟</span>
            <div>
              <h1 class="text-xl font-black leading-none">Sardiñas</h1>
              <span class="text-blue-600 font-black text-xl">na nube</span>
            </div>
          </div>
          
          <div class="space-y-4">
            <label class="block text-[10px] font-black text-gray-400 uppercase tracking-widest">Importación Inteligente</label>
            <div class="group relative">
              <input type="file" id="fileInput" @change="manejarArchivo" class="text-xs w-full block bg-gray-50 p-3 rounded-xl border border-dashed border-gray-300 cursor-pointer hover:border-blue-400 transition-colors" />
            </div>
            <button @click="subirDocumento" :disabled="subiendo" 
                    class="w-full bg-blue-600 hover:bg-blue-700 text-white py-4 rounded-2xl font-bold transition-all shadow-lg active:scale-95 disabled:opacity-50 flex items-center justify-center gap-2">
              <span v-if="subiendo" class="animate-spin inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full"></span>
              {{ subiendo ? 'Procesando...' : 'Subir Documento' }}
            </button>
          </div>

          <div class="mt-12 pt-6 border-t border-gray-100">
            <div class="flex items-center justify-between mb-2">
              <span class="text-[10px] text-gray-400 font-bold uppercase">Estado de la IA</span>
              <span class="flex h-2 w-2 rounded-full bg-green-500 animate-pulse"></span>
            </div>
            <p class="text-[10px] text-gray-400 leading-relaxed italic">Groq Llama-3 Engine Active</p>
          </div>
        </div>
      </aside>

      <main class="lg:col-span-3 space-y-8">
        
        <div class="bg-white p-4 rounded-3xl shadow-sm border border-gray-200 flex flex-col md:flex-row gap-4 items-center">
          <div class="relative flex-1 w-full">
            <span class="absolute left-4 top-4 opacity-30 text-xl">🔍</span>
            <input v-model="queryBusqueda" @keyup.enter="buscarDocumentos(true)" 
                   placeholder="Buscar en el archivador inteligente..." 
                   class="w-full bg-gray-50 border-none rounded-2xl p-4 pl-12 focus:ring-2 focus:ring-blue-400 outline-none text-gray-700 font-medium" />
          </div>
          <button @click="buscarDocumentos(true)" class="bg-gray-900 text-white px-10 py-4 rounded-2xl font-bold hover:bg-black transition-all active:scale-95 shadow-md">Buscar</button>
        </div>

        <section>
          <div class="flex items-center justify-between mb-4 px-2">
            <h2 class="text-xs font-black text-gray-400 uppercase tracking-widest">Carpetas Inteligentes</h2>
          </div>
          <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
            <div v-for="folder in carpetas" :key="folder.nombre" 
                 @click="seleccionarCarpeta(folder.nombre)"
                 :class="[
                   'cursor-pointer p-4 rounded-2xl border-2 transition-all transform hover:-translate-y-1 hover:shadow-md flex flex-col items-center text-center',
                   categoriaSeleccionada === folder.nombre ? 'border-blue-500 bg-white shadow-sm scale-105' : 'border-transparent bg-white/60 hover:bg-white'
                 ]">
              <div :class="['w-12 h-12 rounded-2xl flex items-center justify-center text-2xl mb-3 shadow-sm', folder.color]">
                {{ folder.icono }}
              </div>
              <p class="text-[11px] font-black uppercase tracking-tighter text-gray-800">{{ folder.nombre }}</p>
              <p class="text-[9px] text-gray-400 font-bold mt-1">Auto-archivado</p>
            </div>
          </div>
        </section>

        <div class="space-y-4">
          <div class="flex items-center justify-between px-2">
            <p class="text-xs font-bold text-gray-400 uppercase">
              Resultados en <span class="text-blue-600">"{{ categoriaSeleccionada }}"</span> ({{ totalEncontrados }})
            </p>
          </div>

          <div v-for="doc in documentos" :key="doc.id" class="bg-white p-6 rounded-3xl shadow-sm border border-gray-100 hover:shadow-lg transition-all tarjeta-documento relative overflow-hidden">
            
            <div class="absolute top-0 right-0 p-4">
               <span class="text-[9px] font-black uppercase text-blue-600 bg-blue-50 px-3 py-1 rounded-full border border-blue-100 shadow-sm">
                  {{ doc.metadatos.categoria || 'General' }}
                </span>
            </div>

            <div class="flex justify-between items-start mb-6">
              <div class="flex gap-4 items-center">
                <div class="w-16 h-16 flex items-center justify-center rounded-2xl text-white font-black text-sm shadow-inner"
                     :class="{
                       'bg-red-500': doc.metadatos.extension === 'pdf', 
                       'bg-blue-600': doc.metadatos.extension.includes('doc'), 
                       'bg-green-600': doc.metadatos.extension.includes('xls'), 
                       'bg-gray-700': !['pdf','doc','xls'].some(e => doc.metadatos.extension.includes(e))
                     }">
                  {{ doc.metadatos.extension.toUpperCase() }}
                </div>
                <div>
                  <h3 class="font-bold text-gray-900 text-lg leading-tight mb-1 max-w-[250px] md:max-w-md truncate">{{ doc.nombre_archivo }}</h3>
                  <div class="flex items-center gap-3 text-[11px] font-bold text-gray-400">
                    <span>👤 {{ doc.metadatos.autor || 'Sistema' }}</span>
                    <span>📦 {{ (doc.metadatos.tamano_bytes / 1024).toFixed(1) }} KB</span>
                  </div>
                </div>
              </div>
              
              <button @click="generarResumen(doc.id)" 
                      class="text-xs px-5 py-2.5 rounded-xl font-bold transition-all flex items-center gap-2 shadow-sm border mt-10 md:mt-0"
                      :class="resumienDocId === doc.id ? 'bg-purple-600 text-white border-purple-600' : 'bg-white text-purple-600 border-purple-100 hover:bg-purple-50'">
                <span v-if="cargandoResumen && resumienDocId === doc.id" class="animate-spin inline-block w-3 h-3 border-2 border-white border-t-transparent rounded-full"></span>
                <span v-else>✨</span> Resumen IA
              </button>
            </div>

            <div v-if="doc.fragmentos.length > 0" class="bg-blue-50/30 p-5 rounded-2xl border-l-4 border-blue-400 space-y-4 mb-5">
              <p class="text-[10px] font-black text-blue-500 uppercase tracking-widest">Apariciones detectadas ({{doc.coincidencias}}):</p>
              <div v-for="(f, i) in doc.fragmentos" :key="i" class="text-sm italic text-gray-600 leading-relaxed border-b border-blue-50 last:border-0 pb-3 last:pb-0">
                "...{{ f }}..."
              </div>
            </div>

            <div v-if="resumienDocId === doc.id" 
                 class="mb-6 p-6 bg-gradient-to-br from-purple-50 to-white rounded-2xl border border-purple-100 shadow-inner relative">
              <div class="absolute top-2 right-4 opacity-10 text-4xl">🤖</div>
              <p class="text-xs font-black text-purple-700 mb-3 uppercase tracking-widest flex items-center gap-2">
                <span class="w-2 h-2 bg-purple-500 rounded-full animate-pulse"></span> Análisis del Asistente
              </p>
              <p class="text-sm text-purple-950 leading-relaxed whitespace-pre-wrap font-medium">
                {{ resumenTexto }}
              </p>
            </div>

            <div class="flex items-center text-[10px] font-bold text-gray-300 pt-4 border-t border-gray-50">
               <span v-if="doc.metadatos.num_paginas">📄 {{ doc.metadatos.num_paginas }} páginas detectadas</span>
               <span class="ml-auto">ID: #00{{ doc.id }}</span>
            </div>
          </div>
        </div>

        <div class="flex items-center justify-center gap-6 py-12" v-if="totalEncontrados > limite">
          <button @click="cambiarPagina(-1)" :disabled="paginaActual === 1" 
                  class="bg-white border-2 border-gray-100 px-8 py-3 rounded-2xl font-bold text-gray-600 disabled:opacity-30 hover:bg-gray-100 transition shadow-sm">
            Anterior
          </button>
          <div class="flex items-center gap-3">
            <span class="bg-blue-600 text-white px-4 py-2 rounded-xl font-bold shadow-md text-sm">{{ paginaActual }}</span>
            <span class="text-xs font-bold text-gray-400 uppercase tracking-widest">de {{ Math.ceil(totalEncontrados / limite) }}</span>
          </div>
          <button @click="cambiarPagina(1)" :disabled="(paginaActual * limite) >= totalEncontrados" 
                  class="bg-white border-2 border-gray-100 px-8 py-3 rounded-2xl font-bold text-gray-600 disabled:opacity-30 hover:bg-gray-100 transition shadow-sm">
            Siguiente
          </button>
        </div>
      </main>

    </div>
  </div>
</template>

<style>
@import 'https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css';

.tarjeta-documento {
  animation: fadeInSlide 0.4s ease-out forwards;
}

@keyframes fadeInSlide {
  from { opacity: 0; transform: translateY(15px); }
  to { opacity: 1; transform: translateY(0); }
}

::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #cbd5e0; border-radius: 10px; }
::-webkit-scrollbar-thumb:hover { background: #94a3b8; }
</style>