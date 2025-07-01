def importar_data(instancia, imprimir=True):
    import json

    '''
    Función para importar datos desde un archivo JSON para el modelo
    de optimizacion del reto ASOCIO 2025.
    
    instancia: str
        Ruta del archivo JSON que contiene los datos de la instancia.
    
    imprimir: bool
        Si es True, imprime la información extraída para verificación.
    '''

    # Cargar el archivo JSON
    with open(instancia, 'r') as file:
        data = json.load(file)

    # Extraer listas principales (Conjuntos)
    E = data['Employees']
    D = data['Desks']
    T = data['Days']
    G = data['Groups']
    Z = data['Zones']

    # Extraer diccionarios de relaciones (Parámetros)
    dz = data['Desks_Z']
    dr = data['Desks_E']
    e_g = data['Employees_G']
    di = data['Days_E']
    max = 3
    min = 2

    if imprimir:
        # Mostrar información extraída para verificación
        print("=== LISTAS EXTRAÍDAS ===")
        print(f"Employees: {E}")
        print(f"Desks: {D}")
        print(f"Days: {T}")
        print(f"Groups: {G}")
        print(f"Zones: {Z}")

        print("\n=== DICCIONARIOS DE RELACIONES ===")
        print(f"dz (Escritorios por Zona):")
        for zone, desks in dz.items():
            print(f"  {zone}: {desks}")

        print(f"\ne_g (Colaboradores por Grupo):")
        for group, employees in e_g.items():
            print(f"  {group}: {employees}")

        print(f"\ndr (Escritorios preferidos por Empleado) - Primeros 5:")
        for i, (employee, desks) in enumerate(dr.items()):
            if i < 5:  # Mostrar solo los primeros 5 para no saturar la salida
                print(f"  {employee}: {desks}")
            elif i == 5:
                print(f"  ... y {len(dr) - 5} Colaboradores más")
                break

        print(f"\nDays_E (Días disponibles por Empleado) - Primeros 5:")
        for i, (employee, days) in enumerate(di.items()):
            if i < 5:  # Mostrar solo los primeros 5 para no saturar la salida
                print(f"  {employee}: {days}")
            elif i == 5:
                print(f"  ... y {len(di) - 5} Colaboradores más")
                break

        print(f"\n=== RESUMEN ===")
        print(f"Total de Colaboradores: {len(E)}")
        print(f"Total de escritorios: {len(D)}")
        print(f"Total de días: {len(T)}")
        print(f"Total de grupos: {len(G)}")
        print(f"Total de zonas: {len(Z)}")
    
    return E, D, T, G, Z, dz, dr, e_g, di, max, min

def exportar_modelo(model, nombre_instancia):
    '''
    Función para exportar el modelo a un archivo pickle.
    model: ConcreteModel
        El modelo de optimización a exportar.
    nombre_instancia: str
        Nombre de la instancia para el archivo pickle.
    '''
    import pickle
    with open(f'Model_outputs\\model_{nombre_instancia}.pkl', 'wb') as f:
        pickle.dump(model, f)

def cargar_modelo(nombre_instancia, nombre_carpeta):
    import pickle
    import os
    '''
    Función para cargar un modelo desde un archivo pickle.
    nombre_instancia: str
        Nombre de la instancia para el archivo pickle.
    '''
    with open(f'{nombre_carpeta}\\model_{nombre_instancia}.pkl', 'rb') as f:
        model = pickle.load(f)
    return model

def resumen(E, D, T, Z, model, di, e_g):
    '''
    Función para generar un resumen de la eficiencia de los colaboradores,
    las zonas asignadas y los grupos a los que pertenecen.
    E: list
        Lista de Colaboradores.
    D: list
        Lista de escritorios.
    T: list
        Lista de días.
    Z: list
        Lista de zonas.
    model: ConcreteModel
        El modelo de optimización resuelto.
    di: dict
        Diccionario que relaciona Colaboradores con sus días preferidos.
    e_g: dict
        Diccionario que relaciona Colaboradores con sus grupos.
    '''
    import pandas as pd
    data_eficiencia = []

    for e in E:
        dias_asignados = [t for t in T if model.Y[e, t].value == 1]
        dias_preferidos = di[e]
        interseccion = set(dias_asignados).intersection(set(dias_preferidos))
        eficiencia = len(interseccion) / len(dias_asignados) if dias_asignados else 0

        data_eficiencia.append({
            "Empleado": e,
            "Días_Asignados": dias_asignados,
            "Días_Preferidos": dias_preferidos,
            "Eficiencia": round(eficiencia, 2)
        })

    df_eficiencia = pd.DataFrame(data_eficiencia)
    # print("\n=== Eficiencia por colaborador ===")
    # print(df_eficiencia)
    
    data_zonas = []

    for e in E:
        for t in T:
            for d in D:
                for z in Z:
                    if model.X[e, d, t, z].value == 1:
                        data_zonas.append({
                            "Empleado": e,
                            "Día": t,
                            "Escritorio": d,
                            "Zona": z
                        })

    df_zonas = pd.DataFrame(data_zonas)

    # Crear lista de filas a partir del diccionario e_g
    data_grupos = []

    for grupo, empleados in e_g.items():
        for empleado in empleados:
            data_grupos.append({
                'Grupo': grupo,
                'Empleado': empleado
            })

    # Crear DataFrame
    df_grupos = pd.DataFrame(data_grupos)


    df_final = df_eficiencia.merge(df_grupos, on="Empleado", how="left")
    df_final = df_final.merge(df_zonas.groupby("Empleado")["Zona"].unique().reset_index(), on="Empleado", how="left")
    df_final.rename(columns={"Zona": "Zonas_Asignadas"}, inplace=True)
    return df_final

