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

const resumienDocId = ref(null)
const resumenTexto = ref('')
const cargandoResumen = ref(false)

const fragmentosVisibles = ref({}) 
const API_URL = 'http://127.0.0.1:8000'

const carpetas = [
  { nombre: 'Todas', color: 'bg-blue-100 text-blue-600', svg: '<path d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />' },
  { nombre: 'Finanzas', color: 'bg-green-100 text-green-600', svg: '<path d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />' },
  { nombre: 'Legal', color: 'bg-red-100 text-red-600', svg: '<path d="M3 6l3 1m0 0l-3 9a5.002 5.002 0 006.001 0M6 7l3 9M6 7l6-2m6 2l3-1m-3 1l-3 9a5.002 5.002 0 01-6.001 0M18 7l-3 9m3-9l-6-2m0-2v2m0 16V5m0 16H9m3 0h3" />' },
  { nombre: 'RRHH', color: 'bg-orange-100 text-orange-600', svg: '<path d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />' },
  { nombre: 'Proyectos', color: 'bg-indigo-100 text-indigo-600', svg: '<path d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />' },
  { nombre: 'Charlas', color: 'bg-purple-100 text-purple-600', svg: '<path d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />' }
]

const buscarDocumentos = async (resetearPagina = false) => {
  if (resetearPagina) paginaActual.value = 1
  const skip = (paginaActual.value - 1) * limite
  let url = `${API_URL}/documentos/?skip=${skip}&limit=${limite}`
  if (queryBusqueda.value) url += `&query=${encodeURIComponent(queryBusqueda.value)}`
  if (categoriaSeleccionada.value !== 'Todas') url += `&categoria=${encodeURIComponent(categoriaSeleccionada.value)}`
  
  const res = await fetch(url)
  const data = await res.json()
  documentos.value = data.resultados
  totalEncontrados.value = data.total_encontrados
  documentos.value.forEach(doc => { if(!fragmentosVisibles.value[doc.id]) fragmentosVisibles.value[doc.id] = 5 })
}

let timeoutBusqueda = null
watch(queryBusqueda, () => {
  clearTimeout(timeoutBusqueda)
  timeoutBusqueda = setTimeout(() => {
    buscarDocumentos(true)
  }, 350) 
})

const resaltarBusqueda = (texto, query) => {
  if (!query) return texto
  const escapedQuery = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const regex = new RegExp(`(${escapedQuery})`, 'gi')
  return texto.replace(regex, '<mark class="bg-yellow-200 text-black px-0.5 rounded font-bold">$1</mark>')
}

const mostrarMasFragmentos = (docId) => { fragmentosVisibles.value[docId] += 10 }
const manejarArchivo = (e) => { archivoSeleccionado.value = e.target.files[0] }
const subirDocumento = async () => {
  if (!archivoSeleccionado.value) return
  subiendo.value = true
  const fd = new FormData(); fd.append("file", archivoSeleccionado.value)
  await fetch(`${API_URL}/importar/`, { method: 'POST', body: fd })
  archivoSeleccionado.value = null; subiendo.value = false; buscarDocumentos(true)
}
const verDocumento = (n) => window.open(`${API_URL}/uploads/${n}`, '_blank')
const eliminarDocumento = async (id) => { if(confirm("¿Eliminar?")) { await fetch(`${API_URL}/documentos/${id}`, {method:'DELETE'}); buscarDocumentos() } }
const generarResumen = async (docId) => {
  resumienDocId.value = docId; resumenTexto.value = "🤖 Analizando..."; cargandoResumen.value = true
  const res = await fetch(`${API_URL}/documentos/${docId}/resumir`); const data = await res.json()
  resumenTexto.value = data.resumen; cargandoResumen.value = false
}
const seleccionarCarpeta = (n) => { categoriaSeleccionada.value = n; buscarDocumentos(true) }
const cambiarPagina = (d) => { paginaActual.value += d; buscarDocumentos() }

onMounted(() => buscarDocumentos())
</script>

