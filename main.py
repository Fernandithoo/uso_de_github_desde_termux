#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# github_manager.py
# script para manejar repos de github desde termux sin andar
# copiando comandos a cada rato. lista repos, clona, deja editar
# archivos y sube los cambios solo.

import os
import sys
import json
import subprocess
import getpass
import shutil
from pathlib import Path
from datetime import datetime

# instala lo que falte antes de arrancar
def instalar_dependencias():
    try:
        import requests  # noqa: F401
    except ImportError:
        print(">> falta 'requests', instalando...")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "requests", "--break-system-packages"],
            check=True,
        )

    if shutil.which("git") is None:
        print(">> no tienes git, lo instalo con pkg...")
        subprocess.run(["pkg", "install", "-y", "git"])

    if shutil.which("nano") is None and shutil.which("vi") is None:
        print(">> instalando nano para editar archivos...")
        subprocess.run(["pkg", "install", "-y", "nano"])


instalar_dependencias()
import requests  # noqa: E402


# colores (paleta cyberpunk, rosa/cian/violeta)
class C:
    ROSA = "\033[38;5;198m"
    CYAN = "\033[38;5;51m"
    VIOLETA = "\033[38;5;135m"
    VERDE = "\033[38;5;46m"
    ROJO = "\033[38;5;196m"
    AMARILLO = "\033[38;5;226m"
    GRIS = "\033[38;5;244m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


def limpiar():
    os.system("clear" if os.name != "nt" else "cls")


def banner():
    limpiar()
    print(f"{C.CYAN}{C.BOLD}")
    print(r"""   ▄████  ██░ ██  ███▄ ▄███▓
  ██▒ ▀█▒▓██░ ██▒▓██▒▀█▀ ██▒
 ▒██░▄▄▄░▒██▀▀██░▓██    ▓██░
 ░▓█  ██▓░▓█ ░██ ▒██    ▒██ 
 ░▒▓███▀▒░▓█▒░██▓▒██▒   ░██▒
  ░▒   ▒  ▒ ░░▒░▒░ ▒░   ░  ░
   ░   ░  ▒ ░▒░ ░░  ░      ░
 ░ ░   ░  ░  ░░ ░░      ░   
       ░  ░  ░  ░       ░   """)
    print(f"{C.ROSA}{C.BOLD}      github manager{C.RESET}")
    print(f"{C.GRIS}      tus repos, sin salir de la terminal{C.RESET}\n")


def pausa():
    input(f"\n{C.GRIS}(enter para seguir){C.RESET}")


def titulo(texto):
    print(f"\n{C.VIOLETA}{C.BOLD}-- {texto} --{C.RESET}\n")


def error(texto):
    print(f"{C.ROJO}x {texto}{C.RESET}")


def ok(texto):
    print(f"{C.VERDE}+ {texto}{C.RESET}")


def aviso(texto):
    print(f"{C.AMARILLO}! {texto}{C.RESET}")


# config / token guardado en local
CONFIG_PATH = Path.home() / ".ghmanager_config.json"
PROYECTOS_DIR = Path.home() / "ghmanager_proyectos"
API_URL = "https://api.github.com"

PROYECTOS_DIR.mkdir(exist_ok=True)


def cargar_config():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    return {}


def guardar_config(config):
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f)
    os.chmod(CONFIG_PATH, 0o600)  # solo el usuario puede leerlo


def configurar_token():
    banner()
    titulo("token de github")
    print(f"{C.GRIS}necesitas un Personal Access Token (classic) con permiso 'repo'.")
    print("lo generas gratis en: https://github.com/settings/tokens")
    print(f"(dale a 'Generate new token (classic)' y marca 'repo'){C.RESET}\n")

    token = getpass.getpass(f"{C.CYAN}pega tu token (no se ve en pantalla): {C.RESET}").strip()
    if not token:
        error("no pusiste ningún token.")
        pausa()
        return None

    headers = {"Authorization": f"token {token}"}
    r = requests.get(f"{API_URL}/user", headers=headers)
    if r.status_code != 200:
        error("token inválido o no hay conexión, intenta otra vez.")
        pausa()
        return None

    usuario = r.json()["login"]
    config = {"token": token, "usuario": usuario}
    guardar_config(config)
    ok(f"listo, sesión iniciada como {usuario}.")
    pausa()
    return config


