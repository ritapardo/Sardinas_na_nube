import pandas as pd

class Actividad:
    def __init__(self, id_actividad, duracion, predecesores):
        self.id = id_actividad
        self.t = duracion  # Duración (t_i)
        self.a = predecesores  # Predecesores a(i)
        self.d = []       # Sucesores d(i) - Se calculará automáticamente
        
        # Variables de tiempo (iniciadas en 0 o -1)
        self.tau = 0      # Inicio más pronto (Earliest Start)
        self.nabla = 0    # Fin más pronto (Earliest Finish)
        self.tau_star = float('inf')  # Fin más tarde (Latest Finish)
        self.delta_star = 0           # Inicio más tarde (Latest Start)
        self.holgura = 0              # Holgura total

def calcular_cpm(datos_proyecto):
    actividades = {}
    
    # 1. Inicialización y construcción de relaciones (M, t_i, a(i))
    for id_act, info in datos_proyecto.items():
        actividades[id_act] = Actividad(id_act, info['t'], info['a'])

    # Calcular sucesores d(i) automáticamente invirtiendo a(i)
    for id_act, act in actividades.items():
        for pred_id in act.a:
            if pred_id in actividades:
                actividades[pred_id].d.append(id_act)

    # ---------------------------------------------------------
    # 2. FASE DE IDA (Forward Pass) -> Calcular tau y nabla
    # tau_i = max(tau_j + t_j) para j en a(i)
    # ---------------------------------------------------------
    
    # Usamos ordenamiento topológico o iteración para asegurar que procesamos en orden
    procesados = []
    cola = [id for id, act in actividades.items() if not act.a] # Actividades sin predecesores
    
    while cola:
        curr_id = cola.pop(0)
        curr_act = actividades[curr_id]
        
        # Calcular Inicio Más Pronto (tau)
        if not curr_act.a:
            curr_act.tau = 0
        else:
            # max(tau_j + t_j) de los predecesores
            max_pre_finish = 0
            for pred_id in curr_act.a:
                pred = actividades[pred_id]
                if (pred.tau + pred.t) > max_pre_finish:
                    max_pre_finish = pred.tau + pred.t
            curr_act.tau = max_pre_finish
        
        # Calcular Fin Más Pronto (nabla)
        # nabla_i = tau_i + t_i
        curr_act.nabla = curr_act.tau + curr_act.t
        
        procesados.append(curr_id)
        
        # Añadir sucesores a la cola si todos sus predecesores han sido procesados
        for suc_id in curr_act.d:
            sucesor = actividades[suc_id]
            predecesores_listos = all(p in procesados for p in sucesor.a)
            if predecesores_listos and suc_id not in cola and suc_id not in procesados:
                cola.append(suc_id)

    # Duración del proyecto: max(tau_j + t_j) de actividades finales
    # 
    duracion_proyecto = max(act.nabla for act in actividades.values())

    # ---------------------------------------------------------
    # 3. FASE DE VUELTA (Backward Pass) -> Calcular tau* y delta*
    # tau*_i = min(tau*_j - t_j) para j en d(i)
    # ---------------------------------------------------------
    
    # Procesar en orden inverso a la fase de ida
    for curr_id in reversed(procesados):
        curr_act = actividades[curr_id]
        
        if not curr_act.d:
            # Si no tiene sucesores, es actividad final
            curr_act.tau_star = duracion_proyecto
        else:
            # min(tau*_j - t_j) -> min(Inicio tardío de sucesores)
            min_suc_start = float('inf')
            for suc_id in curr_act.d:
                suc = actividades[suc_id]
                # El inicio tardío del sucesor es (tau*_suc - t_suc)
                start_suc = suc.tau_star - suc.t
                if start_suc < min_suc_start:
                    min_suc_start = start_suc
            curr_act.tau_star = min_suc_start
            
        # Calcular Inicio Más Tarde (delta*)
        # delta*_i = tau*_i - t_i
        curr_act.delta_star = curr_act.tau_star - curr_act.t

        # Calcular Holgura Total
        #  Holgura = tau*_i - tau_i - t_i
        curr_act.holgura = curr_act.tau_star - curr_act.tau - curr_act.t

    return actividades, duracion_proyecto

# =============================================================================
# DATOS DE PRUEBA 
# =============================================================================
# Interpretación de la topología basada en el grafo  y la solución:
# Nota: D depende de B y C (por la flecha ficticia/dummy del nodo 3 al 5 en el grafo)
datos_ejemplo = {
    #PARA RESOLVER EL EJEMPLO DEL TEMA 4, NO EL DE LA PRACTICA COMO TAL, PARA ESO, REVISAR ARCHIVO: practica_3_psi.py.
    'A': {'t': 8, 'a': []},
    'B': {'t': 10, 'a': []},
    'C': {'t': 12, 'a': []},     
    'D': {'t': 10, 'a': ['A']}, 
    'E': {'t': 7, 'a': ['B']},
    'F': {'t': 7, 'a': ['C', 'D', 'E']},     
    'G': {'t': 14, 'a': ['A']},
    'H': {'t': 12, 'a': ['B']},
    'I': {'t': 10, 'a': ['F', 'G']}
}

# Ejecutar cálculo
resultados, duracion_total = calcular_cpm(datos_ejemplo)


data = []
for id_act, act in resultados.items():
    es_critica = "SÍ" if act.holgura == 0 else ""
    data.append([
        id_act, 
        act.t, 
        f"{act.tau} / {act.delta_star}", # Calendario Inicio (Pronto/Tarde)
        f"{act.nabla} / {act.tau_star}", # Calendario Fin (Pronto/Tarde)
        act.holgura,
        es_critica
    ])

df = pd.DataFrame(data, columns=[
    "Actividad", "Duración", "Inicio (Temprano/Tardío)", "Fin (Temprano/Tardío)", "Holgura", "Crítica"
])

print(f"--- RESULTADOS DEL PROYECTO ---")
print(f"Duración Total del Proyecto: {duracion_total} días")
print("\nTabla de Detalles:")
print(df.to_string(index=False))

# Verificación automática
ruta_critica = [id for id, act in resultados.items() if act.holgura == 0]
print(f"\nRuta Crítica Calculada: {' - '.join(sorted(ruta_critica))}")