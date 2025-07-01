import pyomo
from pyomo.environ import *
from pyomo.opt import SolverFactory
from Funciones import *
from datetime import datetime
import pickle
import pandas as pd

# Usar cbc como optimizador
solver = SolverFactory('cbc', executable='Optimizer\\Cbc-releases.2.10.12-windows-2022-msvs-v17-Release-x64\\bin\\cbc.exe')

# instancias a correr
ins = ['instance1', 'instance2', 'instance3', 'instance4', 'instance5', 'instance6']
ins2 = ['instance7', 'instance8', 'instance9', 'instance10']
instancias_a_correr = ins + ins2

tiempo_maximo = 3600  # Tiempo máximo en segundos

for instancia in instancias_a_correr:
    if instancia in ins:
        pass
    else:
        tiempo_maximo += 1800  # Tiempo máximo (incremental) en segundos para instancias más grandes
    
    # Correr modelo F2 (Optimiza los intereses de los colaboradores)
  
    # Llamar a la función para importar datos
    E, D, T, G, Z, dz, dr, e_g, di, max, min = importar_data(f'instances\\{instancia}.json', imprimir=False)

    # Correr modelo F2 (Optimiza los intereses de los colaboradores)

    model = ConcreteModel(name='Colaboradores')
    model.X = Var(E, D, T, Z, within=Binary, initialize = 0) # Si el colaborador e en el escritorio d asiste el dia d en la zona z
    model.Y = Var(E, T, within=Binary, initialize = 0) # Si el colaborador e asiste el dia t
    model.Z = Var(G, T, within=Binary, initialize = 0) # Si el grupo g tiene primario el dia t

    # Funcion objetivo: Maximizar la satisfacción de los empleados
    def satisfaccion_rule(model):
        return sum(
            model.X[e,d,t,z] * int(t in di[e])
            for e in E
            for d in D
            for t in T
            for z in Z
        )
    model.satisfaccion = Objective(rule=satisfaccion_rule, sense=maximize)

    #RESTRICCIONES
    # Relación [X] con variable auxiliar Y
    def dias_presencialidad(model, e, t):
        return sum(model.X[e, d, t, z] for d in D for z in Z) == model.Y[e, t]
    model.dias_presencialidad = Constraint(E, T, rule=dias_presencialidad)

    # Días de presencialidad en el rango
    def dias_min(model, e):
        return sum(model.Y[e, t] for t in T) >= min
    model.dias_min = Constraint(E, rule=dias_min)

    def dias_max(model, e):
        return sum(model.Y[e, t] for t in T) <= max
    model.dias_max = Constraint(E, rule=dias_max)

    # Asignar solo un escritorio si va dicho dia
    def solo_un_escritorio(model, e, t):
        return sum(model.X[e, d, t, z] for d in D for z in Z) <= 1
    model.solo_un_escritorio = Constraint(E, T, rule=solo_un_escritorio)

    # Cada colaborador debe estar en un escritorio de cumplas con sus caracteristicas
    def colaborador_escritorio(model, e, d, t, z):
        return model.X[e, d, t, z] <= int((d in dr[e]))
    model.colaborador_escritorio = Constraint(E, D, T, Z, rule=colaborador_escritorio)

    # Un escritorio solo se le puede asignar a una persona
    def escritorio_unico(model, d, t):
        return sum(model.X[e, d, t, z] for e in E if d in dr[e] for z in Z if d in dz[z]) <= 1
    model.escritorio_unico = Constraint(D, T, rule=escritorio_unico)

    # No se debe asignar escritorios que no estan en esa zona #############################################
    def no_esta_en_zona(model, e, d, t, z):
        return model.X[e, d, t, z] <= int((d in dz[z]))
    model.no_esta_en_zona = Constraint(E, D, T, Z, rule=no_esta_en_zona)

    # Cada grupo tiene grupo primario una vez
    def grupo_primario(model, g):
        return sum(model.Z[g, t] for t in T) == 1
    model.grupo_primario = Constraint(G, rule=grupo_primario)

    # Los integrantes de cada grupo deben asistir al primario
    def asistencia_en_reunion(model, e, t, g):
        if e in e_g[g]:
            return model.Y[e, t] >= model.Z[g, t]
        else:
            return Constraint.Skip
    model.asistencia_en_reunion = Constraint(E, T, G, rule=asistencia_en_reunion)

    # Establecer límite de tiempo en segundos
    solver.options['seconds'] = 300

    # Establecer tolerancia de optimalidad
    solver.options['ratio'] = 0.01  # 1% de tolerancia de optimalidad
    # Criterios de parada: tiempo máximo (en segundos) y tolerancia de optimalidad
    solver.solve(
        model,
        tee=True,  # Muestra el log del solver
    )


    total_presencialidad = 0 # Asignaciones totales de presencialidad
    preferencias_satisfechas = 0 # Maximo preferencias satisfechas

    for e in E:
        for t in T:
            if model.Y[e, t].value == 1:
                total_presencialidad += 1
                if t in di[e]:  # Si el día asignado está dentro de sus días preferidos
                    preferencias_satisfechas += 1

    # Porcentaje de coincidencia
    if total_presencialidad > 0:
        porcentaje = 100 * preferencias_satisfechas / total_presencialidad
    else:
        porcentaje = 0

    satisfaccion_deseada = 0.65
    epsilon = round((preferencias_satisfechas / (porcentaje/100)) * satisfaccion_deseada, 0)

    #  Guardar resultados del modelo
    with open(f'Model_outputs_F2\\model_{instancia}.pkl', 'wb') as f:
        pickle.dump(model, f)
    
    # Guardar la hora actual
    hora_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Guardar la hora de finalización
    with open(f'Model_outputs_F2\\hora_finalizacion_{instancia}.txt', 'w') as f:
        f.write(hora_actual)

    # eliminar model
    del model

    # Correr modelo F1 (Optimiza los intereses de la universidad)
    ##############################################################################################################################################################
    model = ConcreteModel(name='Universidad')
    model.X = Var(E, D, T, Z, within=Binary, initialize = 0) # Si el colaborador e en el escritorio d asiste el dia d en la zona z
    model.Y = Var(E, T, within=Binary, initialize = 0) # Si el colaborador e asiste el dia t
    model.Z = Var(G, T, within=Binary, initialize = 0) # Si el grupo g tiene primario el dia t
    model.J = Var(G, T, within=NonNegativeIntegers, initialize = 0) # Cantidad de zonas en las que está presente integrantes de cada grupo
    model.P = Var(G, Z, T, within = Binary, initialize = 0) # Si el grupo g tiene presencia (al menos un colaborador) en la zona z

    # Variables para penalizacion
    model.Penalizacion = Var(E, within=Binary, initialize=0) # 1 si el colaborador asiste 1 dia, 0 si asiste 2
    model.Penalizacion2 = Var(G, Z, T, within=Binary, initialize=0) # 1 si del grupo g en la zona z el dia t hay un solo colaborador, 0 EOC


    # Funcion objetivo
    def distribucion_rule(model):
        return sum(model.J[g, t] for g in G for t in T) + sum(model.Penalizacion[e] for e in E) + sum(model.Penalizacion2[g, z, t] for g in G for z in Z for t in T)  # Minimizar la cantidad de zonas y penalizaciones
    model.distribucion_rule = Objective(rule=distribucion_rule, sense=minimize)

    #RESTRICCIONES
    # Relación [X] con variable auxiliar Y
    def dias_presencialidad(model, e, t):
        return sum(model.X[e, d, t, z] for d in D for z in Z) == model.Y[e, t]
    model.dias_presencialidad = Constraint(E, T, rule=dias_presencialidad)

    # Días de presencialidad en el rango
    def dias_min(model, e):
        return sum(model.Y[e, t] for t in T) >= min - model.Penalizacion[e]
    model.dias_min = Constraint(E, rule=dias_min)

    def dias_max(model, e):
        return sum(model.Y[e, t] for t in T) <= max
    model.dias_max = Constraint(E, rule=dias_max)

    # Asignar solo un escritorio si va dicho dia
    def solo_un_escritorio(model, e, t):
        return sum(model.X[e, d, t, z] for d in D for z in Z) <= 1
    model.solo_un_escritorio = Constraint(E, T, rule=solo_un_escritorio)

    # Cada colaborador debe estar en un escritorio de cumplas con sus caracteristicas
    def colaborador_escritorio(model, e, d, t, z):
        return model.X[e, d, t, z] <= int((d in dr[e]))
    model.colaborador_escritorio = Constraint(E, D, T, Z, rule=colaborador_escritorio)

    ###################################################################################################
    # Un escritorio solo se le puede asignar a una persona
    def escritorio_unico(model, d, t):
        return sum(model.X[e, d, t, z] for e in E if d in dr[e] for z in Z if d in dz[z]) <= 1
    model.escritorio_unico = Constraint(D, T, rule=escritorio_unico)

    # No se debe asignar escritorios que no estan en esa zona #############################################
    def no_esta_en_zona(model, e, d, t, z):
        return model.X[e, d, t, z] <= int((d in dz[z]))
    model.no_esta_en_zona = Constraint(E, D, T, Z, rule=no_esta_en_zona)
    #######################################################################################################

    # Cada grupo tiene grupo primario una vez
    def grupo_primario(model, g):
        return sum(model.Z[g, t] for t in T) == 1
    model.grupo_primario = Constraint(G, rule=grupo_primario)

    # Los integrantes de cada grupo deben asistir al primario
    def asistencia_en_reunion(model, e, t, g):
        if e in e_g[g]:
            return model.Y[e, t] >= model.Z[g, t]
        else:
            return Constraint.Skip
    model.asistencia_en_reunion = Constraint(E, T, G, rule=asistencia_en_reunion)

    # No debe estar una persona "Sola" (Sola = no hay más colaboradores de su mismo equipo) en una zona
    def sola(model, z, g, t):
        return sum(model.X[e, d, t, z] for e in e_g[g] for d in dz[z]) >=  (model.P[g, z, t] * 2) - model.Penalizacion2[g, z, t]
    model.sola = Constraint(Z, G, T, rule=sola)

    def sola2(model, z, g, t):
        return sum(model.X[e, d, t, z] for e in e_g[g] for d in dz[z]) <=  model.P[g, z, t] * 10000000000
    model.sola2 = Constraint(Z, G, T, rule=sola2)

    # Relacionar las variables J y P
    def relacion_J_P(model, g, t):
        return model.J[g, t] == sum(model.P[g, z, t] for z in Z)
    model.relacion_J_P = Constraint(G, T, rule=relacion_J_P)

    def epsilon_restriccion(model):
        return sum(model.X[e,d,t,z] * int(t in di[e]) for e in E for d in D for t in T for z in Z) >= epsilon
    model.epsilon_restriccion = Constraint(rule=epsilon_restriccion)

    # Establecer límite de tiempo en segundos
    solver.options['seconds'] = tiempo_maximo  # Cambia este valor según tus necesidades

    # Establecer tolerancia de optimalidad
    solver.options['ratio'] = 0.01  # 1% de tolerancia de optimalidad
    # Criterios de parada: tiempo máximo (en segundos) y tolerancia de optimalidad
    solver.solve(
        model,
        tee=True,  # Muestra el log del solver
    )

    # Guardar resultados del modelo
    with open(f'Model_outputs_epsilon\\model_{instancia}.pkl', 'wb') as f:
        pickle.dump(model, f)


    # Guardar la hora actual
    hora_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Guardar la hora de finalización
    with open(f'Model_outputs_epsilon\\hora_finalizacion_{instancia}.txt', 'w') as f:
        f.write(hora_actual)

    del model
