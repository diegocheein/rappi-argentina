# 🇦🇷 Desarrollo del soporte Argentina

Explicación completa del trabajo de ingeniería que se hizo para que el plugin funcione con **Rappi Argentina** de punta a punta — desde el login hasta el pago real de un pedido.

Autor de la versión Argentina: **Diego Cheein** ([@diegocheein](https://github.com/diegocheein)).

---

## 1. Descubrimiento del host de API de Argentina

Rappi usa un host de backend distinto por país, sin un patrón único. Analizando el JavaScript del sitio `www.rappi.com.ar` se identificó el host real de Argentina:

```
https://services.rappi.com.ar
```

Se confirmó que **la estructura de endpoints es la misma** que en otros mercados (`/ms/...`, `/api/...`) — solo cambia el host y el dominio de login (`www.rappi.com.ar`).

## 2. El problema de los headers (respuesta vacía / "empty-200")

El síntoma más difícil de diagnosticar: con el token válido, varios endpoints (perfil, direcciones, búsqueda) devolvían **HTTP 200 pero con el cuerpo vacío**, mientras que otros (home, prime) funcionaban.

Capturando el pedido real que hace el sitio (con un script Playwright de diagnóstico) se descubrió la causa: **el gateway de Argentina devuelve el cuerpo vacío si la request lleva los headers extra que usan otros mercados** (`app-version`, `x-application-id`, `vendor`, `origin`, `sec-fetch-*`).

**Solución:** Argentina usa un **set mínimo de headers**, igual al del sitio web AR. Ver [`build_headers()`](src/rappi/constants.py).

## 3. Resolución de país robusta

El país se resuelve de forma que **todos los puntos de entrada** (comandos del CLI y el servidor MCP) tomen la configuración correcta, sin tener que setear variables de entorno a mano.

## 4. Sincronización de direcciones tolerante

Argentina **no expone el endpoint de "marcar dirección activa"** (devuelve 404). Se reescribió `set_active_address` para que ese paso sea *best-effort* y, pase lo que pase, **sincronice siempre las coordenadas** desde la lista de direcciones — que es lo que la búsqueda y el catálogo realmente necesitan. Ver [`services/address.py`](src/rappi/services/address.py).

## 5. Endpoint de historial de pedidos

El endpoint que trae los pedidos pasados no estaba documentado. Se identificó capturando la página de cuenta:

```
GET /api/orders/history-user?page=N   (paginado)
```

Trae cada pedido con sus productos, cantidades, precios y tienda — base para reconstruir canastas de reposición a partir de lo que se compra seguido.

## 6. Ofertas reales vs. "precio Prime"

Hallazgo clave para no engañar al usuario: en el catálogo, muchos descuentos (`have_discount`, `discount`) son **precios Prime** que **solo se cobran a socios** — un usuario no-Prime paga precio lleno.

Cómo se distingue de verdad: los **descuentos reales aparecen en el detalle de checkout** (`CHECKOUT_DETAIL`, tras `CART_RECALCULATE`) como línea **"Descuentos de tienda"**; lo que no baja ahí, no es real para vos. También se validaron **combos por cantidad** ("Agregá 3, Pagá 2"), que sí aplican para todos.

## 7. Comparación por litro / unidad

Sobre los datos de precio se agrega lógica de **valor real**: por ejemplo, una botella de 1.5L con 25% puede convenir más que una de 600ml en combo 3x2, una vez calculado el **precio por litro**. Las "ofertas" se evalúan por conveniencia, no por el cartel.

## 8. Límite: un carrito por tipo de tienda

Se descubrió (rompiendo y reparando un carrito) que Rappi mantiene **un solo carrito por tipo de tienda** (el id del carrito es `<user>_<store_type>`). No se pueden tener dos sucursales del mismo tipo a la vez: al agregar un producto de otra sucursal, el backend lo remapea o reemplaza el carrito. Implicación práctica: comprar en dos sucursales = **dos pedidos separados**.

## 9. Confirmación de pedido real (place_order) ✅

Se completó y verificó el flujo de pago de punta a punta en Argentina:

1. `CART_RECALCULATE` → `CHECKOUT_DETAIL` para obtener un `return_key` fresco.
2. `SET_TIP` para la propina al rider.
3. `POST PLACE_ORDER` con `{return_key}` → respuesta `{id, state: "created"}`.
4. Verificación: pedido activo, shopper preparando, ETA y entrega a la dirección.

**Resultado:** pedido real colocado y pagado con tarjeta, confirmado en el sistema.

## 10. Entrega programada (investigado, no soportado)

Vea ofrece **franjas horarias** (hay un widget `slots` en el checkout). Se intentó implementarlo, pero el servicio de franjas (`/shopping-cart/v1/vea/slots`) devuelve **502** de forma consistente y no se pudo obtener/seleccionar una franja de manera confiable. Por eso el conector hace **solo entrega inmediata**; para programar un día/horario hay que confirmar desde la app (el carrito armado queda guardado en la cuenta).

## 11. CLI y documentación en español

Opción de login para Argentina, textos en español y una [guía de uso completa](GUIA-ARGENTINA.md).

---

## Archivos del desarrollo Argentina

| Archivo | Qué se hizo |
|---|---|
| [`src/rappi/constants.py`](src/rappi/constants.py) | Host AR, set mínimo de headers, `accept-language: es-AR` |
| [`src/rappi/services/address.py`](src/rappi/services/address.py) | Sync de coordenadas tolerante (sin endpoint set-active) |
| [`src/rappi/cli/auth.py`](src/rappi/cli/auth.py) | Login Argentina |
| [`tests/test_constants.py`](tests/test_constants.py) | Tests del set de headers AR |
| [`GUIA-ARGENTINA.md`](GUIA-ARGENTINA.md) | Guía de uso en español |

> Construido sobre el plugin base de Gabriel Garavit (arquitectura del servidor MCP, skills, CLI y memoria), licencia MIT. El trabajo de adaptación, reverse-engineering e integración para Argentina descrito acá es de Diego Cheein.
