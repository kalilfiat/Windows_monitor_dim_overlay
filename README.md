# Monitor Dim Overlay 2.1.2

![Monitor Dim Overlay](./assets/image/MonitorDimOverlayThumbnail.png)

Monitor Dim Overlay es una utilidad para Windows que reduce las distracciones en escritorios con varios monitores. Atenúa las pantallas que no estás usando mediante overlays suaves, transparentes a los clics y sin robar el foco.

La versión 2.1.2 incorpora una máquina de estados estable, **Smart Focus**, controles verificables por monitor y una inicialización nativa confiable: puede seguir el cursor, detectar en qué monitor se encuentra la ventana activa o mantener una selección fija.

## Funciones

- Overlays nativos click-through: no bloquean clics ni aceptan foco.
- Fade configurable con restauración retardada.
- Tres modos:
  - **Seguir el cursor:** revela la pantalla donde se encuentra el puntero.
  - **Ventana activa / Smart Focus:** revela el monitor donde estás trabajando.
  - **Oscurecimiento fijo:** mantiene atenuados los monitores seleccionados.
- Configuración independiente por monitor.
- El monitor principal participa por defecto y responde al cursor o a Smart Focus como cualquier otra pantalla.
- Intensidad, color, tiempo de espera y transición configurables.
- Atajo global para activar o desactivar; `F9` por defecto.
- Peek temporal para revelar todas las pantallas; `Ctrl+Shift+F9` por defecto.
- Pausa opcional para aplicaciones fullscreen, desactivada por defecto.
- Lista de aplicaciones excluidas.
- Perfiles Trabajo, Gaming y Noche, además de perfiles personalizados.
- Inicio opcional con Windows.
- Opción para excluir los overlays de capturas compatibles con Windows.
- Detección dinámica de cambios de resolución, orientación, DPI y monitor principal.
- Interfaz moderna y aplicación residente en la bandeja del sistema.
- Preferencias visibles al iniciar; cerrar la ventana mantiene el servicio activo en la bandeja.

## Uso

Al iniciar, la aplicación queda disponible en la bandeja de Windows. Un clic abre las preferencias y un doble clic activa o desactiva los overlays.

Las preferencias se muestran automáticamente al iniciar. Al cerrar la ventana, Monitor Dim Overlay continúa funcionando en la bandeja; este comportamiento puede desactivarse desde **Automatización**.

| Acción | Control predeterminado |
|---|---|
| Activar o desactivar | `F9` |
| Revelar temporalmente | `Ctrl+Shift+F9` |
| Abrir preferencias | Clic en el icono del tray |
| Alternar estado | Doble clic en el icono del tray |

Los atajos pueden cambiarse desde **Automatización**. Si otra aplicación ya usa una combinación, Monitor Dim Overlay sigue funcionando y muestra una advertencia.

## Preferencias

La configuración se guarda de forma atómica en:

```text
%APPDATA%\MonitorDimOverlay\settings.json
```

El log de diagnóstico se encuentra en la misma carpeta. Las configuraciones de versiones anteriores y el archivo legado `monitor_dim_overlay_config.json` se migran automáticamente al iniciar.

## Ejecutar desde el código fuente

Requiere Windows, Python 3.11 o posterior y PyQt6.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python monitor_dim_overlay.py
```

Para instalar también las herramientas de tests y build:

```powershell
pip install -r requirements-dev.txt
```

## Tests

```powershell
python -m pytest
```

La suite actual contiene 20 tests y cubre validación y persistencia de preferencias, migraciones, la máquina de estados del overlay, decisión de monitores y parsing de atajos globales.

## Compilar el EXE

Con las dependencias de desarrollo instaladas:

```powershell
.\build.ps1
```

El resultado se genera en `dist\monitor_dim_overlay.exe` y también como copia portable versionada (`dist\MonitorDimOverlay-<versión>.exe`) para evitar la caché de iconos del Explorador. El script crea un icono multirresolución e incorpora versión y metadatos de Windows.

Para generar además un instalador por usuario es necesario instalar [Inno Setup](https://jrsoftware.org/isinfo.php) y ejecutar:

```powershell
.\build.ps1 -Installer
```

El instalador no requiere permisos de administrador y realiza una desinstalación limpia.

## Estructura

```text
monitor_dim/
├── app.py               Inicio y logging
├── config.py            Persistencia y migración
├── controller.py        Monitores, tray y reglas de enfoque
├── logic.py             Decisión pura de oscurecimiento
├── models.py            Preferencias y perfiles
├── overlay.py           Ventanas y animaciones
├── settings_window.py   Interfaz de preferencias
├── theme.py             Sistema visual e icono
└── winapi.py            Hotkeys, foreground y estilos nativos
```

## Privacidad y rendimiento

La aplicación funciona localmente, no usa red y no recopila telemetría. Solo consulta la posición del cursor y, cuando corresponde, la geometría y el nombre del ejecutable de la ventana activa. El polling predeterminado es de 90 ms y no captura el contenido de las pantallas.

## Limitaciones

- Diseñado exclusivamente para Windows.
- La exclusión de capturas depende de la API y versión de Windows y no puede garantizarse para todos los grabadores.
- Algunas aplicaciones con anticheat o modos exclusivos pueden controlar su propia capa de presentación; la pausa fullscreen evita interferencias en la mayoría de esos casos.
