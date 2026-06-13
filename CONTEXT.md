# Portada Movilab

Landing page para movilab.es que muestra una grid de proyectos side-project con sistema de administración básico.

## Language

**Project**:
Un side-project que se muestra en la grid de la landing page.
_Avoid_: app, aplicación, servicio

**Grid**:
Elemento visual de 4 columnas que muestra los proyectos en la página principal.
_Avoid_: lista, tarjetas

**Admin panel**:
Interfaz web protegida por login para gestionar proyectos (CRUD).
_Avoid_: dashboard, panel de control

**Project entry**:
Un registro en la base de datos que representa un proyecto con título, descripción, enlaces e imagen.
_Avoid_: item, elemento

**Upload**:
Acción de subir una captura de pantalla del proyecto a la app.
_Avoid_: imagen, foto, screenshot

## Tech Stack

- Backend: Python + FastAPI
- Frontend: HTML/CSS/JS vanilla
- Database: SQLite
- Container: Docker (python:3.12-slim)
- Proxy: nginx proxy manager

## Infrastructure

- Puerto del contenedor: configurable via .env (CONTAINER_PORT, default: 8000)
- Puerto del host: configurable via .env (HOST_PORT, default: 8000)
- Red Docker: proxy_network (requerido para nginx proxy manager)
- Contenedor: movilab-portada (nginx proxy manager apunta a http://movilab-portada:8000)
- Volumen: Bind mount C:/Proyextos/portada_movilab/data/ a /app/data
- SSL: ya configurado en nginx proxy manager

## Security

- Login: usuario único, credenciales en .env (USER, PASSWORD)
- Password: almacenada con hash bcrypt
- Sesión: cookie persistente de 30 días
- Seguridad: básica consciente (sin rate limiting, sin brute force protection)

## Upload

- Formatos: PNG, JPG
- Tamaño máximo: 5MB
- Validación: backend (no confiar en frontend)
- Almacenamiento: disco dentro del contenedor (/app/data/uploads/)

## Tech Stack Decisions (por qué)

- **FastAPI**: más rápido que Flask, async nativo, OpenAPI automático
- **SQLite**: suficiente para uso personal, sin dependencias externas
- **HTML formularios**: sin JavaScript requerido, más simple
- **CSS puro**: para una landing page con pocos componentes no se necesita framework
- **python:3.12-slim**: balance entre tamaño y compatibilidad
