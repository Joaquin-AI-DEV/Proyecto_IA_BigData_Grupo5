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
- MySQL
- XAMPP (entorno local)

**Visualización**
- Power BI
- Streamlit (alternativa en Python)

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
│   └── Fase0_Presentacion_y_Viabilidad.pdf
│
├── src/
│
├── data/
│
├── environment/
│
├── README.md
└── .gitignore



### 📁 docs/
Contiene la documentación del proyecto:

- Entregables del curso
- Diagramas de arquitectura
- Memoria técnica
- Presentaciones

### 📁 src/
Contiene el código del proyecto:

- Scripts de limpieza de datos
- Scripts de entrenamiento del modelo
- Evaluación del modelo
- API o scripts de integración
- Código del dashboard

### 📁 data/
Contiene los datasets del proyecto:

- datos brutos
- datos procesados
- datasets de prueba

⚠️ Los datasets grandes no se subirán al repositorio.  
Solo se incluirán muestras o instrucciones de descarga.

### 📁 environment/
Contiene la configuración del entorno:

- `requirements.txt`
- `environment.yml`
- configuración de dependencias
- notebooks de pruebas

---
```
# Cómo ejecutar el proyecto

⚠️ El sistema aún se encuentra en desarrollo, pero la estructura básica de ejecución será la siguiente.

## 1. Clonar el repositorio

```bash
git clone https://github.com/usuario/StockPulse.git
cd StockPulse
```
## 2. Crear entorno virtual
```bash
python -m venv venv
```
Activar entorno:

Windows
```bash
venv\Scripts\activate
```
Linux / Mac
```bash
source venv/bin/activate
```
## 3. Instalar dependencias
```bash
pip install -r environment/requirements.txt
```
## 4. Ejecutar el pipeline de datos
```bash
python src/data_pipeline.py
```
## 5. Entrenar el modelo
```bash
python src/train_model.py
```
## 6. Ejecutar dashboard (opcional)
Si se usa Streamlit:
```bash
streamlit run src/dashboard.py
```
# Estado del proyecto
Actualmente el proyecto se encuentra en fase de desarrollo dentro del curso de Especialización en Inteligencia Artificial y Big Data.

Las próximas fases incluirán:

- Implementación completa del pipeline de datos
- Entrenamiento del modelo de predicción
- Creación del dashboard interactivo
- Evaluación del sistema