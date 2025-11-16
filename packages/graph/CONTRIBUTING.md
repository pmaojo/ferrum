# Guía de Contribución

Este proyecto utiliza Python 3.11 y varios servicios externos. Para ejecutar la suite completa de pruebas y participar en el desarrollo, sigue estos pasos.

## Instalación de dependencias

1. Crea un entorno virtual.
2. Instala los paquetes de `requirements.txt` y `requirements-dev.txt`.
   Lo más sencillo es usar:

```bash
pip install -e .[dev]  # o ejecuta `make install`
```

Puedes usar también `make install` para instalar de una vez todas las
dependencias opcionales. Ejecuta este paso antes de correr `pytest` para que
paquetes como `numpy`, `redis` y `PyPDF2` estén disponibles.

Las pruebas de integración y rendimiento requieren paquetes adicionales incluidos en el grupo opcional `dev`. Asegúrate de instalarlos antes de ejecutar `pytest`.

## Servicios externos

Algunas pruebas necesitan bases de datos en ejecución. Puedes iniciarlas mediante contenedores Docker.

### Memgraph

```bash
docker run -d --name memgraph \
  -p 7687:7687 -p 3000:3000 \
  memgraph/memgraph-platform:latest
```

El puerto `7687` expone la base de datos y `3000` la interfaz web Memgraph Lab.

### FalkorDB

Ejecuta el script incluido para desplegar FalkorDB:

```bash
bash scripts/setup_falkordb.sh
```

El script arranca un contenedor Redis compatible y muestra las variables de entorno necesarias.

## Dependencias opcionales para las pruebas

Algunos módulos de prueba dependen de librerías adicionales como `numpy`, `Pillow`, `torch`, `fastapi` y `redis`.
Si no están instaladas, `pytest` marcará esos archivos como saltados mediante `pytest.importorskip`.
Para ejecutar la suite completa instala también:

```bash
pip install numpy Pillow torch fastapi redis
```

## Automatización con Makefile

El repositorio incluye un `Makefile` con atajos para preparar el entorno de pruebas. Los comandos principales son:

- `make install` – instala todas las dependencias.
- `make start-services` – inicia Memgraph, FalkorDB y servicios de `docker-compose.yml` necesarios para las pruebas.
- `make test` – ejecuta la suite de `pytest`.
- `make lint` – analiza el código con `flake8`.

Puedes combinar estos objetivos para obtener un entorno listo para desarrollar y validar tus cambios.

Antes de enviar un Pull Request, ejecuta `make lint` y corrige cualquier advertencia o error de estilo que aparezca.