def obtener_config():
    config = cargar_config()
    if "token" not in config:
        aviso("todavía no tienes token configurado.")
        pausa()
        config = configurar_token()
    return config


def headers_api(config):
    return {"Authorization": f"token {config['token']}"}


# corre un comando git en 'cwd' mostrando qué se ejecuta
def git(args, cwd, mostrar=True):
    cmd = ["git"] + args
    if mostrar:
        print(f"{C.GRIS}$ {' '.join(cmd)}{C.RESET}")
    resultado = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    salida = (resultado.stdout + resultado.stderr).strip()
    if salida and mostrar:
        print(salida)
    return resultado.returncode == 0, salida


# ------------------------------------------------------------------
def listar_repos(config):
    repos = []
    pagina = 1
    while True:
        r = requests.get(
            f"{API_URL}/user/repos",
            headers=headers_api(config),
            params={"per_page": 100, "page": pagina, "sort": "updated"},
        )
        if r.status_code != 200:
            error(f"no pude traer los repos ({r.status_code}).")
            return []
        datos = r.json()
        if not datos:
            break
        repos.extend(datos)
        if len(datos) < 100:
            break
        pagina += 1
    return repos


def pantalla_repos(config):
    # esto es lo primero que se ve al abrir el script
    titulo(f"tus repos - {config.get('usuario','')}")
    print(f"{C.GRIS}cargando...{C.RESET}")
    repos = listar_repos(config)
    if not repos:
        aviso("no encontré repos (o el token no tiene acceso).")
        return []

    limpiar()
    banner()
    titulo(f"tus repos - {config.get('usuario','')}")
    for i, repo in enumerate(repos, 1):
        visibilidad = f"{C.ROSA}privado{C.RESET}" if repo["private"] else f"{C.CYAN}público{C.RESET}"
        desc = repo.get("description") or "sin descripción"
        local = "(clonado)" if (PROYECTOS_DIR / repo["name"]).exists() else ""
        print(f" {C.AMARILLO}[{i}]{C.RESET} {C.BOLD}{repo['name']}{C.RESET} ({visibilidad}) {C.GRIS}{local}{C.RESET}")
        print(f"      {C.GRIS}{desc}{C.RESET}")
    return repos


def preparar_proyecto_local(repo, config):
    # clona el repo si no lo tienes, o hace pull si ya está
    ruta = PROYECTOS_DIR / repo["name"]
    token = config["token"]
    url_con_token = repo["clone_url"].replace("https://", f"https://{token}@")

    if not ruta.exists():
        titulo(f"clonando '{repo['name']}'...")
        exito, _ = git(["clone", url_con_token, str(ruta)], cwd=PROYECTOS_DIR)
        if not exito:
            error("no se pudo clonar.")
            return None
        ok("clonado.")
    else:
        titulo(f"actualizando '{repo['name']}' (git pull)...")
        # actualizamos el remoto con el token para que el push funcione después
        git(["remote", "set-url", "origin", url_con_token], cwd=ruta, mostrar=False)
        exito, salida = git(["pull"], cwd=ruta)
        if not exito:
            aviso("no se pudo actualizar solo (puede que haya conflictos).")
    pausa()
    return ruta


def crear_repo_nuevo(config):
    banner()
    titulo("crear repo nuevo")
    nombre = input(f"{C.CYAN}nombre: {C.RESET}").strip()
    if not nombre:
        return
    privado = input(f"{C.CYAN}¿privado? (s/n): {C.RESET}").strip().lower() == "s"
    r = requests.post(
        f"{API_URL}/user/repos",
        headers=headers_api(config),
        json={"name": nombre, "private": privado, "auto_init": True},
    )
    if r.status_code == 201:
        ok(f"'{nombre}' creado en github.")
    else:
        error(f"no se pudo crear: {r.json().get('message')}")
    pausa()