<template>
  <div class="min-h-screen bg-gray-50 p-4 md:p-8 font-sans text-gray-900 selection:bg-blue-100">
    <div class="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-4 gap-8">
      
      <aside class="space-y-6">
        <div class="bg-white p-6 rounded-3xl shadow-sm border border-gray-200 sticky top-8">
          <div class="flex items-center gap-3 mb-8 cursor-pointer" @click="queryBusqueda=''; seleccionarCarpeta('Todas')">
            <svg class="w-10 h-10 text-blue-600" fill="currentColor" viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 14.5v-9l6 4.5-6 4.5z"/></svg>
            <h1 class="text-xl font-black">Sardiñas <span class="text-blue-600">na nube</span></h1>
          </div>
          <label for="fileInput" class="flex flex-col items-center justify-center w-full h-32 border-2 border-dashed border-gray-200 rounded-2xl cursor-pointer bg-gray-50 hover:bg-blue-50 hover:border-blue-300 transition-all text-center px-4">
              <p class="text-[10px] text-gray-400 font-bold truncate">{{ archivoSeleccionado ? archivoSeleccionado.name : 'Arrastra o haz click' }}</p>
              <input id="fileInput" type="file" class="hidden" @change="manejarArchivo" />
          </label>
          <button @click="subirDocumento" :disabled="subiendo || !archivoSeleccionado" class="w-full bg-blue-600 py-4 rounded-2xl font-bold text-white mt-4 disabled:opacity-40 shadow-lg shadow-blue-100 active:scale-95 transition-transform">
            {{ subiendo ? 'Indexando...' : 'Indexar Documento' }}
          </button>
        </div>
      </aside>

      <main class="lg:col-span-3 space-y-8">
        <div class="bg-white p-4 rounded-3xl shadow-sm border flex gap-4 ring-offset-2 focus-within:ring-2 ring-blue-100 transition-all">
          <input v-model="queryBusqueda" placeholder="Escribe para buscar en tiempo real..." class="flex-1 bg-transparent px-4 py-2 outline-none font-medium text-lg placeholder-gray-300" />
          <div class="bg-gray-100 text-gray-400 px-4 py-3 rounded-2xl text-xs font-bold flex items-center">LIVE</div>
        </div>

        <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          <button v-for="f in carpetas" :key="f.nombre" @click="seleccionarCarpeta(f.nombre)" :class="[ 'p-4 rounded-2xl border-2 transition-all transform hover:-translate-y-1 flex flex-col items-center text-center group', categoriaSeleccionada === f.nombre ? 'border-blue-500 bg-white shadow-md' : 'border-transparent bg-white/60 hover:bg-white' ]">
            <div :class="['w-12 h-12 rounded-2xl flex items-center justify-center mb-3 shadow-sm', f.color]"><svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" v-html="f.svg"></svg></div>
            <p class="text-[11px] font-black uppercase text-gray-800">{{ f.nombre }}</p>
          </button>
        </div>

        <div class="space-y-6">
          <div v-for="doc in documentos" :key="doc.id" class="bg-white p-6 rounded-3xl shadow-sm border hover:shadow-lg transition-shadow relative overflow-hidden">
            <div class="flex flex-col md:flex-row md:items-center gap-6 mb-6">
              <div class="w-16 h-16 rounded-2xl flex items-center justify-center text-white font-black shrink-0 shadow-md" :class="{'bg-red-500': doc.metadatos.extension==='pdf', 'bg-blue-500': doc.metadatos.extension.includes('doc'), 'bg-green-500': doc.metadatos.extension.includes('xls'), 'bg-gray-700': true}">{{doc.metadatos.extension.toUpperCase()}}</div>
              <div class="flex-1 min-w-0 pr-10">
                <h3 class="font-bold text-xl truncate hover:text-blue-600 cursor-pointer transition-colors" @click="verDocumento(doc.nombre_archivo)">{{ doc.nombre_archivo }}</h3>
                <div class="flex gap-4 mt-2">
                    <span class="text-[9px] font-black uppercase text-blue-600 bg-blue-50 px-3 py-1 rounded-full border border-blue-100 shadow-sm">{{ doc.metadatos.categoria }}</span>
                    <span class="text-xs text-gray-400 font-bold italic">Coincidencias: {{ doc.coincidencias }}</span>
                </div>
              </div>
              <div class="flex gap-2 shrink-0">
                <button @click="verDocumento(doc.nombre_archivo)" class="p-3 bg-gray-50 text-gray-600 rounded-2xl hover:bg-gray-200" title="Ver original"><svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/></svg></button>
                <button @click="generarResumen(doc.id)" class="px-5 py-3 bg-purple-50 text-purple-600 rounded-2xl font-bold text-xs hover:bg-purple-100 flex items-center gap-2 border border-purple-100">
                    <span v-if="cargandoResumen && resumienDocId === doc.id" class="animate-spin w-3 h-3 border-2 border-purple-600 border-t-transparent rounded-full"></span>
                    <svg v-else class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg> Análisis IA
                </button>
                <button @click="eliminarDocumento(doc.id)" class="p-3 bg-red-50 text-red-400 rounded-2xl hover:bg-red-100 hover:text-red-600"><svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg></button>
              </div>
            </div>

            <div v-if="doc.fragmentos.length > 0" class="space-y-4 bg-gray-50 p-6 rounded-2xl border-l-4 border-blue-500 mb-6 shadow-inner">
              <div v-for="(f, i) in doc.fragmentos.slice(0, fragmentosVisibles[doc.id])" :key="i" 
                   class="text-sm italic text-gray-700 leading-relaxed border-b border-gray-200 last:border-0 pb-3"
                   v-html="'... ' + resaltarBusqueda(f, queryBusqueda) + ' ...'">
              </div>
              <button v-if="doc.coincidencias > fragmentosVisibles[doc.id]" @click="mostrarMasFragmentos(doc.id)" class="text-xs font-black text-blue-600 uppercase tracking-widest mt-4 flex items-center gap-2 hover:translate-x-1 transition-transform">
                Cargar {{ Math.min(10, doc.coincidencias - fragmentosVisibles[doc.id]) }} coincidencias más <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M19 9l-7 7-7-7"/></svg>
              </button>
            </div>

            <div v-if="resumienDocId === doc.id" class="p-6 bg-gradient-to-br from-purple-50 to-white rounded-2xl border border-purple-100 shadow-inner ring-1 ring-purple-200 animate-pulse-subtle">
                <p class="text-[10px] font-black text-purple-700 mb-4 uppercase tracking-widest flex items-center gap-2">🤖 Informe de Inteligencia Corporativa</p>
                <p class="text-sm text-purple-900 leading-loose whitespace-pre-wrap font-medium">{{ resumenTexto }}</p>
            </div>
          </div>
        </div>

        <div class="flex items-center justify-center gap-4 pt-12" v-if="totalEncontrados > limite">
          <button @click="cambiarPagina(-1)" :disabled="paginaActual === 1" class="p-4 bg-white border rounded-2xl disabled:opacity-30 hover:bg-gray-100 transition-colors shadow-sm">← Anterior</button>
          <div class="bg-gray-900 text-white px-5 py-3 rounded-2xl font-mono text-sm font-bold shadow-md">Página {{ paginaActual }} / {{ Math.ceil(totalEncontrados / limite) }}</div>
          <button @click="cambiarPagina(1)" :disabled="(paginaActual * limite) >= totalEncontrados" class="p-4 bg-white border rounded-2xl disabled:opacity-30 hover:bg-gray-100 transition-colors shadow-sm">Siguiente →</button>
        </div>
      </main>
    </div>
  </div>
</template>

<style>
@import 'https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css';
mark { background-color: #fef08a !important; color: black !important; padding: 0 4px; border-radius: 4px; border-bottom: 2px solid #facc15; }
.tarjeta-documento { animation: fadeInSlide 0.5s cubic-bezier(0.4, 0, 0.2, 1); }
@keyframes fadeInSlide { from { opacity: 0; transform: translateY(30px); } to { opacity: 1; transform: translateY(0); } }
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-thumb { background: #cbd5e0; border-radius: 10px; }
.animate-pulse-subtle { animation: pulse-subtle 3s infinite ease-in-out; }
@keyframes pulse-subtle { 0%, 100% { opacity: 1; } 50% { opacity: 0.8; } }
</style>