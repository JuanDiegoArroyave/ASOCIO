
## Autores

- Juan Diego Arroyave Murillo  |  juan.arroyave14@udea.edu.co  |  linkedin.com/in/juan-diego-arroyave-murillo-41ba08302
- Sebastian Sanchez Alvarez  |  sebastian.sanchez9@udea.edu.co  |  linkedin.com/in/sebastián-sánchez-álvarez-919018237
- Tatiana Ortiz Rojas  |  tatiana.ortizr1@udea.edu.co  |  linkedin.com/in/tatiana-ortiz-rojas-419b0b26b

## Licencia

Este proyecto está licenciado bajo los términos de la **Apache License 2.0**.  
Puedes ver los detalles completos en el archivo [LICENSE](./LICENSE).

## Optimizador CBC

Para este proyecto se hizo uso del optimizador CBC desarrollado por Coin-or el release Cbc-releases.2.10.12-windows-2022-msvs-v17-Release-x64 el cual se encuentra en el repositorio https://github.com/coin-or/Cbc/releases

## requerements.txt

Contiene las librerias necesarias que se deben instalar para correr el sistema

## Funciones.py

Contiene las funciones desarrolladas para realizar calculos y metricas de los modelos, exportacion e importacion de los modelos.

## Funciones_modelos.py

Contiene los modelos F1 y F2 empaquetados en funciones

## Script_ejecucion_usuario.py y Salidas_usuario

Hace uso de los modelos empaquetados para crear la experiencia de usuario, los resultados de las visualizaciones y el excel con la programacion se exportan en la carpteta Salidas_usuario

## Instances

Contiene las instancias con las que es posible correr los diferentes modelos

## Despliegue.py y Model_outputs

Despliegue del modelo F1 crudo (solo intereses de la universidad), todos los resultados de este modelo son exportados en la carpeta Model_outputs

## Despliegue_epsilon.py, Model_outputs_epsilon y Model_outputs_F2

Despliegue del modelo F2 crudo (solo intereses de la universidad) y el modelo epsilon. Los resultados de ambos modelos se exportan hacia las carpetas Model_outputs_F2 y Model_outputs_epsilon respectivamente
