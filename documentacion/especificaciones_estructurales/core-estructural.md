---
name: "core-estructural"
version: "1.0.0"
fecha: "2026-06-13"
estado: "approved"
module: "core"
dependencies: []
related_adrs: []
---

# Especificación Estructural: Core (Portada Movilab)

## 1. Propósito

Define la arquitectura técnica de la landing page de movilab.es: una aplicación web que muestra una grid de proyectos side-project con sistema de administración básico, desplegada en Docker con nginx proxy manager.

## 2. Decisiones de Arquitectura

### 2.1 Backend: Python + FastAPI
- **Contexto:** Necesitábamos un framework ligero, rápido de montar, con soporte async nativo y documentación automática
- **Consecuencias:** FastAPI genera OpenAPI automáticamente, uvicorn como ASGI server, dependencias mínimas
- **Restricciones:** Python 3.12 como versión mínima

### 2.2 Frontend: HTML/CSS/JS vanilla
- **Contexto:** Para una landing page con pocos componentes, un framework JS sería overkill
- **Consecuencias:** Sin build step, sin dependencias de npm, archivos estáticos servidos por FastAPI
- **Restricciones:** Sin interactividad compleja, formularios HTML estándar

### 2.3 Base de Datos: SQLite
- **Contexto:** Uso personal, un solo usuario, pocos registros (proyectos), sin concurrencia
- **Consecuencias:** Sin servidor de BD, archivo único `data.db`, suficiente para el caso de uso
- **Restricciones:** NO escala a múltiples usuarios concurrentes, NO soporta escritura concurrente de alto volumen

### 2.4 Contenedor: Docker (python:3.12-slim)
- **Contexto:** Consistencia entre entornos, despliegue reproducible
- **Consecuencias:** Imagen base ~150MB, sin dependencias del sistema host
- **Restricciones:** Bind mount para persistir datos en C:/Proyextos/portada_movilab/data/

### 2.5 Proxy: nginx proxy manager
- **Contexto:** Ya existe infraestructura nginx proxy manager con SSL configurado
- **Consecuencias:** El contenedor DEBE estar en la red `proxy_network`, nginx apunta a `http://movilab-portada:8000`
- **Restricciones:** No exponer puertos al host innecesariamente

## 3. Patrones de Diseño

### 3.1 Patrón: Server-Side Rendering (SSR)
- **Descripción:** Las páginas HTML se generan en el servidor con datos de la BD
- **Implementación:** FastAPI sirve HTML con Jinja2 templates, formularios POST estándar
- **Trade-offs:** Sin SPA, pero más simple y sin JavaScript requerido

### 3.2 Patrón: Session Cookie
- **Descripción:** Autenticación basada en cookie persistente de 30 días
- **Implementación:** Cookie firmada con secret key, validación en cada request admin
- **Trade-offs:** Más cómodo que JWT para un solo usuario, pero no revocable sin cerrar sesión

## 4. Contratos de API

### 4.1 GET /
- **Método:** GET
- **Ruta:** /
- **Request:** Sin parámetros
- **Response 200:** HTML con grid de proyectos
- **Errores:**
  - `500`: Error de base de datos

### 4.2 GET /admin
- **Método:** GET
- **Ruta:** /admin
- **Request:** Cookie de sesión requerida
- **Response 200:** HTML con lista de proyectos y formularios CRUD
- **Response 302:** Redirect a /login si no autenticado
- **Errores:**
  - `401`: No autenticado

### 4.3 POST /login
- **Método:** POST
- **Ruta:** /login
- **Request:**
  ```json
  {
    "username": "string (requerido)",
    "password": "string (requerido)"
  }
  ```
- **Response 302:** Redirect a /admin en éxito
- **Response 401:** Credenciales inválidas (mensaje de error en HTML)
- **Errores:**
  - `401`: Credenciales inválidas

### 4.4 POST /projects
- **Método:** POST
- **Ruta:** /projects
- **Request:** multipart/form-data con campos del proyecto + imagen
- **Response 302:** Redirect a /admin
- **Errores:**
  - `400`: Campos requeridos faltantes
  - `413:** Imagen supera 5MB
  - `415:** Formato de imagen no soportado (solo PNG/JPG)

