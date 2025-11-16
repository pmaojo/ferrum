# PermaGraph

PermaGraph es un **framework** para construir y consultar grafos de conocimiento mediante GraphRAG. Sigue una arquitectura hexagonal donde los servicios de dominio interactúan con la infraestructura a través de puertos y adaptadores, facilitando la extensión y el testeo aislado de cada componente.

Para entender cómo la documentación de Kthulu llega a este proyecto mediante SCG, consulta la [guía de flujo de documentación](../docs/documentation-flow.md).

## Características

- Soporte multi-tenant con `tenant_id` en todas las entidades.
- Servicios reutilizables para ingesta, consulta y orquestación de flujos.
- Adaptadores para distintos LLM, motores de grafo y frontends (FastAPI, Streamlit).
- Observabilidad con OpenTelemetry y métricas Prometheus.
- Extensa batería de pruebas ubicada en `tests/`.

## Estructura

```
application/       # Puertos (interfaces)
adapters/          # Implementaciones de puertos
infrastructure/    # Scripts de arranque y utilidades
domain/            # Entidades y servicios de negocio
ui_adapters/       # Integraciones con frameworks de interfaz
monitoring/        # Dashboards y alertas
```

## Inicio rápido

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .[dev]  # o usa `pip install -r requirements-dev.txt`
cp .env.example .env
docker compose up -d
python -m infrastructure.start_api
```

Todas las variables de entorno disponibles se documentan en `.env.example`. Sustituye tus claves allí y evita hardcodearlas en el código.

Para controlar el acceso desde aplicaciones web, configura la variable `ALLOWED_ORIGINS` con una lista separada por comas de dominios permitidos:

```bash
export ALLOWED_ORIGINS='["https://app.ejemplo.com","http://localhost:3000"]'
```

Si se omite, el servidor no aceptará solicitudes con cabecera `Origin` distinta a los dominios especificados.

## Command Line Interface

La utilidad de línea de comandos se implementa con [Typer](https://typer.tiangolo.com/) y emplea prompts de [Questionary](https://github.com/tmbo/questionary). Para usarla es necesario instalar las dependencias de desarrollo:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .[dev]  # o `pip install -r requirements-dev.txt`
```

Una vez configurado el entorno, se pueden ejecutar los siguientes comandos:

```bash
permagraph create-app ./myproject
permagraph check-env --env-file .env
permagraph start-api
permagraph migrate  # --downgrade para revertir
```

## Ejecutar pruebas

Antes de correr la suite es necesario instalar **tanto** los requisitos
principales de `requirements.txt` como los de `requirements-dev.txt`.
La forma recomendada es:

```bash
pip install -e .[dev]  # o ejecuta `make install`
```

Una vez instaladas las dependencias puedes lanzar las pruebas con:

```bash
pytest -q
# o bien
make test
```

## Generar documentación

Puedes generar la documentación HTML con [pdoc](https://pdoc.dev/):

```bash
bash scripts/generate_docs.sh
# o bien
make docs
```

Los archivos se guardarán en el directorio `docs/`.

## Licencia

Distribuido bajo los términos de la [licencia MIT](LICENSE).
