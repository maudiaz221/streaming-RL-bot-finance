# Plataforma de Streaming en Tiempo Real para Mercado de Criptomonedas con Aprendizaje por Refuerzo

---

**Autores:**

| Nombre | Clave Única |
|--------|-------------|
| Jorge Esteban Ramírez Sashida | 201530 |
| Mauricio Diaz Villarreal | 200854 |

**Curso:** Arquitectura de Computadoras  
**Fecha:** Noviembre 2024

---

## Resumen

Este proyecto presenta el diseño e implementación de una plataforma de procesamiento de datos en streaming para el mercado de criptomonedas, integrando tecnologías de big data como Apache Spark Structured Streaming y Amazon Kinesis, junto con un modelo de aprendizaje por refuerzo (RL) basado en el algoritmo PPO (Proximal Policy Optimization). La arquitectura propuesta permite capturar datos en tiempo real desde el WebSocket de Binance, procesarlos mediante indicadores técnicos financieros, generar señales de trading automatizadas y visualizar los resultados a través de dashboards interactivos. El sistema está diseñado para procesar más de 4,096 mensajes por segundo con una latencia end-to-end de aproximadamente 20-30 segundos, demostrando la viabilidad de aplicar técnicas de machine learning en entornos de streaming financiero.

---

## 1. Introducción y Justificación

El mercado de criptomonedas se caracteriza por su alta volatilidad y operación continua las 24 horas del día, los 7 días de la semana, generando enormes volúmenes de datos en tiempo real. Esta dinámica presenta tanto desafíos como oportunidades para el desarrollo de sistemas automatizados de análisis y toma de decisiones. La capacidad de procesar estos flujos de datos en tiempo real, calcular indicadores técnicos y generar predicciones de trading representa una ventaja competitiva significativa en el ámbito del trading algorítmico [1].

El presente proyecto surge de la necesidad de implementar una arquitectura escalable y tolerante a fallos que permita capturar, procesar y analizar datos de criptomonedas en streaming. La justificación técnica radica en la convergencia de tres disciplinas fundamentales: (1) procesamiento de datos en streaming mediante Apache Spark, (2) arquitecturas cloud-native con servicios gestionados de AWS, y (3) aprendizaje por refuerzo para la generación de señales de trading. Esta integración permite explorar casos de uso reales en finanzas cuantitativas mientras se aplican conceptos de sistemas distribuidos y machine learning [2].

**Objetivos del Proyecto:**
- Diseñar e implementar un pipeline de ingesta de datos en tiempo real desde el WebSocket de Binance hacia Amazon Kinesis Data Streams.
- Desarrollar un procesador de streaming con PySpark que calcule indicadores técnicos (RSI, MACD, Bandas de Bollinger, medias móviles) y ejecute inferencia de un modelo de aprendizaje por refuerzo.
- Construir dashboards de visualización en tiempo real utilizando Next.js con TradingView Lightweight Charts, y un dashboard de predicciones con Streamlit.
- Demostrar la capacidad del sistema para procesar más de 4,096 puntos de datos por segundo, cumpliendo con los requerimientos de throughput del curso.

---

## 2. Obtención y Método de Captura de Datos

La fuente de datos principal es la API WebSocket pública de Binance, el exchange de criptomonedas con mayor volumen de operaciones a nivel mundial. El cliente WebSocket, implementado en Python utilizando la librería `websocket-client`, se conecta al endpoint `wss://stream.binance.com:9443/stream` para suscribirse a múltiples streams simultáneamente. Actualmente, el sistema captura datos de trades (transacciones individuales) y klines (velas OHLCV de 1 minuto) para los pares BTCUSDT, ETHUSDT y BNBUSDT. Cada mensaje recibido incluye información como precio, volumen, timestamp y tipo de evento, y se normaliza agregando metadatos del cliente antes de enviarse a Kinesis [3].

La cadencia de datos depende de la actividad del mercado: durante períodos de alta volatilidad, Bitcoin puede generar cientos de trades por segundo, mientras que en períodos de calma la frecuencia disminuye considerablemente. El sistema implementa un mecanismo de batching que agrupa hasta 100 mensajes o espera un máximo de 1 segundo antes de enviar un lote a Kinesis, optimizando el uso del ancho de banda y reduciendo costos de AWS. Además, el cliente incluye reconexión automática con backoff exponencial (máximo 5 intentos) para garantizar la continuidad del servicio ante desconexiones temporales de la red o del exchange [4].

---

