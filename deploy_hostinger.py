#!/usr/bin/env python3
"""Despliega la web de La Fortaleza a Hostinger por FTP(S).

Credenciales: se leen de ~/.netrc (nunca se pasan por argumento ni se imprimen).
Formato esperado en ~/.netrc (chmod 600):

    machine ftp.mistercuarter.es
    login TU_USUARIO_FTP
    password TU_CONTRASEÑA_FTP

Uso:
    python3 deploy_hostinger.py                # despliegue completo
    python3 deploy_hostinger.py --dry-run      # solo lista lo que subiría
    python3 deploy_hostinger.py --host X       # otro host FTP
    python3 deploy_hostinger.py --remote /public_html/otra-carpeta
"""
import argparse
import ftplib
import netrc
import os
import posixpath
import sys
from pathlib import Path

LOCAL = Path(__file__).resolve().parent
EXCLUDE_DIRS = {".claude", "__pycache__", ".git"}
EXCLUDE_FILES = {".DS_Store", "deploy_hostinger.py"}

def iter_files():
    for root, dirs, files in os.walk(LOCAL):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for f in sorted(files):
            if f in EXCLUDE_FILES:
                continue
            p = Path(root) / f
            yield p, p.relative_to(LOCAL).as_posix()

def ensure_dir(ftp, remote_dir):
    parts = [p for p in remote_dir.split("/") if p]
    path = ""
    for part in parts:
        path += "/" + part
        try:
            ftp.mkd(path)
        except ftplib.error_perm:
            pass  # ya existe

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="ftp.mistercuarter.es")
    ap.add_argument("--remote", default="/public_html/fortaleza")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--plain", action="store_true", help="FTP sin TLS (si FTPS falla)")
    args = ap.parse_args()

    files = list(iter_files())
    total = sum(p.stat().st_size for p, _ in files)
    print(f"{len(files)} archivos · {total/1e6:.1f} MB → {args.host}:{args.remote}")

    if args.dry_run:
        for _, rel in files:
            print("  ", rel)
        return

    try:
        auth = netrc.netrc().authenticators(args.host)
    except FileNotFoundError:
        sys.exit("No existe ~/.netrc — crea el fichero con las credenciales FTP (ver cabecera).")
    if not auth:
        sys.exit(f"~/.netrc no tiene entrada para «machine {args.host}».")
    user, _, pwd = auth

    ftp_cls = ftplib.FTP if args.plain else ftplib.FTP_TLS
    ftp = ftp_cls(args.host, timeout=60)
    ftp.login(user, pwd)
    if not args.plain:
        ftp.prot_p()
    ftp.set_pasv(True)

    ensure_dir(ftp, args.remote)
    done = 0
    made = set()
    for p, rel in files:
        rdir = posixpath.dirname(rel)
        if rdir and rdir not in made:
            ensure_dir(ftp, posixpath.join(args.remote, rdir))
            made.add(rdir)
        with open(p, "rb") as fh:
            ftp.storbinary(f"STOR {posixpath.join(args.remote, rel)}", fh, blocksize=1 << 16)
        done += 1
        print(f"[{done}/{len(files)}] {rel}")
    ftp.quit()
    print("✅ Despliegue completo → https://mistercuarter.es/fortaleza/")

if __name__ == "__main__":
    main()
