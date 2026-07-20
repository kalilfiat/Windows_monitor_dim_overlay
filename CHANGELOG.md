# Changelog

## 2.1.2

- Preferencias se abre automáticamente al iniciar y puede desactivarse desde Automatización.
- Cerrar Preferencias oculta la ventana y mantiene la aplicación activa en la bandeja.
- Inicialización diferida después del arranque de Qt para evitar overlays inactivos.
- Refuerzo nativo de `TOPMOST`, `NOACTIVATE` y `FRAMECHANGED` mediante `SetWindowPos`.
- El monitor que contiene Preferencias se revela mientras la ventana está abierta.

## 2.1.1

- El monitor principal queda habilitado para oscurecimiento por defecto.
- Migración automática al esquema 4 para adoptar el nuevo comportamiento una sola vez.

## 2.1.0

- Máquina de estados idempotente: la espera de restauración ya no se reinicia con cada ciclo de polling.
- Smart Focus estabiliza el último monitor válido durante cambios transitorios de foco.
- La pausa fullscreen pasa a ser opcional y queda desactivada por defecto.
- Página Monitores rediseñada con intensidad general o individual y vista previa por pantalla.
- Toggles accesibles con patrón de interruptor, estados deshabilitados claros y confirmación al aplicar.
- Migración automática al esquema de configuración 3.

## 2.0.0

- Motor de overlays click-through que no acepta foco.
- Modos Cursor, Smart Focus por ventana activa y oscurecimiento fijo.
- Preferencias visuales por monitor con opacidad independiente.
- Peek temporal y atajos globales configurables.
- Pausa fullscreen y exclusiones por ejecutable.
- Perfiles Trabajo, Gaming y Noche, más perfiles personalizados.
- Configuración atómica en AppData y migración del formato anterior.
- Detección de cambios de monitor, resolución, orientación y DPI.
- UI moderna, tray completo, inicio con Windows y logging.
- Pipeline reproducible para EXE e instalador por usuario.