##########################################################################################################################
# Ejemplo de cargar modelo epsilon 
# Cargar model
instance = 'instance5'
carpeta = 'Model_outputs_epsilon'

model = cargar_modelo(instance, carpeta)

# print(f'FO: {value(model.distribucion_rule)}')


# Llamar a la función para importar datos
E, D, T, G, Z, dz, dr, e_g, di, max, min = importar_data(f'instances\\{instance}.json', imprimir=False)


df_resumen = resumen(E, D, T, Z, model, di, e_g)

df_reuniones = reuniones(G, T, model, e_g, D, Z)

df_programacion_primario = programacion_primario(model, G, T, e_g, D, Z)

df_programacion = programacion(model, E, D, T, Z, e_g)

preferencias(model, E, T, di)

# Imprimir valores de penalizacion
print("Penalizaciones asociadas a que van un solo dia de la semana:")
for e in E:
    if model.Penalizacion[e].value > 0:
        print(f"Colaborador: {e} | grupo: {next((k for k, lista in e_g.items() if e in lista), None)}")

print("\nPenalizaciones asociadas a que un grupo tiene un solo colaborador en una zona:")
# Imprimir valores de penalizacion2
for g in G:
    for z in Z:
        for t in T:
            if model.Penalizacion2[g, z, t].value > 0:
                print(f"Grupo {g} en zona {z} el día {t} tiene penalización un colaborador solo")