def listar_contenido(ruta_actual):
    elementos = sorted(
        [p for p in ruta_actual.iterdir() if p.name != ".git"],
        key=lambda p: (p.is_file(), p.name.lower()),
    )
    return elementos


def abrir_editor(ruta_archivo):
    editor = os.environ.get("EDITOR") or ("nano" if shutil.which("nano") else "vi")
    subprocess.run([editor, str(ruta_archivo)])


def subir_cambios(ruta_repo, mensaje):
    # add + commit + push
    titulo("subiendo cambios")
    git(["add", "-A"], cwd=ruta_repo)
    exito, salida = git(["commit", "-m", mensaje], cwd=ruta_repo)
    if not exito and "nothing to commit" in salida.lower():
        aviso("no había nada que subir.")
        return
    exito, _ = git(["push"], cwd=ruta_repo)
    if exito:
        ok("subido a github.")
    else:
        error("falló el push, revisa tu conexión o el token.")


def ver_estado(ruta_repo):
    titulo("git status")
    git(["status", "-s"], cwd=ruta_repo)
    pausa()


def ver_historial(ruta_repo):
    titulo("últimos commits")
    git(["log", "--oneline", "-10"], cwd=ruta_repo)
    pausa()


def explorador_proyecto(repo_nombre, ruta_repo):
    ruta_actual = ruta_repo
    while True:
        limpiar()
        banner()
        rel = ruta_actual.relative_to(ruta_repo)
        titulo(f"{repo_nombre}  /{rel if str(rel) != '.' else ''}")

        elementos = listar_contenido(ruta_actual)
        for i, item in enumerate(elementos, 1):
            if item.is_dir():
                print(f" {C.AMARILLO}[{i}]{C.RESET} {C.CYAN}{item.name}/{C.RESET}")
            else:
                print(f" {C.AMARILLO}[{i}]{C.RESET} {item.name}")

        print(f"\n {C.VIOLETA}[n]{C.RESET} archivo nuevo   {C.VIOLETA}[c]{C.RESET} carpeta nueva")
        print(f" {C.VIOLETA}[e]{C.RESET} git status   {C.VIOLETA}[h]{C.RESET} historial")
        print(f" {C.VIOLETA}[p]{C.RESET} subir cambios")
        if str(rel) != ".":
            print(f" {C.VIOLETA}[..]{C.RESET} carpeta anterior")
        print(f" {C.VIOLETA}[v]{C.RESET} volver a la lista de repos   {C.VIOLETA}[s]{C.RESET} salir")

        eleccion = input(f"\n{C.CYAN}> {C.RESET}").strip().lower()

        if eleccion == "v":
            return
        if eleccion == "s":
            despedida()
        if eleccion == ".." and str(rel) != ".":
            ruta_actual = ruta_actual.parent
            continue
        if eleccion == "n":
            nombre = input("Nombre del nuevo archivo: ").strip()
            if nombre:
                (ruta_actual / nombre).touch()
                ok(f"'{nombre}' creado.")
                if input("¿lo editas ahora? (s/n): ").strip().lower() == "s":
                    abrir_editor(ruta_actual / nombre)
                    mensaje = input("mensaje de commit (enter = uno automático): ").strip()
                    if not mensaje:
                        mensaje = f"crea {nombre} - {datetime.now():%Y-%m-%d %H:%M}"
                    subir_cambios(ruta_repo, mensaje)
            pausa()
            continue
        if eleccion == "c":
            nombre = input("nombre de la carpeta: ").strip()
            if nombre:
                (ruta_actual / nombre).mkdir(exist_ok=True)
                ok(f"'{nombre}' creada.")
            pausa()
            continue
        if eleccion == "e":
            ver_estado(ruta_repo)
            continue
        if eleccion == "h":
            ver_historial(ruta_repo)
            continue
        if eleccion == "p":
            mensaje = input("mensaje de commit: ").strip() or f"actualización - {datetime.now():%Y-%m-%d %H:%M}"
            subir_cambios(ruta_repo, mensaje)
            pausa()
            continue

        # si escribió un número, es que eligió un archivo/carpeta de la lista
        if not eleccion.isdigit() or not (1 <= int(eleccion) <= len(elementos)):
            error("esa opción no existe.")
            pausa()
            continue

        elegido = elementos[int(eleccion) - 1]

        if elegido.is_dir():
            ruta_actual = elegido
            continue

        limpiar()
        banner()
        titulo(elegido.name)
        print(f" {C.AMARILLO}[1]{C.RESET} editar")
        print(f" {C.AMARILLO}[2]{C.RESET} ver contenido")
        print(f" {C.AMARILLO}[3]{C.RESET} renombrar")
        print(f" {C.AMARILLO}[4]{C.RESET} eliminar")
        print(f" {C.AMARILLO}[5]{C.RESET} cancelar")
        accion = input(f"\n{C.CYAN}> {C.RESET}").strip()

        if accion == "1":
            abrir_editor(elegido)
            ok("editor cerrado.")
            mensaje = input("mensaje de commit (enter = uno automático): ").strip()
            if not mensaje:
                mensaje = f"edita {elegido.name} - {datetime.now():%Y-%m-%d %H:%M}"
            subir_cambios(ruta_repo, mensaje)
            pausa()

        elif accion == "2":
            titulo(elegido.name)
            try:
                print(elegido.read_text(errors="replace"))
            except Exception as e:
                error(f"no pude leer el archivo: {e}")
            pausa()

        elif accion == "3":
            nuevo_nombre = input("nuevo nombre: ").strip()
            if nuevo_nombre:
                destino = elegido.parent / nuevo_nombre
                elegido.rename(destino)
                ok("renombrado.")
                mensaje = f"renombra {elegido.name} a {nuevo_nombre}"
                subir_cambios(ruta_repo, mensaje)
            pausa()

        elif accion == "4":
            confirmar = input(f"{C.ROJO}seguro que quieres eliminar '{elegido.name}'? (s/n): {C.RESET}").strip().lower()
            if confirmar == "s":
                elegido.unlink()
                ok("eliminado localmente.")
                mensaje = f"elimina {elegido.name}"
                subir_cambios(ruta_repo, mensaje)
            pausa()


