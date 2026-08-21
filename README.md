# uso_de_github_desde_termux


Es un script en Python que hice para manejar mis repositorios de GitHub directamente desde la terminal de mi celular (uso Termux en Android), sin tener que escribir comandos de git a mano cada vez.


Lo que hace:

Al abrirlo, muestra la lista de mis repos de GitHub (usando la API de GitHub con la librería requests).


Puedo elegir uno con un número, y el script lo clona automáticamente (o lo actualiza si ya lo tenía descargado).


Adentro puedo ver los archivos y carpetas, y elegir editar, ver contenido, renombrar o eliminar cualquier archivo.


Cuando edito un archivo, se abre un editor de texto (nano) y, al cerrarlo, el script hace automáticamente git add, commit y push para subir los cambios a GitHub.


También deja crear repos nuevos, ver el historial de commits y el estado del repositorio.