## 3. Características del Dashboard y su Rol en la Definición del Modelo

El dashboard principal, desarrollado con Next.js 14 y React 18, proporciona una interfaz de usuario en tiempo real que consume directamente el WebSocket de Binance para mostrar gráficos de velas (candlestick), trades en vivo, estadísticas de mercado y métricas de conexión. La librería TradingView Lightweight Charts se utiliza para renderizar gráficos financieros profesionales con soporte para zoom, pan y crosshair interactivo. El diseño adopta una estética "cyberpunk" con colores neón y efectos de resplandor, diferenciándose de interfaces genéricas. Los componentes principales incluyen: `PriceDisplay` para precios actuales con indicador de cambio, `CryptoChart` para gráficos OHLCV, `LiveTrades` para el feed de transacciones, y `CryptoStats` para métricas agregadas como volumen 24h y variación porcentual [5].

La información visualizada en el dashboard contribuye directamente a la definición del espacio de estados del modelo de aprendizaje por refuerzo. Los indicadores técnicos mostrados (precio actual, momentum, volatilidad, volumen relativo, RSI, MACD y posición en Bandas de Bollinger) constituyen las 13 features del vector de observación que alimenta al agente PPO. Al observar cómo estos indicadores se comportan en tiempo real, se validó que el conjunto de features seleccionado captura adecuadamente los patrones de mercado relevantes para la toma de decisiones de trading. Adicionalmente, se planea desarrollar un segundo dashboard con Streamlit enfocado en mostrar las predicciones del modelo (señales BUY/SELL/HOLD) y el rendimiento histórico del portafolio simulado.

---

## 4. Arquitectura y Módulos de Spark y Kafka (Kinesis)

La arquitectura del sistema sigue un patrón de streaming de eventos que puede describirse en cinco capas principales. La **capa de ingesta** consiste en un productor Python que se ejecuta en una instancia EC2 y captura datos del WebSocket de Binance, enviándolos a Amazon Kinesis Data Streams mediante la librería boto3. Kinesis actúa como el equivalente a Apache Kafka en el ecosistema AWS, proporcionando un buffer durable y ordenado para los mensajes con retención configurable de 24 a 168 horas. El stream está configurado con 1-2 shards, donde cada shard soporta 1 MB/s de entrada y 2 MB/s de salida, permitiendo un throughput de más de 4,096 mensajes por segundo [6].

La **capa de procesamiento** utiliza PySpark Structured Streaming ejecutándose sobre Amazon EMR (Elastic MapReduce). El job de Spark lee continuamente desde Kinesis utilizando el conector `spark-sql-kinesis_2.12:3.4.0`, procesa los datos en micro-batches de 10 segundos, y aplica transformaciones que incluyen: parsing de JSON, cálculo de medias móviles (5min, 15min, 1h), RSI con período de 14 barras, MACD (12, 26, 9), Bandas de Bollinger (20 períodos, 2σ), y detección de anomalías mediante z-score. Las operaciones de ventana se implementan tanto con ventanas deslizantes (sliding windows) como ventanas de caída (tumbling windows), utilizando watermarks de 30 segundos para manejar datos tardíos [7].

La **capa de almacenamiento** utiliza Amazon S3 como data lake, donde los datos procesados se escriben en formato Parquet particionado por símbolo (`S=BTCUSDT/date=2024-01-15/`). Kinesis Firehose se utiliza adicionalmente para almacenar los datos crudos como respaldo. Los checkpoints de Spark también se persisten en S3 para garantizar tolerancia a fallos y recuperación ante reinicio del job. Finalmente, la **capa de inferencia** carga el modelo PPO entrenado (almacenado en S3) y ejecuta predicciones en cada micro-batch utilizando pandas UDFs, generando señales de trading que se escriben junto con los indicadores técnicos.

---

## 5. Interfaz GUI de Spark (Spark UI)

La interfaz gráfica de Spark, accesible por defecto en `http://localhost:4040` durante la ejecución del job, proporciona herramientas esenciales para el monitoreo y debugging de aplicaciones de streaming. Las pestañas principales incluyen: **Jobs** para visualizar el DAG (Directed Acyclic Graph) de ejecución y el progreso de cada stage; **Stages** para identificar cuellos de botella en operaciones específicas como shuffles o transformaciones; **Storage** para monitorear el uso de caché y persistencia de RDDs/DataFrames; y **Streaming** específicamente para aplicaciones de Structured Streaming, mostrando métricas como input rate, processing rate, batch duration y la cola de batches pendientes [8].