def reuniones(G, T, model, e_g, D, Z):
    '''
    Función para generar un DataFrame con las reuniones programadas,
    incluyendo los grupos, días, zonas asignadas y colaboradores.
    G: list
        Lista de grupos.
    T: list
        Lista de días.
    model: ConcreteModel
        El modelo de optimización resuelto.
    e_g: dict
        Diccionario que relaciona Colaboradores con sus grupos.
    D: list
        Lista de escritorios.
    Z: list
        Lista de zonas.
    '''
    import pandas as pd
    data_reuniones = []

    for g in G:
        for t in T:
            if model.Z[g, t].value == 1:
                zonas_grupo = set()  # para almacenar las zonas únicas en que se ubican
                for e in e_g[g]:
                    for d in D:
                        for z in Z:
                            if model.X[e, d, t, z].value == 1:
                                zonas_grupo.add(z)
                data_reuniones.append({
                    "Grupo": g,
                    "Día_Reunión": t,
                    "Zonas_Asignadas": list(zonas_grupo),
                    "Colaboradores_Grupo": e_g[g]
                })

    df_reuniones = pd.DataFrame(data_reuniones)
    return df_reuniones

def preferencias(model, E, T, di):
    '''
    Función para calcular el porcentaje de coincidencia entre los días asignados
    de presencialidad y las preferencias de los colaboradores.
    model: ConcreteModel
        El modelo de optimización resuelto.
    E: list
        Lista de colaboradores.
    T: list
        Lista de días.
    di: dict
        Diccionario que relaciona Colaboradores con sus días preferidos.
    '''
    total_presencialidad = 0
    preferencias_satisfechas = 0

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

    # Mostrar resultados
    print("Preferencias satisfechas:", preferencias_satisfechas)
    print("Total de días de presencialidad asignados:", total_presencialidad)
    print(f"✅ Porcentaje de coincidencia con preferencias: {porcentaje:.2f}%")

def programacion_primario(model, G, T, e_g, D, Z):
    '''
    Función para generar un DataFrame con la programación de reuniones,
    incluyendo los grupos, días, empleados, zonas y escritorios asignados.
    model: ConcreteModel
        El modelo de optimización resuelto.
    G: list
        Lista de grupos.
    T: list
        Lista de días.
    e_g: dict
        Diccionario que relaciona Colaboradores con sus grupos.
    D: list
        Lista de escritorios.
    Z: list
        Lista de zonas.
    '''
    import pandas as pd
    data_escritorios_reunion = []

    for g in G:
        for t in T:
            if model.Z[g, t].value == 1:
                for e in e_g[g]:
                    for d in D:
                        for z in Z:
                            if model.X[e, d, t, z].value == 1:
                                data_escritorios_reunion.append({
                                    "Grupo": g,
                                    "Día_Reunión": t,
                                    "Empleado": e,
                                    "Zona": z,
                                    "Escritorio": d
                                })

    df_programacion_primario = pd.DataFrame(data_escritorios_reunion)
    return df_programacion_primario

def programacion(model, E, D, T, Z, e_g):
    '''
    Función para generar un DataFrame con la programación de los colaboradores,
    incluyendo los días, zonas y escritorios asignados.
    model: ConcreteModel
        El modelo de optimización resuelto.
    E: list
        Lista de colaboradores.
    D: list
        Lista de escritorios.
    T: list
        Lista de días.
    Z: list
        Lista de zonas.
    e_g: dict
        Diccionario que relaciona Colaboradores con sus grupos.
    '''
    import pandas as pd
    programacion = []

    for e in E:
        for d in D:
            for t in T:
                for z in Z:
                    if model.X[e, d, t, z].value == 1:
                        programacion.append({
                            "Empleado": e,
                            "Día": t,
                            "Zona": z,
                            "Escritorio": d
                        })
    # Crear DataFrame
    df_programacion = pd.DataFrame(programacion)
    data_grupos = []
    for grupo, empleados in e_g.items():
        for empleado in empleados:
            data_grupos.append({
                'Grupo': grupo,
                'Empleado': empleado
            })

    # Crear DataFrame
    df_grupos = pd.DataFrame(data_grupos)
    # Hacer merge con los grupos
    if 'df_grupos' in locals():
        df_programacion = df_programacion.merge(df_grupos, on="Empleado", how="left")
    return df_programacion

