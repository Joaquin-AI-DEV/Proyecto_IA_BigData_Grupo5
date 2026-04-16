# StockPulse
Proyecto de Big Data e Inteligencia Artificial

## Descripción del proyecto

StockPulse es un sistema de análisis y predicción de ventas diseñado para ayudar a mejorar la gestión de inventario en empresas.

El sistema analiza datos históricos de ventas para identificar patrones de comportamiento y generar predicciones de demanda futura. Estas predicciones se visualizan mediante un dashboard interactivo que permite comparar ventas reales con estimaciones y facilitar la toma de decisiones.

El objetivo principal del proyecto es reducir problemas comunes en la gestión de inventario como:

- exceso de stock
- roturas de inventario
- planificación incorrecta de compras

Para ello se implementará un pipeline de datos que permitirá procesar datasets de ventas, entrenar un modelo de predicción y visualizar los resultados de forma clara.

---

# Integrantes

Grupo 5

- **Sergio Romero** — Data Engineer  
  Responsable de ingesta de datos, limpieza del dataset y análisis exploratorio (EDA).

- **Deninson Tapia** — Data Analyst / Data Scientist  
  Responsable del modelado de datos, entrenamiento del modelo y evaluación de resultados.

- **Joaquín Fernández** — Platform / Project Manager  
  Responsable del repositorio, API, integración de componentes y despliegue.

- **Jimmy Chen** — Business Intelligence  
  Responsable del dashboard, visualización de datos y definición de KPIs.

---

# Arquitectura del sistema (resumen)

El sistema sigue una arquitectura basada en un pipeline de datos dividido en varias capas:

1. **Ingesta de datos**
   - Carga de datasets de ventas en formato CSV o XLSX.

2. **Procesamiento de datos**
   - Limpieza de datos
   - Eliminación de duplicados
   - Normalización de fechas y categorías

3. **Almacenamiento**
   - Los datos procesados se almacenan en una base de datos MySQL.

4. **Modelado**
   - Se entrena un modelo de predicción de demanda utilizando librerías de Machine Learning.

5. **Visualización**
   - Un dashboard mostrará métricas, tendencias y predicciones de ventas.

Flujo simplificado:
Dataset → Limpieza de datos → Base de datos → Modelo predictivo → Dashboard

---

# Tecnologías utilizadas

El proyecto utiliza tecnologías comunes en el ecosistema de Big Data y Data Science:

**Lenguaje principal**
- Python

**Procesamiento de datos**
- Pandas
- NumPy

**Machine Learning**
- Scikit-learn
- Prophet (alternativa para series temporales)

**Base de datos**
- PostgreSQL (Supabase)

**Visualización**
- Uvicorn

**Herramientas de desarrollo**
- Git
- GitHub
- Jupyter Notebook

---

# Organización del repositorio

```bash
repo/
│
├── docs/
│   ├─── Fase0_Presentacion_y_Viabilidad.pdf
│   ├─── Fase1_Grupo5.pdf
│   └─── Fase2_Producto_Funcional_Local_y_Codigo_Grupo5.pdf
├── environment/
│   └─── requirements.txt
├── src/
│   ├─── backend
│   │    ├─── routes
│   │    │    ├─── __init__.py
│   │    │    ├─── auth_routes.py
│   │    │    ├─── dashboard_routes.py
│   │    │    └─── upload_routes.py
│   │    ├─── auth.py
│   │    ├─── database.py
│   │    └─── main.py
│   ├─── frontend
│   │    ├─── app.js
│   │    ├─── index.html
│   │    └─── styless.css
│   ├─── models
│   │    ├─── features.py
│   │    └─── train_model.py
│   └─── pipeline
│        ├─── __init__.py
│        ├─── clean.py
│        ├─── ingest.py
│        ├─── load_db.py
│        └─── run_pipeline.py
├── README.md
└── .gitignore



### 📁 docs/
Contiene la documentación del proyecto:

- Entregables del curso
- Diagramas de arquitectura
- Memoria técnica
- Presentaciones

### 📁 environment/
Contiene la configuración del entorno:

- `requirements.txt`
- configuración de dependencias

### 📁 src/
Contiene el código del proyecto:

- Scripts de limpieza de datos
- Scripts de entrenamiento del modelo
- Evaluación del modelo
- API o scripts de integración
- Código del dashboard

⚠️ Los datasets grandes no se subirán al repositorio.  
Solo se incluirán muestras o instrucciones de descarga.

---
```
# Cómo ejecutar el proyecto

⚠️ El sistema aún se encuentra en desarrollo, pero la estructura básica de ejecución será la siguiente.

## 1. Clonar el repositorio

```bash
git clone https://github.com/Joaquin-AI-DEV/Proyecto_IA_BigData_Grupo5.git
cd Proyecto_IA_BigData_Grupo5
```

## 2. Crear y activar entorno virtual

### Crear entorno virtual

```bash
python -m venv venv
```

### Activar en Windows

```bash
venv\Scripts\activate
```

### Activar en Linux / Mac

```bash
source venv/bin/activate
```

## 3. Instalar dependencias

```bash
pip install -r environment/requirements.txt
```

## 4. Configurar variables del entorno

```bash
# Copia el archivo de ejemplo y rellena las credenciales de Supabase:
# Linux / Mac
cp environment/.env.example environment/.env


# Windows
copy environment\.env.example environment\.env

# El archivo .env debe contener:
DB_HOST=aws-0-eu-west-1.pooler.supabase.com
DB_PORT=6543
DB_NAME=postgres
DB_USER=postgres.nbamabcfxtcltbzxuncg
DB_PASSWORD=123Grupo5321
```
## 5. Ejecución del proyecto Carga de CSV y Inicio de sesión

Ejecutar el comando: uvicorn main:app --reload --port 8000
La máquina virtual debe estar encendida y las dependencias instaladas, debes encontrarte en la carpeta src/backend
Verás la interfaz de inicio del proyecto, deberás inciar sesión con las credenciales:
Usuario: admin
Contraseña: admin123

# Estado del proyecto
El proyecto está en fase de pulido, durante la seguiente Fase se introducirán cambios en la visualización, métricas, resultados, métodos y accesibilidad del proyecto.