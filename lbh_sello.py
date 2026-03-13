#!/usr/bin/env python3
"""
LBH Image Validator — Hormiga de Sello
Firma y verifica propiedad intelectual con protocolo LBH
CLHQ / HormigasAIS 2026
"""

import hashlib
import hmac
import json
import os
import time
import sys

AUTORIDAD = "CLHQ"
VERSION_LBH = "1.1"
SECRET_KEY = os.environ.get("LBH_SECRET", "hormigasais-soberano-2026")

def firmar_imagen(ruta_imagen, propietario, licencia="freemium"):
    if not os.path.exists(ruta_imagen):
        print(f"Imagen no encontrada: {ruta_imagen}")
        return None

    with open(ruta_imagen, "rb") as f:
        contenido = f.read()

    sha256 = hashlib.sha256(contenido).hexdigest()
    timestamp = int(time.time())
    payload = f"{sha256}|{propietario}|{timestamp}"
    firma = hmac.new(SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()

    nombre_base = os.path.splitext(ruta_imagen)[0]

    with open(f"{nombre_base}.identity.lbh", "w") as f:
        f.write(f"ASSET_ID: {os.path.basename(ruta_imagen)}\n")
        f.write(f"ROL: Propiedad-Intelectual\n")
        f.write(f"CLASE: IMAGEN\n")
        f.write(f"PROPIETARIO: {propietario}\n")
        f.write(f"LICENCIA: {licencia}\n")
        f.write(f"AUTORIDAD_RAIZ: {AUTORIDAD}\n")
        f.write(f"VERSION_LBH: {VERSION_LBH}\n")

    with open(f"{nombre_base}.signature", "w") as f:
        f.write(f"ISSUED_BY: {AUTORIDAD}\n")
        f.write(f"SHA256: {sha256}\n")
        f.write(f"SIGNATURE: {firma}\n")
        f.write(f"TIMESTAMP: {timestamp}\n")

    manifiesto = {
        "asset": os.path.basename(ruta_imagen),
        "propietario": propietario,
        "licencia": licencia,
        "sha256": sha256,
        "timestamp": timestamp,
        "autoridad": AUTORIDAD,
        "version_lbh": VERSION_LBH
    }
    with open(f"{nombre_base}.manifest.json", "w") as f:
        json.dump(manifiesto, f, indent=2)

    print(f"SELLADO: {os.path.basename(ruta_imagen)}")
    print(f"Propietario : {propietario}")
    print(f"SHA256      : {sha256[:16]}...")
    print(f"Firma       : {firma[:16]}...")
    print(f"Timestamp   : {timestamp}")
    return firma

def verificar_imagen(ruta_imagen):
    nombre_base = os.path.splitext(ruta_imagen)[0]
    sig_path = f"{nombre_base}.signature"

    if not os.path.exists(sig_path):
        print(f"SIN FIRMA LBH: {ruta_imagen}")
        return False

    with open(ruta_imagen, "rb") as f:
        contenido = f.read()
    sha256_actual = hashlib.sha256(contenido).hexdigest()

    datos = {}
    with open(sig_path) as f:
        for linea in f:
            if ":" in linea:
                k, v = linea.strip().split(":", 1)
                datos[k.strip()] = v.strip()

    sha256_original = datos.get("SHA256", "")
    timestamp = datos.get("TIMESTAMP", "")

    if sha256_actual != sha256_original:
        print(f"INTEGRIDAD COMPROMETIDA: {ruta_imagen}")
        return False

    print(f"IMAGEN VALIDA: {os.path.basename(ruta_imagen)}")
    print(f"SHA256   : {sha256_actual[:16]}... OK")
    print(f"Timestamp: {timestamp}")
    return True

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python3 lbh_sello.py firmar <imagen.png> <propietario>")
        print("     python3 lbh_sello.py verificar <imagen.png>")
        sys.exit(1)

    cmd = sys.argv[1]
    imagen = sys.argv[2]

    if cmd == "firmar":
        propietario = sys.argv[3] if len(sys.argv) > 3 else "CLHQ"
        firmar_imagen(imagen, propietario)
    elif cmd == "verificar":
        verificar_imagen(imagen)