Para este proyecto, la Spark UI aporta visibilidad crítica en varios aspectos: (1) permite verificar que el throughput de procesamiento (>4,096 msg/s) se mantiene por encima de la tasa de entrada de Kinesis; (2) facilita la identificación de skew en particiones, especialmente relevante cuando un símbolo como Bitcoin genera significativamente más tráfico que otros; (3) ayuda a optimizar el uso de memoria y detectar posibles memory leaks en operaciones stateful como los cálculos de ventana; y (4) proporciona información sobre el lag del streaming, permitiendo ajustar el trigger interval o el número de ejecutores si el sistema comienza a retrasarse respecto a los datos entrantes.

---

## 6. Resultados Esperados y Utilidad

Los resultados principales del proyecto se materializan en tres entregables concretos. Primero, un **pipeline de datos en tiempo real** capaz de ingestar, procesar y almacenar datos de criptomonedas con una latencia end-to-end de 20-30 segundos, generando datasets de alta calidad enriquecidos con indicadores técnicos. Segundo, un **modelo de trading basado en PPO** entrenado con datos históricos que genera señales de BUY/SELL/HOLD con scores de confianza, implementando un espacio de estados de 13 dimensiones y recompensas basadas en cambios de portafolio ajustados por ratio de Sharpe. Tercero, **dashboards interactivos** que permiten visualizar tanto los datos en tiempo real como las predicciones del modelo [9].

La utilidad práctica de estos resultados se extiende a múltiples dominios. Desde una perspectiva educativa, el proyecto demuestra la integración de tecnologías de big data (Spark, Kinesis), cloud computing (AWS), y machine learning (stable-baselines3) en un caso de uso realista. Desde una perspectiva de negocio, la arquitectura podría adaptarse para implementar sistemas de trading algorítmico en producción, sistemas de alertas para traders discrecionales, o herramientas de backtesting en tiempo real. La modularidad del diseño permite escalar horizontalmente añadiendo más símbolos, incorporar nuevos indicadores técnicos, o reemplazar el modelo PPO por otras arquitecturas de RL como A2C, DQN o SAC.

---

## 7. Implementación en AWS y Alternativa con Google Colab

### Implementación Actual en AWS

La implementación en AWS utiliza los siguientes servicios gestionados:

| Componente | Servicio AWS | Configuración |
|------------|--------------|---------------|
| Productor WebSocket | EC2 (t3.small) / ECS Fargate | Python 3.11, 512 MB RAM |
| Buffer de Streaming | Kinesis Data Streams | 1-2 shards, 24h retención |
| Almacenamiento Raw | Kinesis Firehose → S3 | Buffer 5min/5MB |
| Procesamiento | EMR (m5.xlarge) | Spark 3.4, 4 vCPU, 16 GB |
| Data Lake | S3 | Parquet, lifecycle policies |
| Dashboard | EC2 + Next.js | Node.js 18 |

El costo estimado mensual es de $140-220 USD, optimizable mediante instancias Spot para EMR y políticas de lifecycle en S3.

### Implementación Alternativa con Google Colab

Para implementar este proyecto utilizando Google Colab como alternativa gratuita, se requieren las siguientes adaptaciones:

1. **Ingesta de Datos**: Reemplazar Kinesis por Apache Kafka ejecutándose en un servidor externo (ej. Confluent Cloud tier gratuito) o utilizar archivos CSV/Parquet precargados en Google Drive para simular el streaming.

2. **Procesamiento**: PySpark puede ejecutarse directamente en Colab instalando `pyspark` via pip. Sin embargo, Colab no soporta procesos de larga duración, por lo que el procesamiento sería en batch simulando micro-batches.

3. **Modelo RL**: El entrenamiento del modelo PPO con stable-baselines3 funciona nativamente en Colab, aprovechando GPUs gratuitas para acelerar el entrenamiento.

4. **Dashboard**: Streamlit puede ejecutarse en Colab mediante túneles ngrok, aunque con limitaciones de tiempo de sesión.

