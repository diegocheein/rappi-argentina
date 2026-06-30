# 🇦🇷 Rappi Argentina — Guía de uso

Plugin para pedir de **Rappi Argentina** conversando con Claude (Claude Code, Desktop) o desde la terminal. Buscás productos, armás el carrito, comparás ofertas reales, pedís y seguís la entrega — todo con tu cuenta de Rappi.

> **Versión Argentina desarrollada por [Diego Cheein](https://github.com/diegocheein).** Soporte completo para Rappi AR (`services.rappi.com.ar`): login, búsqueda, ofertas, carrito, pedido y tracking. Ver [qué se desarrolló para Argentina](#qué-se-desarrolló-para-argentina).
> _Construido sobre el plugin base de Gabriel Garavit (Colombia/México), licencia MIT._

---

## ✅ Qué se puede hacer

- **Buscar** productos y tiendas (restaurantes, Vea y otros súper, farmacias, etc.).
- **Ver menús y catálogos** de cada tienda.
- **Armar el carrito** y modificar cantidades.
- **Detectar ofertas reales** (descuentos de tienda y combos tipo "3x2") — distinguiéndolas de los "precios Prime" que no se aplican si no sos socio.
- **Comparar precio por litro / unidad** para elegir lo que más conviene.
- **Manejar direcciones** de entrega.
- **Poner propina** al rider.
- **Confirmar el pedido** (entrega inmediata) y **seguir la entrega** en tiempo real.
- **Memoria local**: aprende qué comprás seguido y arma canastas de reposición.

> ⚠️ **Limitación conocida:** la entrega **programada con franja horaria** (ej: "mañana de 10 a 12") todavía no está soportada por el conector; solo **entrega inmediata**. Para programar un día/horario, confirmá el pedido desde la app de Rappi (el carrito que armes queda guardado en tu cuenta).

---

## 📋 Requisitos

- **Python 3.12+**
- **[uv](https://docs.astral.sh/uv/)** (gestor de paquetes de Python)
- Una **cuenta de Rappi Argentina** (con teléfono para el código OTP)

---

## 🚀 Instalación

```bash
git clone https://github.com/diegocheein/rappi-argentina.git
cd rappi-argentina
uv sync
uv run playwright install chromium   # navegador para el login
```

---

## 🔑 Autenticación (Argentina)

```bash
uv run rappi auth login --country ar
```

Se abre una ventana del navegador en `rappi.com.ar/login`. Entrás con tu **teléfono + código OTP** y el plugin captura el token automáticamente. Queda guardado **local** en `~/.rappi/config.json` (nunca sale de tu máquina).

Verificar que quedó logueado:

```bash
uv run rappi auth status
```

---

## 💻 Comandos del CLI

| Comando | Qué hace |
|---|---|
| `rappi go` | Sesión interactiva guiada — la forma más fácil de pedir |
| `rappi auth login --country ar` | Iniciar sesión (Argentina) |
| `rappi auth status` | Ver tu perfil y estado de sesión |
| `rappi auth logout` | Cerrar sesión |
| `rappi address list` | Listar tus direcciones de entrega |
| `rappi address set <id>` | Activar una dirección (sincroniza coordenadas) |
| `rappi search "<texto>"` | Buscar productos y tiendas |
| `rappi store browse` | Explorar tiendas y menús |
| `rappi cart ...` | Ver y modificar el carrito |
| `rappi order ...` | Checkout y seguimiento del pedido |
| `rappi history` | Historial de pedidos |
| `rappi favorites` | Tiendas favoritas |
| `rappi prefs` | Preferencias del usuario |

Ejemplos:

```bash
uv run rappi search "milanesa"
uv run rappi address list
uv run rappi address set 436238197
uv run rappi go
```

> Todos los comandos se ejecutan con `uv run rappi <comando>`.

---

## 🤖 Uso en Claude Code

El plugin se auto-registra en Claude Code (servidor MCP definido en `.mcp.json`). Una vez logueado, simplemente abrí Claude Code en la carpeta del proyecto:

```bash
cd rappi-argentina
claude
```

Y le hablás natural: *"buscá pizza en Vea"*, *"armame un carrito con lo que compro siempre"*, *"¿hay alguna oferta de Coca Zero?"*. Las **skills** disponibles son `/order-food`, `/rappi-search`, `/rappi-reorder` y `/rappi-suggest`.

---

## 🇦🇷 Qué se desarrolló para Argentina

El desarrollo del soporte Argentina (lo de este fork) está en estos archivos:

- **`src/rappi/constants.py`** — host de API de Argentina (`services.rappi.com.ar`), país `ar`, header `accept-language: es-AR`, y resolución de país desde `~/.rappi/config.json`. Argentina usa un **set mínimo de headers**: el gateway de AR devuelve respuestas vacías si se le mandan los headers extra de CO/MX (`app-version`, `x-application-id`, etc.).
- **`src/rappi/services/address.py`** — sincronización de coordenadas tolerante (AR no tiene el endpoint de "marcar dirección activa").
- **`src/rappi/cli/auth.py`** — opción `--country ar`.
- **`tests/test_constants.py`** — tests de headers por país.

> Nota técnica: los **descuentos** aparecen en el detalle de checkout (tras recalcular), no en el carrito crudo. Los descuentos de "precio Prime" no se aplican si no sos socio Prime.

---

## 📄 Licencia y créditos

**Versión Argentina:** desarrollada por **Diego Cheein** — [@diegocheein](https://github.com/diegocheein).

Licencia **MIT**. Construido sobre el plugin base de Gabriel Garavit ([garavitgabriel/rappi-plugin-claude-openclaw](https://github.com/garavitgabriel/rappi-plugin-claude-openclaw)), del que se reutilizó la arquitectura de Colombia/México.

> ⚠️ Proyecto no oficial, sin relación con Rappi S.A. Usalo con tu propia cuenta y bajo tu responsabilidad.