### 4.5 PUT /projects/{id}
- **Método:** PUT
- **Ruta:** /projects/{id}
- **Request:** multipart/form-data con campos actualizados
- **Response 302:** Redirect a /admin
- **Errores:**
  - `404:** Proyecto no encontrado

### 4.6 DELETE /projects/{id}
- **Método:** DELETE
- **Ruta:** /projects/{id}
- **Request:** Sin body
- **Response 302:** Redirect a /admin
- **Errores:**
  - `404:** Proyecto no encontrado

### 4.7 GET /uploads/{filename}
- **Método:** GET
- **Ruta:** /uploads/{filename}
- **Request:** Sin parámetros
- **Response 200:** Archivo de imagen
- **Errores:**
  - `404:** Archivo no encontrado

## 5. Modelos de Datos

### 5.1 Project
```sql
CREATE TABLE projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    url TEXT,
    repo_url TEXT,
    image_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```
- **Restricciones:**
  - `title`: requerido, máximo 200 caracteres
  - `url`: formato URL válido o NULL
  - `repo_url`: formato URL válido o NULL
  - `image_url`: nombre del archivo en uploads/ o NULL
- **Relaciones:** Ninguna (tabla aislada)

### 5.2 uploads/ (directorio)
- **Estructura:** Archivos de imagen con nombre UUID + extensión original
- **Restricciones:** Solo PNG/JPG, máximo 5MB
- **Relaciones:** `image_url` en Project referencia al nombre del archivo

## 6. Dependencias

### 6.1 Librerías Python
- **FastAPI 0.115.0:** Framework web async
- **uvicorn 0.30.0:** Servidor ASGI
- **python-multipart 0.0.9:** Soporte para formularios multipart
- **aiosqlite 0.20.0:** SQLite async para FastAPI

### 6.2 Servicios Externos
- **nginx proxy manager:** Proxy inverso con SSL (ya configurado)
- **Docker:** Runtime de contenedores

## 7. Restricciones Técnicas

### 7.1 Rendimiento
- Latencia máxima: < 200ms para páginas estáticas
- Throughput: suficiente para un solo usuario
- Conexiones simultáneas: 1 (uso personal)

### 7.2 Seguridad
- Autenticación: cookie persistente de 30 días con secret key
- Password: hash bcrypt
- Datos sensibles: credenciales en variables de entorno (.env)
- Rate limiting: NO implementado (consciamente básico)
- Brute force protection: NO implementado

### 7.3 Disponibilidad
- Uptime: best-effort (proyecto personal)
- Estrategia de fallback: restart automático via Docker
- Backup: manual del volumen data/

## 8. Convenciones

### 8.1 Naming
- Endpoints: kebab-case para rutas, snake_case para parámetros
- Variables: snake_case (Python convention)
- Tablas: snake_case
- Archivos: snake_case

### 8.2 Estructura de Código
```
/
├── main.py              ← FastAPI app + routes
├── database.py          ← SQLite connection + queries
├── auth.py              ← Login logic + session
├── requirements.txt     ← Python dependencies
├── Dockerfile           ← Container build
├── docker-compose.yml   ← Service definition
├── .env.example         ← Environment variables template
├── templates/           ← Jinja2 HTML templates
│   ├── index.html       ← Landing page
│   ├── login.html       ← Login form
│   └── admin.html       ← Admin panel
├── static/              ← CSS, images
│   └── style.css
└── data/                ← Persistent data (gitignored)
    ├── data.db          ← SQLite database
    └── uploads/         ← Project screenshots
```

## 9. Notas de Implementación

- El .env DEBE contener: USER, PASSWORD, SECRET_KEY, CONTAINER_PORT, HOST_PORT
- Las imágenes se guardan con nombre UUID para evitar colisiones
- El endpoint DELETE DEBE eliminar también el archivo de imagen asociado
- FastAPI sirve los archivos estáticos directamente (sin nginx interno)

## 10. Changelog

| Versión | Fecha | Cambios |
|---------|-------|---------|
| 1.0.0 | 2026-06-13 | Versión inicial |