### Diagrama de Arquitectura AWS

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              ARQUITECTURA AWS                                │
└─────────────────────────────────────────────────────────────────────────────┘

                        ┌──────────────────┐
                        │   Binance API    │
                        │   (WebSocket)    │
                        └────────┬─────────┘
                                 │ wss://stream.binance.com
                                 ▼
                        ┌──────────────────┐
                        │  EC2 Producer    │
                        │  (Python Client) │
                        └────────┬─────────┘
                                 │ boto3.put_records()
                    ┌────────────┴────────────┐
                    ▼                         ▼
          ┌──────────────────┐      ┌──────────────────┐
          │  Kinesis Data    │      │ Kinesis Firehose │
          │    Streams       │      │   (Backup)       │
          │ (crypto-market)  │      │                  │
          └────────┬─────────┘      └────────┬─────────┘
                   │                         │
                   │                         ▼
                   │                ┌──────────────────┐
                   │                │   S3 Bucket      │
                   │                │  (raw-data/)     │
                   ▼                └──────────────────┘
          ┌──────────────────┐
          │   Amazon EMR     │
          │  (Spark 3.4)     │
          │                  │
          │ ┌──────────────┐ │
          │ │ Spark Driver │ │
          │ │              │ │
          │ │ - Read       │ │
          │ │   Kinesis    │ │
          │ │ - Calculate  │ │
          │ │   Indicators │ │
          │ │ - RL Model   │ │
          │ │   Inference  │ │
          │ └──────────────┘ │
          └────────┬─────────┘
                   │
                   ▼
          ┌──────────────────┐
          │   S3 Bucket      │
          │                  │
          │ ├─ processed-    │
          │ │  data/         │
          │ │  (Parquet)     │
          │ │                │
          │ ├─ checkpoints/  │
          │ │                │
          │ └─ models/       │
          │    (PPO .zip)    │
          └────────┬─────────┘
                   │
        ┌──────────┴──────────┐
        ▼                     ▼
┌──────────────────┐  ┌──────────────────┐
│   EC2 Instance   │  │   EC2 Instance   │
│                  │  │                  │
│  ┌────────────┐  │  │  ┌────────────┐  │
│  │  Next.js   │  │  │  │  Streamlit │  │
│  │ Dashboard  │  │  │  │ Predictor  │  │
│  │            │  │  │  │            │  │
│  │ - Charts   │  │  │  │ - Daily    │  │
│  │ - Trades   │  │  │  │   Forecast │  │
│  │ - Stats    │  │  │  │ - Model    │  │
│  │            │  │  │  │   Metrics  │  │
│  └────────────┘  │  │  └────────────┘  │
└──────────────────┘  └──────────────────┘
        │                     │
        └──────────┬──────────┘
                   ▼
          ┌──────────────────┐
          │   Usuario Final  │
          │   (Browser)      │
          └──────────────────┘
```

---

## Referencias Bibliográficas

[1] A. Géron, "Hands-On Machine Learning with Scikit-Learn, Keras, and TensorFlow," 3rd ed. O'Reilly Media, 2022. ISBN: 978-1098125974.

[2] M. Zaharia et al., "Structured Streaming: A Declarative API for Real-Time Applications in Apache Spark," in Proc. ACM SIGMOD, 2018, pp. 601-613. DOI: 10.1145/3183713.3190664

[3] Binance, "Binance WebSocket Streams Documentation," 2024. [En línea]. Disponible: https://binance-docs.github.io/apidocs/spot/en/#websocket-market-streams

[4] Amazon Web Services, "Amazon Kinesis Data Streams Developer Guide," 2024. [En línea]. Disponible: https://docs.aws.amazon.com/streams/latest/dev/introduction.html

[5] TradingView, "Lightweight Charts Documentation," 2024. [En línea]. Disponible: https://tradingview.github.io/lightweight-charts/

[6] Apache Spark, "Structured Streaming Programming Guide," v3.4.0, 2023. [En línea]. Disponible: https://spark.apache.org/docs/latest/structured-streaming-programming-guide.html

[7] J. Schulman et al., "Proximal Policy Optimization Algorithms," arXiv:1707.06347, 2017. [En línea]. Disponible: https://arxiv.org/abs/1707.06347

[8] Apache Spark, "Monitoring Spark Applications," v3.4.0, 2023. [En línea]. Disponible: https://spark.apache.org/docs/latest/monitoring.html

[9] Stable-Baselines3, "PPO Algorithm Documentation," 2024. [En línea]. Disponible: https://stable-baselines3.readthedocs.io/en/master/modules/ppo.html

[10] **Consultas a LLM (Claude/ChatGPT)**: Se utilizaron modelos de lenguaje para asistencia en la redacción de código, debugging y estructuración de la arquitectura. Enlace de referencia: https://claude.ai (Consultas realizadas entre octubre-noviembre 2024).

---

*Documento elaborado para el curso de Arquitectura de Computadoras - Noviembre 2024*

