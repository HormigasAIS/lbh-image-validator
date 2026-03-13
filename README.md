# 🐜 lbh-image-validator

Validador soberano de propiedad intelectual usando el protocolo LBH.

## ¿Qué hace?

Firma criptográficamente imágenes PNG generando un pasaporte LBH:

| Archivo | Contenido |
|---|---|
| `.identity.lbh` | Propietario, licencia, autoridad |
| `.signature` | HMAC-SHA256 + SHA256 + timestamp |
| `.manifest.json` | Certificado verificable sin internet |

## Uso

```bash
# Sellar imagen
python3 lbh_sello.py firmar imagen.png "Nombre-Propietario"

# Verificar integridad
python3 lbh_sello.py verificar imagen.png
Licencias
Freemium — uso personal, hasta 5 imágenes
Premium — ilimitado + API
Enterprise — integración corporativa + SLA soberano
Fundador
CLHQ — Cristhiam Leonardo Hernández Quiñonez
Protocolo LBH v1.1 | El Salvador 2026
DOI: 10.5281/zenodo.17767205
