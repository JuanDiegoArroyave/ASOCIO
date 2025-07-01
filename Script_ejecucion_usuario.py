from Funciones_modelos import *
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import os

os.system('cls')  # Para Windows

# Mostrar los nombres de los archivos existente en la carpeta instances
# Mostrar los nombres de los archivos existente en la carpeta instances

print('Bienvenido al programa de ejecucion de programacion semanal de la universidad' \
'\nlas configuraciones (instancias) disponible para planear son:')
archivos = os.listdir('instances')
for archivo in archivos:
    print(archivo)

print('\nIngrese el nombre de la configuracion que desea correr' \
'\nEjemplo: Si desea correr instance1.json, Ingrese instance1')
instancia_a_correr = str(input('\nCONFIGURACION: '))

while True:
    if f'{instancia_a_correr}.json' not in archivos:
        print('Configuracion elegida no valida')
        print('\nIngrese el nombre de la configuracion que desea correr' \
            '\nEjemplo: Si desea correr instance1.json, Ingrese instance1')
        instancia_a_correr = str(input('\nCONFIGURACION: '))
    else:
        os.system('cls')
        break

# Tiempos usados en las simulaciones
tiempos_recomendados = {'instance1':3600, 'instance2':3600, 'instance3':3600,
                        'instance4':3600, 'instance5':3600, 'instance6':3600,
                        'instance7':5400, 'instance8':7200, 'instance9':9000,
                        'instance10':10800,}

# Verificar si la instancia seleccionada se encuentra dentro de las usadas en las silulaciones
if instancia_a_correr in list(tiempos_recomendados.keys()):
    print('Defina el tiempo maximo (en horas) de corrida para la configuracion selecionada' \
      f'\npara {instancia_a_correr} se recomienda {tiempos_recomendados[instancia_a_correr]/3600} horas')

else:
    print('Defina el tiempo maximo (en horas) de corrida para la configuracion selecionada' \
      f'\npara {instancia_a_correr} no se tiene tiempo registrado')

t_max_user = float(input('TIEMPO MAXIMO DE EJECUCION: ')) * 3600 # Tiempo maximo de ejecucion definido por el usuario (en segundos)


print('Configurando modelo...')
preferencias_satisfechas, porcentaje = resolver_modelo_F2(instancia_a_correr, 300) # Encontrar la maxima satisfaccion de los colaboradores para dicha instancia
print('Modelo configurado' \
    f'\nPara la configuracion seleccionada, se tiene una satisfaccion maxima de los colaboradores de: {round(porcentaje, 2)}%' \
    '\nIngrese la satisfaccion minima que usted espera que tengan sus colaboradores basado en las preferencias de asistencia presencial' \
    '\nEjemplo: si desea que la satisfaccion minima sea 67.89%, ingrese 67.89')
satis_min_esperada = float(input('SATISFACCION MINIMA ESPERADA: ')) / 100

# La satisfaccion minima esperada no puede ser mayor a la satisfaccion maxima encontrada
while True:
    if (satis_min_esperada*100) > round(porcentaje, 2):
        print(f'La satisfaccion ingresada no puede ser mayor a la satisfaccion maxima ({round(porcentaje, 2)}%)')
        satis_min_esperada = float(input('INGRESE NUEVAMENTE LA SATISFACCION MINIMA ESPERADA: ')) /100
    else:
        os.system('cls')
        print('Modelo correctamente configurado')
        break



print('Corriendo modelo...')
df_programacion, df_reuniones = resolver_modelo_F1(instancia_a_correr, satis_min_esperada, porcentaje, preferencias_satisfechas, tiempo_limite=t_max_user)

# Asegurarse de que los días están estandarizados
df_programacion["Día"] = df_programacion["Día"].str.strip().str.capitalize()

# Crear carpeta para guardar los gráficos
carpeta_graficos = "Salidas_usuario"
os.makedirs(carpeta_graficos, exist_ok=True)

# Definir orden deseado de los días
orden_dias = ["L", "Ma", "Mi", "J", "V"]

# # Inicializar el escritor de Excel
# excel_filename = "programacion_completa.xls"
# excel_writer = pd.ExcelWriter("programacion_completa.xlsx", engine="openpyxl")

excel_filename = os.path.join(carpeta_graficos, "programacion_completa.xlsx")
excel_writer = pd.ExcelWriter(excel_filename, engine="openpyxl")


# Recorrer los días en el orden deseado
for dia in orden_dias:
    df_dia = df_programacion[df_programacion["Día"] == dia]

    if df_dia.empty:
        continue  # Saltar si no hay datos para ese día

    # --- Guardar hoja en Excel ---
    df_dia.to_excel(excel_writer, sheet_name=dia, index=False)

    # --- Crear gráfico ---
    #pivot_table = df_dia.pivot_table(index="Empleado", columns="Escritorio", values="Zona", aggfunc='first')

    pivot_table = df_dia.pivot_table(index="Empleado", columns="Escritorio", values="Zona", aggfunc='first')

    # Ordenar empleados y escritorios numéricamente
    pivot_table = pivot_table.reindex(
        sorted(pivot_table.index, key=lambda x: int(x[1:])), axis=0
    )
    pivot_table = pivot_table.reindex(
        sorted(pivot_table.columns, key=lambda x: int(x[1:])), axis=1
    )

    plt.figure(figsize=(10, 6))
    sns.heatmap(pivot_table.isna(), cbar=False, cmap="Greys", linewidths=0.5, linecolor='gray')

    # Anotar zonas dentro del mapa
    for i, row in enumerate(pivot_table.index):
      for j, col in enumerate(pivot_table.columns):
          zona = pivot_table.loc[row, col]
          if pd.notna(zona):
              # Obtener grupo desde df_dia
              grupo = df_dia[df_dia["Empleado"] == row]["Grupo"].iloc[0]
              texto = f"{grupo} - {zona}"  
              plt.text(j + 0.5, i + 0.5, texto, ha='center', va='center', fontsize=6)

    plt.title(f"Asignaciones - Día: {dia}")
    plt.xlabel("Escritorio")
    plt.ylabel("Empleado")
    plt.tight_layout()

    # Guardar cada imagen en la carpeta
    ruta_guardado = os.path.join(carpeta_graficos, f"programacion_dia_{dia}.png")
    plt.savefig(ruta_guardado)
    plt.close()

########################################################################

# Convertir listas a strings plans
df_reuniones = df_reuniones.copy()

for col in df_reuniones.columns:
    df_reuniones[col] = df_reuniones[col].apply(
        lambda x: ', '.join(x) if isinstance(x, list) else x
    )

#Reuniones como una hoja adicional
df_reuniones.to_excel(excel_writer, sheet_name="Grupo primario", index=False)

#Exportar el archivo de Excel
excel_writer.close()

print('Ejecucion finalizada. Puedes revisar los resultados en la carpeta Salidas_usuario')
