# cam360 — cámara 360° para Webots

Graba video 360° (equirectangular) de cualquier simulación de Webots, hasta 8K,
con un impacto mínimo en la velocidad de la simulación.

- **Sin costura en Python:** Webots genera la panorámica completa en la GPU.
- **Codificación por hardware:** el video se codifica con la GPU NVIDIA (NVENC)
  mediante ffmpeg, en un proceso aparte.
- **Sin dependencias de Python:** el controlador solo usa la biblioteca estándar.
- **Duración correcta:** el video siempre dura lo mismo que el tiempo simulado,
  aunque la simulación corra más lenta o más rápida que el tiempo real.

## Contenido

```
cam360/
├── protos/cam360.proto              la cámara 360 (nodo Robot con una Camera)
├── controllers/cam360/cam360.py     controlador que graba el video
└── worlds/cam360.wbt                mundo de ejemplo
```

## Requisitos

| Requisito | Notas |
|---|---|
| [Webots R2025a](https://cyberbotics.com/) | o una versión posterior compatible |
| Python 3.8+ | el que use Webots para los controladores en Python |
| [ffmpeg](https://ffmpeg.org/download.html) | debe estar en el `PATH`. En Windows: `winget install Gyan.FFmpeg` |
| GPU NVIDIA con NVENC | recomendado; sin ella se puede codificar por CPU (ver [Configuración](#configuración)) |

Para comprobar que ffmpeg está instalado y que tiene NVENC disponible:

```
ffmpeg -hide_banner -encoders | findstr nvenc      (Windows)
ffmpeg -hide_banner -encoders | grep nvenc         (Linux / macOS)
```

## Prueba rápida

1. Abrir `worlds/cam360.wbt` en Webots.
2. Ejecutar la simulación (▶). La consola muestra
   `[cam360] 8192x4096 @ 15.62 fps -> ...`.
3. Reiniciar la simulación (Reset) o cerrar Webots para terminar la grabación.

El video queda en `controllers/cam360/CAM360_8192x4096.mp4`.

El mundo de ejemplo tiene cuatro cubos para comprobar la orientación:

| Cubo | Dirección | Posición en el video |
|---|---|---|
| rojo | frente (+X) | centro |
| verde | izquierda (+Y) | cuarto izquierdo |
| amarillo | derecha (−Y) | cuarto derecho |
| azul | atrás (−X) | bordes izquierdo y derecho |

## Usarlo en tu propio proyecto

1. Copiar `protos/cam360.proto` a la carpeta `protos/` de tu proyecto, y la
   carpeta `controllers/cam360/` a tu carpeta `controllers/`.
2. En tu archivo `.wbt`, declarar el PROTO al inicio (junto a los otros `EXTERNPROTO`):

   ```
   EXTERNPROTO "../protos/cam360.proto"
   ```

3. Agregar la cámara al mundo:

   ```
   cam360 {
     translation 0 0 1.5
     height 2048
     controller "cam360"
   }
   ```

### Cámara montada en un robot o vehículo

`cam360` es un nodo `Robot`, así que se puede poner dentro del campo `children`
de otro robot (o de un `Solid`/`Transform` de ese robot) para que se mueva con él.
Cada `cam360` tiene su propio controlador, independiente del controlador del
robot que la lleva.

```
Robot {
  children [
    cam360 {
      translation 0 0 0.8
      height 2048
      controller "cam360"
    }
    ...
  ]
  controller "mi_controlador"
}
```

### Varias cámaras

Cada cámara debe tener un `name` distinto. El nombre también se usa en el
nombre del archivo de video:

```
cam360 { name "CAM_A" translation 0 0 1.5 controller "cam360" }
cam360 { name "CAM_B" translation 3 0 1.5 controller "cam360" }
```

Esto genera `CAM_A_4096x2048.mp4` y `CAM_B_4096x2048.mp4`.

## Configuración

### Campos del PROTO

| Campo | Valor por defecto | Descripción |
|---|---|---|
| `translation` | `0 0 0` | posición de la cámara |
| `rotation` | `0 0 1 0` | orientación; el centro del video apunta al eje +X de la cámara |
| `height` | `2048` | resolución vertical; el video es de `(2·height) × height` |
| `name` | `"CAM360"` | nombre del robot cámara; también es el prefijo del archivo de video |
| `controller` | `"<generic>"` | usar `"cam360"` |

Resoluciones habituales:

| `height` | Video | Uso |
|---|---|---|
| 1024 | 2048×1024 (2K) | pruebas rápidas |
| 2048 | 4096×2048 (4K) | uso general, más rápido que el tiempo real en la mayoría de GPU |
| 3072 | 6144×3072 (6K) | punto intermedio |
| 4096 | 8192×4096 (8K) | máxima calidad; es el límite de NVENC |

### Constantes del controlador (`controllers/cam360/cam360.py`)

| Constante | Valor por defecto | Descripción |
|---|---|---|
| `VIDEO_FPS` | `15.0` | fps deseados; se redondea al múltiplo de `basicTimeStep` más cercano |
| `ENCODER` | `"hevc_nvenc"` | `hevc_nvenc` o `av1_nvenc` (GPU NVIDIA); `libx265` o `libx264` (CPU) |
| `QUALITY_CQ` | `23` | calidad: menor = mejor calidad y archivo más grande (18–28 es un rango razonable) |

Variable de entorno opcional: `PANO_MAX_FRAMES=N` detiene la grabación después
de `N` cuadros (útil para pruebas).

#### fps real del video

La cámara solo puede capturar en pasos de simulación, así que el fps real es
`1000 / (k · basicTimeStep)`, con `k` entero. Por ejemplo:

| `basicTimeStep` | `VIDEO_FPS` | fps real |
|---|---|---|
| 32 ms | 15 | 15.625 |
| 16 ms | 30 | 31.25 |
| 10 ms | 25 | 25 |
| 8 ms | 30 | 31.25 |

Para obtener un fps exacto, elegir un `basicTimeStep` que divida a `1000 / fps`
(por ejemplo, 10 ms para 25 fps o 20 ms para 50 fps).

### Sin GPU NVIDIA

Cambiar en el controlador:

```python
ENCODER = "libx265"   # o "libx264" si el video no supera 4096 px de ancho
```

La codificación por CPU funciona con cualquier equipo, pero es bastante más
lenta y reduce la velocidad de la simulación, sobre todo en 8K.

## Rendimiento

Valores medidos en una laptop con RTX 4070, en el mundo de ejemplo
(1.0 = tiempo real):

| Video | Velocidad de la simulación |
|---|---|
| 4096×2048 | ≈ 2.4× tiempo real |
| 8192×4096 | ≈ 0.5× tiempo real |

Consejos para grabar más rápido:

- Ejecutar en modo **Fast** (⏩).
- Desactivar el render de la vista 3D de Webots (**View → Rendering**, `Ctrl+4`).
  Las cámaras siguen funcionando.
- No mostrar el overlay de la cámara en la vista 3D.
- Usar la menor resolución que sirva para tu caso: 4K es unas 4 veces más rápido que 8K.

## Ver o publicar el video 360°

El MP4 contiene la imagen equirectangular, pero no los metadatos que indican
que es un video 360°. Para que YouTube, VLC o los visores VR lo muestren como
video esférico:

1. Descargar [Spatial Media Metadata Injector](https://github.com/google/spatial-media/releases).
2. Abrir el MP4, marcar **"My video is spherical (360)"** y pulsar **Inject metadata**.
3. Usar el archivo `_injected.mp4` que se genera.

## Cómo funciona

1. **Captura en la GPU.** El PROTO crea una `Camera` con `projection "cylindrical"`,
   `fieldOfView 6.2832` (2π) y `width = 2·height`. Con esa configuración, Webots
   renderiza un cubemap y lo convierte a la proyección equirectangular con un
   shader. La imagen que recibe el controlador ya es la panorámica final.
2. **Solo cuando se graba.** La cámara se habilita con un periodo igual al
   intervalo entre cuadros del video, así que Webots no renderiza la cámara en
   los pasos intermedios.
3. **Codificación en paralelo.** El controlador pasa los bytes BGRA de
   `getImage()`, sin convertirlos, a un proceso `ffmpeg` que codifica con NVENC.
   Un hilo aparte envía los cuadros a ffmpeg mientras Webots renderiza el siguiente.

## Solución de problemas

| Síntoma | Causa probable / solución |
|---|---|
| `FileNotFoundError` al iniciar el controlador | ffmpeg no está en el `PATH`. Instalarlo y reiniciar Webots. |
| `No capable devices found` / `Cannot load nvcuda.dll` | No hay GPU NVIDIA o el driver está desactualizado. Actualizar el driver o usar `libx265`. |
| ffmpeg falla con resoluciones altas | NVENC admite hasta 8192 px de ancho (`height` ≤ 4096); `h264_nvenc` y `libx264` solo hasta 4096 px. |
| El video está vacío o corrupto | La grabación se cierra al detener o reiniciar la simulación. Si Webots se cierra a la fuerza, el MP4 queda incompleto. |
| La imagen se ve negra | Revisar que el mundo tenga luz (`TexturedBackgroundLight` o `DirectionalLight`). |
| `WARNING: ... device not found` | El controlador busca la cámara `<name>_equirect` del PROTO. Usar `controller "cam360"` solo con nodos `cam360`. |

## Licencia

Este proyecto se distribuye bajo la licencia
[PolyForm Noncommercial 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0)
(ver [LICENSE](LICENSE)).

- **Permitido sin costo:** uso personal, estudio, investigación, docencia y
  proyectos sin fines comerciales, incluido el uso en universidades, colegios,
  centros de investigación, ONG y entidades públicas. Se puede modificar y
  redistribuir, siempre que se incluya el archivo `LICENSE` con la línea
  `Required Notice`.
- **No permitido sin autorización:** cualquier uso comercial, por ejemplo
  integrarlo en un producto o servicio que se vende, o usarlo en proyectos
  pagados para clientes.

Para obtener una licencia comercial, escribir a
[dcasta25@eafit.edu.co](mailto:dcasta25@eafit.edu.co).