def despedida():
    limpiar()
    print(f"{C.CYAN}{C.BOLD}chao{C.RESET}")
    sys.exit(0)


def menu_principal():
    config = obtener_config()
    if config is None:
        return

    while True:
        banner()
        repos = pantalla_repos(config)

        print(f"\n {C.VIOLETA}[número]{C.RESET} elegir proyecto")
        print(f" {C.VIOLETA}[r]{C.RESET} recargar   {C.VIOLETA}[n]{C.RESET} crear repo nuevo")
        print(f" {C.VIOLETA}[t]{C.RESET} cambiar token   {C.VIOLETA}[s]{C.RESET} salir")

        eleccion = input(f"\n{C.CYAN}> {C.RESET}").strip().lower()

        if eleccion == "s":
            despedida()
        elif eleccion == "r":
            continue
        elif eleccion == "n":
            crear_repo_nuevo(config)
        elif eleccion == "t":
            nuevo_config = configurar_token()
            if nuevo_config:
                config = nuevo_config
        elif eleccion.isdigit() and repos and 1 <= int(eleccion) <= len(repos):
            repo = repos[int(eleccion) - 1]
            ruta_repo = preparar_proyecto_local(repo, config)
            if ruta_repo:
                explorador_proyecto(repo["name"], ruta_repo)
        else:
            error("esa opción no existe.")
            pausa()


if __name__ == "__main__":
    try:
        menu_principal()
    except KeyboardInterrupt:
        despedida()
