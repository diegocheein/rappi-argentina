# 🇦🇷 Rappi Argentina — para Claude

Pedí de **Rappi Argentina** conversando con Claude (Claude Code, Desktop) o desde la terminal. Buscás productos, comparás **ofertas reales**, armás el carrito, **pagás** y seguís la entrega — todo con tu cuenta de Rappi.

**Autor de la versión Argentina:** [Diego Cheein](https://github.com/diegocheein).

> 📖 **Guía de uso completa (español): [GUIA-ARGENTINA.md](GUIA-ARGENTINA.md)**
> 🛠️ **Cómo se desarrolló: [DESARROLLO.md](DESARROLLO.md)**

---

## ✅ Qué se puede hacer

- **Buscar** productos y tiendas (restaurantes, Vea y otros súper, farmacias, etc.).
- **Detectar ofertas reales** — distingue los descuentos de tienda que de verdad se aplican de los "precios Prime" que no se cobran si no sos socio.
- **Comparar por litro / unidad** para elegir lo que más conviene.
- **Armar el carrito** y modificar cantidades.
- **Reposición inteligente:** aprende qué comprás seguido y arma la canasta.
- **Poner propina**, **confirmar el pedido** (entrega inmediata) y **seguir la entrega** en tiempo real.

> 💡 El pedido se confirma con **entrega inmediata** y funciona end-to-end (carrito → propina → pago → seguimiento). Si querés elegir un **día/franja horaria**, hacé el paso final desde la app — el carrito queda guardado en tu cuenta.

---

## 🚀 Arranque rápido

```bash
git clone https://github.com/diegocheein/rappi-argentina.git
cd rappi-argentina
uv sync
uv run playwright install chromium

# Login (se abre el navegador, entrás con teléfono + OTP)
uv run rappi auth login --country ar

# Probar
uv run rappi auth status
uv run rappi search "milanesa"
uv run rappi go        # sesión interactiva guiada
```

Requisitos: **Python 3.12+**, **[uv](https://docs.astral.sh/uv/)** y una **cuenta de Rappi Argentina**.

El token queda guardado **local** en `~/.rappi/config.json` — nunca sale de tu máquina.

---

## 💻 Comandos

| Comando | Qué hace |
|---|---|
| `rappi go` | Sesión interactiva — lo más fácil para pedir |
| `rappi auth login --country ar` / `auth status` | Iniciar sesión / ver perfil |
| `rappi search "<texto>"` | Buscar productos y tiendas |
| `rappi address list` / `set <id>` | Direcciones de entrega |
| `rappi store browse` | Explorar tiendas y menús |
| `rappi cart` / `order` | Carrito / checkout y seguimiento |
| `rappi history` / `favorites` / `prefs` | Historial / favoritos / preferencias |

Detalle y ejemplos en la [guía](GUIA-ARGENTINA.md).

---

## 🤖 En Claude Code

Se auto-registra (servidor MCP). Abrí Claude Code en la carpeta y hablale natural:

```
cd rappi-argentina
claude
```

*"¿hay alguna oferta de Coca Zero?"* · *"armame el carrito de lo que compro siempre"* · *"pedí 2 papeles y pastillas de lavavajillas"*. Skills: `/order-food`, `/rappi-search`, `/rappi-reorder`, `/rappi-suggest`.

---

## 📄 Licencia y créditos

Licencia **MIT**. Versión Argentina por **Diego Cheein**. Construido sobre el plugin base de [Gabriel Garavit](https://github.com/garavitgabriel/rappi-plugin-claude-openclaw) (arquitectura del servidor MCP, skills, CLI y memoria).

> ⚠️ Proyecto no oficial, sin relación con Rappi S.A. Usalo con tu propia cuenta y bajo tu responsabilidad.
