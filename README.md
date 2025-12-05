# Lambda Ingestion - Asynchronous Purchase Pattern Analysis

Este proyecto implementa el componente de ingestión de datos dentro de la arquitectura de análisis de patrones de compra.

## Arquitectura

![Arquitectura del Sistema](diagram/architecture.png)

El sistema implementa un patrón de arquitectura **event-driven** completamente asíncrono para la ingestión de datos de compras. Los componentes principales son:

### Componentes

1. **Amazon S3 (Data Lake)**
   - Almacena los archivos CSV con datos de tickets de compra
   - Actúa como origen de datos y trigger del proceso de ingestión
   - Configurado con notificaciones de eventos para nuevos archivos

2. **Amazon SQS (Message Queue)**
   - Cola de mensajes que desacopla la carga de archivos del procesamiento
   - Recibe notificaciones automáticas cuando se suben archivos a S3
   - Garantiza procesamiento confiable mediante reintentos automáticos

3. **AWS Lambda (Ingestion Function)**
   - Función serverless que procesa los eventos de SQS
   - Descarga y parsea los archivos CSV desde S3
   - Transforma y carga los datos en Neo4j
   - Escala automáticamente según el volumen de mensajes

4. **EC2 con Neo4j (Graph Database)**
   - Base de datos de grafos que almacena los registros de tickets procesados
   - Optimizada para análisis de patrones y relaciones entre compras
   - Permite consultas complejas sobre relaciones entre productos, categorías y comportamientos de compra

### Flujo de Datos

1. **Upload**: El usuario sube un archivo `tickets.csv` al bucket de S3
2. **Event Notification**: S3 genera un evento y lo envía a la cola SQS
3. **Trigger**: Lambda se activa automáticamente al recibir mensajes de SQS
4. **Processing**: Lambda descarga el archivo, procesa los registros CSV
5. **Storage**: Los datos transformados se insertan en Neo4j como nodos y relaciones

## Descripción de la Función

La función Lambda (`ingestion/lambda_function.py`) está diseñada específicamente para manejar eventos de **SQS**.

### Flujo de Ejecución Detallado

1.  **Recepción del Mensaje**: La Lambda recibe un evento `SQSEvent` que contiene una lista de `Records`.
2.  **Parsing del Body**: Cada registro de SQS contiene un `body` que es una cadena JSON. Este `body` se parsea para extraer la estructura del evento de notificación de S3 (`S3Event`).
3.  **Extracción de Metadatos**: Se obtienen el nombre del `bucket` y la `key` (nombre del archivo) desde el evento de S3.
4.  **Descarga**: El archivo CSV se descarga desde S3 al almacenamiento temporal de la Lambda (`/tmp`).
5.  **Ingestión**: Se lee el archivo CSV y se insertan los registros en Neo4j como nodos y relaciones.

## Configuración

### Variables de Entorno

*   `NEO4J_URI`: URI de conexión a la instancia Neo4j en EC2 (ejemplo: `bolt://10.x.x.x:7687`)
*   `NEO4J_USER`: Usuario de Neo4j. Valor por defecto: `neo4j`
*   `NEO4J_PASSWORD`: Contraseña de Neo4j (debe configurarse como variable de entorno segura)

### Estructura de Datos (CSV)

El archivo de entrada debe tener las siguientes columnas:
`ticket_id`, `product`, `basket_id`, `timestamp`, `category`, `quantity`, `store`.

## Despliegue

El código fuente se encuentra en el directorio `ingestion/`.

1.  Asegúrate de que la Lambda tenga permisos IAM para:
    *   `sqs:ReceiveMessage`, `sqs:DeleteMessage`, `sqs:GetQueueAttributes` (para leer de la cola).
    *   `s3:GetObject` (para descargar el archivo).
    *   Acceso de red a la instancia EC2 con Neo4j (configurar Security Groups apropiadamente).
2.  Configura el **Trigger** de la Lambda para que sea la cola SQS correspondiente.
3.  Asegúrate de que la instancia EC2 con Neo4j esté corriendo y accesible desde la Lambda (mismo VPC o configuración de red apropiada).
