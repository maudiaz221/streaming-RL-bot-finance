# Binance Spark Processor

## ¿Qué hace?

Sistema de streaming en tiempo real que recolecta datos de criptomonedas desde Binance, los procesa con PySpark agregando características de series temporales, y los almacena en S3 para análisis de trading.

## Arquitectura

```
EC2 Instance
    └── Docker Compose
        └── Contenedor Python
            ├── WebSocket Client → Binance API (datos en vivo)
            ├── PySpark Processor → Ingeniería de características
            └── S3 Writer → Almacenamiento en AWS S3
```

### Componentes

1. **WebSocket Client** (`websocket_client.py`)
   - Conecta al stream de Binance WebSocket
   - Recibe klines (velas) de 1 minuto para múltiples pares de trading
   - Filtra solo velas cerradas (ignora velas en progreso)
   - Alimenta una cola de mensajes

2. **Spark Processor** (`spark_processor.py`)
   - Procesa datos con PySpark en batch
   - Genera características técnicas:
     - Returns y cambios de precio
     - Medias móviles (MA 5, 10, 20)
     - Volatilidad (rolling std)
     - Momentum de precio
     - Features de volumen
   - Usa window functions para análisis temporal por símbolo

3. **S3 Writer** (`s3_writer.py`)
   - Escribe datos en formato Parquet comprimido (Snappy)
   - Organiza archivos con particionamiento temporal (año/mes/día/hora)
   - Guarda dos versiones:
     - **Raw**: Datos originales sin procesar
     - **Clean**: Datos con características engineered

4. **Orchestrator** (`main.py`)
   - Coordina todos los componentes
   - Agrupa mensajes por minuto (todas las monedas del mismo minuto)
   - Pipeline: WebSocket → PySpark → S3 (raw + processed)
   - Maneja reconexión y shutdown graceful

### Flujo de Datos

```
Binance WebSocket
    ↓ (streaming klines)
Message Queue
    ↓ (batch por minuto)
Spark Processor
    ↓ (feature engineering)
S3 Bucket
    ├── raw/2024/12/01/klines_20241201_143000.parquet
    └── clean/2024/12/01/klines_20241201_143000.parquet
```

## Deployment

El sistema corre en una instancia EC2 usando Docker Compose:

- **Image**: Construida desde `Dockerfile` con Python + PySpark
- **Variables**: Configuradas en `.env` (AWS credentials, símbolos, bucket S3)
- **Ports**: 4040 expuesto para Spark UI
- **Volumes**: Logs persistentes en el host
- **Restart**: Automático en caso de fallo

### Ejecución

```bash
# Levantar el servicio
docker-compose up -d

# Ver logs
docker-compose logs -f

# Monitorear Spark UI
http://<EC2_IP>:4040
```

## Estructura de Datos

### Raw Data
Datos originales del WebSocket de Binance (JSON convertido a Parquet).

### Processed Data (Features)
- **Básicos**: timestamp, symbol, OHLCV
- **Precio**: price_change, price_change_pct, log_return
- **Moving Averages**: ma_5, ma_10, ma_20
- **Volatilidad**: volatility_10
- **Volumen**: volume_ma_5, volume_change_pct
- **Momentum**: momentum_5, momentum_10
- **Spread**: hl_spread, hl_spread_pct

## Monitoring

- **Logs**: `/logs/app.log` (rotación automática)
- **Spark UI**: Puerto 4040 para ver jobs y stages
- **Healthcheck**: Docker verifica que el proceso esté corriendo

