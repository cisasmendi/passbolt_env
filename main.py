#!/usr/bin/env python3
"""
Passbolt CLI - Descarga recursos de Passbolt via GPGAuth.

Uso:
  passbolt-dwn --list
  passbolt-dwn --download RESOURCE_ID -j
  passbolt-dwn --download RESOURCE_ID -e
  passbolt-dwn --download RESOURCE_ID -j -e
"""

import argparse
import json
import os
import sys
import urllib3
from pathlib import Path

import gnupg
import requests

from config import config

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class PassboltClient:
    def __init__(self):
        config.validate()

        self.url = config.passbolt_url
        self.passphrase = config.passphrase

        # Leer la clave: primero desde archivo (PRIVATE_KEY_FILE), luego desde env var
        key_file = os.getenv("PRIVATE_KEY_FILE")
        if key_file:
            # utf-8-sig elimina automáticamente el BOM si existe
            with open(key_file, "r", encoding="utf-8-sig") as f:
                private_key = f.read()
        else:
            # Fallback: limpiar BOM, comillas y \n literales del env var
            private_key = config.private_key.lstrip("\ufeff").strip().strip('"').strip("'")
            private_key = private_key.replace("\\n", "\n")

        self.gpg_home = "/tmp/.gnupg"
        os.makedirs(self.gpg_home, exist_ok=True)
        self.gpg = gnupg.GPG(gnupghome=self.gpg_home)

        result = self.gpg.import_keys(private_key)
        if not result.count:
            print("stderr:", result.stderr)
            raise RuntimeError("No se pudo importar la clave GPG")
        self.fingerprint = result.fingerprints[0]
        print(f"[GPG] Clave importada: {self.fingerprint}")

        self.session = requests.Session()
        self.session.verify = False

        output_path = os.getenv("OUTPUT_DIR", "/app/out")
        self.out_dir = Path(output_path)
        self.out_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Autenticación GPGAuth (challenge-response)
    # ------------------------------------------------------------------
    def authenticate(self):
        print("\n[GPGAuth] Paso 1: Solicitando challenge...")
        resp = self.session.post(
            f"{self.url}/auth/login.json",
            json={"data": {"gpg_auth": {"keyid": self.fingerprint}}},
        )

        encrypted_token = resp.headers.get("X-GPGAuth-User-Auth-Token")
        if not encrypted_token:
            print("Headers:", dict(resp.headers))
            print("Body:", resp.text)
            raise RuntimeError("No se recibió X-GPGAuth-User-Auth-Token")

        encrypted_token = requests.utils.unquote(encrypted_token).replace("\\+", " ")

        print("[GPGAuth] Paso 2: Descifrando challenge...")
        decrypted = self.gpg.decrypt(encrypted_token, passphrase=self.passphrase)
        if not decrypted.ok:
            raise RuntimeError(f"Error descifrando token: {decrypted.status}")

        print("[GPGAuth] Paso 3: Completando login...")
        resp = self.session.post(
            f"{self.url}/auth/login.json",
            json={
                "data": {
                    "gpg_auth": {
                        "keyid": self.fingerprint,
                        "user_token_result": str(decrypted),
                    }
                }
            },
        )
        if resp.status_code != 200:
            print("Status:", resp.status_code, "Body:", resp.text)
            raise RuntimeError("Login GPGAuth fallido")

        print("[GPGAuth] Autenticación exitosa!")

    # ------------------------------------------------------------------
    # --list
    # ------------------------------------------------------------------
    def list_resources(self):
        self.authenticate()

        print("\nObteniendo lista de recursos...")
        resp = self.session.get(f"{self.url}/resources.json")
        resp.raise_for_status()
        resources = resp.json()["body"]

        print(f"\n{'ID':<40} {'NOMBRE':<35} URI")
        print("-" * 110)
        for r in resources:
            print(f"{r.get('id',''):<40} {r.get('name',''):<35} {r.get('uri','')}")

        out_file = self.out_dir / "resources_list.json"
        out_file.write_text(json.dumps(resources, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nLista guardada en: {out_file}")

    # ------------------------------------------------------------------
    # --download RESOURCE_ID [-j] [-e]
    # ------------------------------------------------------------------
    def download_resource(self, resource_id: str, as_json: bool, as_env: bool):
        if not as_json and not as_env:
            as_json = True  # por defecto JSON

        self.authenticate()

        # Metadatos del recurso
        print(f"\nObteniendo metadatos del recurso {resource_id}...")
        resp = self.session.get(f"{self.url}/resources/{resource_id}.json")
        resp.raise_for_status()
        resource = resp.json()["body"]

        field_names_map = {}
        encrypted_metadata = resource.get("metadata", "")
        if encrypted_metadata.startswith("-----BEGIN PGP MESSAGE-----"):
            dec_meta = self.gpg.decrypt(encrypted_metadata, passphrase=self.passphrase)
            if dec_meta.ok:
                meta = json.loads(str(dec_meta))
                for cf in meta.get("custom_fields", []):
                    field_names_map[cf["id"]] = cf.get(
                        "metadata_key", cf.get("label", cf.get("name", cf["id"]))
                    )

        # Secreto cifrado
        print("Obteniendo secreto...")
        resp = self.session.get(f"{self.url}/secrets/resource/{resource_id}.json")
        resp.raise_for_status()
        secret_body = resp.json()["body"]
        encrypted_secret = secret_body["data"] if isinstance(secret_body, dict) else secret_body

        print("Descifrando secreto...")
        decrypted = self.gpg.decrypt(encrypted_secret, passphrase=self.passphrase)
        if not decrypted.ok:
            raise RuntimeError(f"Error GPG: {decrypted.status}")

        data = json.loads(str(decrypted))
        custom_fields = data.get("custom_fields", [])
        result = {}

        if isinstance(custom_fields, list):
            for field in custom_fields:
                fid = field.get("id", "")
                value = field.get("secret_value", field.get("value", ""))
                label = field_names_map.get(fid, fid)
                result[label] = str(value)
        else:
            result = {k: str(v) for k, v in data.items() if k != "object_type"}

        # Mostrar en consola
        name = resource.get("name", resource_id)
        print(f"\n=== RECURSO: {name} ===")
        for k, v in result.items():
            print(f"  {k}={v}")

        # Guardar archivos de salida
        if as_json:
            out_file = self.out_dir / f"resource_{resource_id}.json"
            payload = {
                **result,
                "_resource_name": name,
                "_resource_id": resource_id,
                "_resource_uri": resource.get("uri", ""),
            }
            out_file.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"Guardado JSON: {out_file}")

        if as_env:
            out_file = self.out_dir / f"resource_{resource_id}.env"
            lines = [
                f"# Variables del recurso: {name}",
                f"# Resource ID: {resource_id}",
                f"# URI: {resource.get('uri', '')}",
                "",
            ]
            for k, v in result.items():
                escaped = v.replace('"', '\\"').replace("$", "\\$")
                lines.append(f'{k}="{escaped}"')
            out_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
            print(f"Guardado ENV:  {out_file}")


# ------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        prog="passbolt-dwn",
        description="Descarga recursos de Passbolt via GPGAuth",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  passbolt-dwn --list
  passbolt-dwn --download RESOURCE_ID -j
  passbolt-dwn --download RESOURCE_ID -e
  passbolt-dwn --download RESOURCE_ID -j -e
        """,
    )

    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--list", action="store_true", help="Listar todos los recursos")
    action.add_argument("--download", metavar="RESOURCE_ID", help="Descargar un recurso por ID")

    parser.add_argument("-j", "--json", dest="as_json", action="store_true", help="Salida en formato JSON")
    parser.add_argument("-e", "--env", dest="as_env", action="store_true", help="Salida en formato ENV")

    args = parser.parse_args()

    try:
        client = PassboltClient()
        if args.list:
            client.list_resources()
        else:
            client.download_resource(args.download, as_json=args.as_json, as_env=args.as_env)
        print("\nOperación completada exitosamente.")
    except Exception as exc:
        print(f"\nError: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()