print(f'E: {len(E)} | T: {len(T)} | Z: {len(Z)} | D: {len(D)} | G: {len(G)} | ')



# Contar valores de la columna 'Empleado'
df_programacion['Empleado'].value_counts().sort_index(ascending=True)

############################################################################################################
# Ver las penalizaciones en los modelos F2
# Cargar modelo F2
instance2 = 'instance10'
carpeta2 = 'Model_outputs_F2'
model_F2 = cargar_modelo(instance2, carpeta2)

E, D, T, G, Z, dz, dr, e_g, di, max, min = importar_data(f'instances\\{instance2}.json', imprimir=False)

df_programacion_F2 = programacion(model_F2, E, D, T, Z, e_g)

preferencias(model_F2, E, T, di)


# Ver que empleados en que zona, que dia, de que grupo, esta solo

def verificacion_sola(model, Z, G, T):
    """
    Verifica si hay grupos con un solo colaborador en una zona en un día específico.
    retorna un texto con el grupo, la zona y el dia t.
    """
    contador = 0
    for z in Z:
        for g in G:
            for t in T:
                if sum(model.X[e, d, t, z].value for e in e_g[g] for d in dz[z]) == 1:
                    print(f"Grupo {g} en zona {z} el día {t} tiene penalización un colaborador solo")
                    contador += 1
                else:
                    pass
    return contador



def zonas_por_grupo_dia(model, G, Z, T, e_g, dz):
    """
    Devuelve un diccionario con la cantidad de zonas en las que está presente cada grupo cada día.
    """
    resultado = {}
    for g in G:
        for t in T:
            zonas_presentes = 0
            for z in Z:
                # Si algún colaborador del grupo g está presente en la zona z el día t
                if any(model.X[e, d, t, z].value == 1 for e in e_g[g] for d in dz[z]):
                    zonas_presentes += 1
            resultado[(g, t)] = zonas_presentes
            # print(f"Grupo {g} - Día {t}: {zonas_presentes} zonas")
            total_zonas = sum(resultado.values())
    return total_zonas

# Uso:

colabs_solos = verificacion_sola(model_F2, Z, G, T)

fo_f2 = zonas_por_grupo_dia(model_F2, G, Z, T, e_g, dz) + colabs_solos

print(f'FO: {fo_f2}  | {colabs_solos} penalizaciones')


#################################################################################################################
