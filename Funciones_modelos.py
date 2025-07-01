def resolver_modelo_F2(instance, tiempo_limite, tolerancia=0.01, solver_path ='Optimizer\\Cbc-releases.2.10.12-windows-2022-msvs-v17-Release-x64\\bin\\cbc.exe'):
    '''
    Resuelve el modelo que optimiza los intereses de los colaboradores
    '''
    from Funciones import importar_data
    import pyomo
    from pyomo.environ import ConcreteModel, Var, Binary, Objective, maximize, Constraint
    from pyomo.opt import SolverFactory

    solver = SolverFactory('cbc', executable=solver_path)
    instancia = f'instances\\{instance}.json'

    E, D, T, G, Z, dz, dr, e_g, di, max, min = importar_data(instancia, imprimir=False)

    model = ConcreteModel(name='Colaboradores')
    model.X = Var(E, D, T, Z, within=Binary, initialize=0)
    model.Y = Var(E, T, within=Binary, initialize=0)
    model.Z = Var(G, T, within=Binary, initialize=0)

    def satisfaccion_rule(model):
        return sum(
            model.X[e, d, t, z] * int(t in di[e])
            for e in E
            for d in D
            for t in T
            for z in Z
        )
    model.satisfaccion = Objective(rule=satisfaccion_rule, sense=maximize)

    def dias_presencialidad(model, e, t):
        return sum(model.X[e, d, t, z] for d in D for z in Z) == model.Y[e, t]
    model.dias_presencialidad = Constraint(E, T, rule=dias_presencialidad)

    def dias_min(model, e):
        return sum(model.Y[e, t] for t in T) >= min
    model.dias_min = Constraint(E, rule=dias_min)

    def dias_max(model, e):
        return sum(model.Y[e, t] for t in T) <= max
    model.dias_max = Constraint(E, rule=dias_max)

    def solo_un_escritorio(model, e, t):
        return sum(model.X[e, d, t, z] for d in D for z in Z) <= 1
    model.solo_un_escritorio = Constraint(E, T, rule=solo_un_escritorio)

    def colaborador_escritorio(model, e, d, t, z):
        return model.X[e, d, t, z] <= int((d in dr[e]))
    model.colaborador_escritorio = Constraint(E, D, T, Z, rule=colaborador_escritorio)

    def escritorio_unico(model, d, t):
        return sum(model.X[e, d, t, z] for e in E if d in dr[e] for z in Z if d in dz[z]) <= 1
    model.escritorio_unico = Constraint(D, T, rule=escritorio_unico)

    def no_esta_en_zona(model, e, d, t, z):
        return model.X[e, d, t, z] <= int((d in dz[z]))
    model.no_esta_en_zona = Constraint(E, D, T, Z, rule=no_esta_en_zona)

    def grupo_primario(model, g):
        return sum(model.Z[g, t] for t in T) == 1
    model.grupo_primario = Constraint(G, rule=grupo_primario)

    def asistencia_en_reunion(model, e, t, g):
        if e in e_g[g]:
            return model.Y[e, t] >= model.Z[g, t]
        else:
            return Constraint.Skip
    model.asistencia_en_reunion = Constraint(E, T, G, rule=asistencia_en_reunion)

    solver.options['seconds'] = tiempo_limite
    solver.options['ratio'] = tolerancia

    solver.solve(model, tee=False)

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

    return preferencias_satisfechas, porcentaje

def resolver_modelo_F1(instance, satisfaccion_deseada, porcentaje, preferencias_satisfechas, tiempo_limite, tolerancia=0.01, solver_path='Optimizer\\Cbc-releases.2.10.12-windows-2022-msvs-v17-Release-x64\\bin\\cbc.exe'):
    '''
    Resuelve el modelo que optimiza los intereses de la Universidad con epsilon restriccion de 
    satisfaccion de los colaboradores
    '''
    from Funciones import importar_data, programacion, reuniones, preferencias
    import pyomo
    from pyomo.environ import ConcreteModel, Var, Binary, Objective, Constraint, NonNegativeIntegers, minimize
    from pyomo.opt import SolverFactory

    # Calculo del epsilon
    epsilon = round((preferencias_satisfechas / (porcentaje/100)) * satisfaccion_deseada, 0)
    
    # Configuracion de solver
    solver = SolverFactory('cbc', executable=solver_path)
    instancia = f'instances\\{instance}.json'

    # Llamar a la función para importar datos
    E, D, T, G, Z, dz, dr, e_g, di, max, min = importar_data(instancia, imprimir=False)

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
    solver.options['seconds'] = tiempo_limite

    # Establecer tolerancia de optimalidad
    solver.options['ratio'] = tolerancia
    # Criterios de parada: tiempo máximo (en segundos) y tolerancia de optimalidad
    solver.solve(
        model,
        tee=False,  # No muestra el log del solver
    )
    
    preferencias(model, E, T, di)
    
    df_programacion = programacion(model, E, D, T, Z, e_g)
    df_reuniones = reuniones(G, T, model, e_g, D, Z)

    return df_programacion, df_reuniones