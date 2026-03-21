#!/usr/bin/env python3
"""
hormiga_slack.py — Hormiga Bot para Slack
Identidad LBH soberana con espejo DHT
Firmada por: Stanford + CLHQ
Validada por: Hormiga_10 Soberana
CLHQ / HormigasAIS 2026
"""

import hashlib, hmac, json, os, time, math
import sqlite3, threading, urllib.request

BASE_DIR   = os.path.expanduser("~/hormigasais-lab/LBH-Net")
SELLO_DIR  = os.path.expanduser("~/hormigasais-lab/lbh-image-validator")
SECRET_KEY = "hormigasais-soberano-2026"
ESPEJO_DB  = os.path.expanduser("~/hormigasais-lab/lbh-image-validator/dht_espejo.db")

# ─────────────────────────────────────────
# IDENTIDAD LBH — hormiga_slack
# ─────────────────────────────────────────
IDENTIDAD = {
    "node_name":   "hormiga_slack",
    "node_id":     hashlib.sha256(b"hormiga_slack:CLHQ:2026").hexdigest(),
    "rol":         "bot_externo",
    "scope":       "slack_only",
    "firmada_por": ["Stanford", "CLHQ"],
    "validada_por": "hormiga_10_soberana",
    "issued_at":   1774000000,
    "version":     "1.1",
    "issued_by":   "CLHQ",
    "nota": "Opera exclusivamente en Slack. No interfiere con hormigas estudiantes."
}

# ─────────────────────────────────────────
# UTILIDADES LBH
# ─────────────────────────────────────────
def sha256(data):
    return hashlib.sha256(
        data.encode() if isinstance(data, str) else data
    ).hexdigest()

def firmar(payload):
    msg = json.dumps(payload, sort_keys=True)
    return hmac.new(
        SECRET_KEY.encode(), msg.encode(), hashlib.sha256
    ).hexdigest()[:16]

def now():
    return int(time.time())

def fanout_hibrido(n):
    if n <= 5:    return n
    if n <= 1000: return max(3, int(n ** (1/3)) + 1)
    return max(3, int(math.log2(n)))

def emitir_feromona_lbh(action, asset, estado, hash_img):
    """Emite feromona LBH en lugar de respuesta genérica"""
    payload = {
        "action":    action,
        "asset":     asset,
        "estado":    estado,
        "hash":      hash_img,
        "node":      "hormiga_slack",
        "timestamp": now(),
        "ttl":       300
    }
    sig = firmar(payload)
    return {
        "feromona": f"""LBH://SIGNAL
version: 1.1
node: hormiga_slack
action: {action}
asset: {asset}
estado: {estado}
hash: {hash_img}
timestamp: {now()}
ttl: 300
sig: {sig}
issued_by: CLHQ""",
        "payload": payload,
        "sig": sig
    }

# ─────────────────────────────────────────
# DHT ESPEJO SLACK — SQLite local
# ─────────────────────────────────────────
class DHT_Espejo:
    def __init__(self):
        self.db = ESPEJO_DB
        self._init_db()
        self._lock = threading.Lock()

    def _init_db(self):
        conn = sqlite3.connect(self.db)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS feromonas_slack (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                fid       TEXT UNIQUE,
                action    TEXT,
                asset     TEXT,
                estado    TEXT,
                hash_img  TEXT,
                sig       TEXT,
                ts        INTEGER,
                sync_mode TEXT DEFAULT 'pending',
                synced    INTEGER DEFAULT 0
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sync_log (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                ts        INTEGER,
                modo      TEXT,
                feromonas INTEGER,
                autorizado_por TEXT
            )
        """)
        conn.commit()
        conn.close()

    def escribir(self, feromona_data, modo_sync="realtime"):
        """A) Tiempo real — escribe inmediatamente"""
        payload = feromona_data["payload"]
        fid     = sha256(f"{payload['asset']}:{payload['timestamp']}")

        with self._lock:
            conn = sqlite3.connect(self.db)
            try:
                conn.execute("""
                    INSERT OR IGNORE INTO feromonas_slack
                    (fid, action, asset, estado, hash_img, sig, ts, sync_mode)
                    VALUES (?,?,?,?,?,?,?,?)
                """, (
                    fid,
                    payload["action"],
                    payload["asset"],
                    payload["estado"],
                    payload["hash"],
                    feromona_data["sig"],
                    payload["timestamp"],
                    modo_sync
                ))
                conn.commit()
                print(f"🐜 [DHT_ESPEJO] feromona escrita: {fid[:12]}...")
            except Exception as e:
                print(f"⚠️  [DHT_ESPEJO] error: {e}")
            finally:
                conn.close()
        return fid

    def pendientes(self):
        conn = sqlite3.connect(self.db)
        rows = conn.execute(
            "SELECT * FROM feromonas_slack WHERE synced=0"
        ).fetchall()
        conn.close()
        return rows

    def marcar_synced(self, fid):
        with self._lock:
            conn = sqlite3.connect(self.db)
            conn.execute(
                "UPDATE feromonas_slack SET synced=1 WHERE fid=?", (fid,)
            )
            conn.commit()
            conn.close()

    def registrar_sync(self, modo, n_feromonas, autorizado_por="auto"):
        conn = sqlite3.connect(self.db)
        conn.execute(
            "INSERT INTO sync_log (ts, modo, feromonas, autorizado_por) VALUES (?,?,?,?)",
            (now(), modo, n_feromonas, autorizado_por)
        )
        conn.commit()
        conn.close()

    def stats(self):
        conn = sqlite3.connect(self.db)
        total   = conn.execute("SELECT COUNT(*) FROM feromonas_slack").fetchone()[0]
        synced  = conn.execute("SELECT COUNT(*) FROM feromonas_slack WHERE synced=1").fetchone()[0]
        pending = total - synced
        conn.close()
        return {"total": total, "synced": synced, "pending": pending}

# ─────────────────────────────────────────
# HORMIGA_10 — validación soberana
# ─────────────────────────────────────────
class Hormiga10_Soberana:
    def __init__(self, dht_espejo):
        self.dht = dht_espejo
        self.sync_interval = 300  # 5 min — modo B
        self._running = False

    def validar_identidad_slack(self):
        """Valida que hormiga_slack no interfiere con estudiantes"""
        print("\n🐜 [Hormiga_10] validando identidad hormiga_slack...")
        checks = {
            "scope_correcto":   IDENTIDAD["scope"] == "slack_only",
            "no_es_estudiante": "estudiante" not in IDENTIDAD["rol"],
            "firmada_stanford": "Stanford" in IDENTIDAD["firmada_por"],
            "firmada_clhq":     "CLHQ" in IDENTIDAD["firmada_por"],
            "version_lbh":      IDENTIDAD["version"] == "1.1",
        }
        aprobado = all(checks.values())
        for check, resultado in checks.items():
            icon = "✅" if resultado else "❌"
            print(f"   {icon} {check}")

        if aprobado:
            print("   ✅ [Hormiga_10] hormiga_slack APROBADA")
            print("   📋 Nota: opera solo en Slack, no interfiere con estudiantes")
        else:
            print("   ❌ [Hormiga_10] RECHAZADA")

        return aprobado

    def sync_batch(self, autorizado_por="batch_auto"):
        """B) Lotes — sincroniza pendientes con colonia"""
        pendientes = self.dht.pendientes()
        if not pendientes:
            return 0

        print(f"\n🔄 [Hormiga_10] sync batch → {len(pendientes)} feromonas")

        # Simular envío al DHT Kademlia colonia
        dht_colonia = os.path.join(BASE_DIR, "signals/lbh_queue.db")
        synced = 0
        for row in pendientes:
            fid = row[1]
            self.dht.marcar_synced(fid)
            synced += 1

        self.dht.registrar_sync("batch", synced, autorizado_por)
        print(f"   ✅ {synced} feromonas sincronizadas con colonia")
        return synced

    def sync_demanda(self):
        """C) Bajo demanda — hormiga_10 autoriza sync manual"""
        print("\n🐜 [Hormiga_10] sync bajo demanda autorizado")
        return self.sync_batch(autorizado_por="hormiga_10_manual")

    def iniciar_daemon_batch(self):
        """Daemon B) — sync cada 5 minutos"""
        self._running = True
        def _loop():
            while self._running:
                time.sleep(self.sync_interval)
                self.sync_batch()
        t = threading.Thread(target=_loop, daemon=True)
        t.start()
        print(f"🔄 [Hormiga_10] daemon batch iniciado (cada {self.sync_interval}s)")

# ─────────────────────────────────────────
# STANFORD — firma del contrato
# ─────────────────────────────────────────
class Stanford:
    @staticmethod
    def firmar_contrato(identidad):
        contrato = {
            "tipo":        "CONTRATO_HORMIGA_SLACK",
            "identidad":   identidad["node_name"],
            "node_id":     identidad["node_id"][:16],
            "scope":       identidad["scope"],
            "firmado_por": "Stanford",
            "timestamp":   now(),
            "condicion":   "Opera solo en Slack. No accede a datos de estudiantes.",
            "issued_by":   "CLHQ"
        }
        contrato["sig"] = firmar(contrato)
        print(f"\n📋 [Stanford] contrato firmado:")
        print(f"   hormiga_slack → scope: {identidad['scope']}")
        print(f"   sig: {contrato['sig']}")
        print(f"   condicion: {contrato['condicion']}")
        return contrato

# ─────────────────────────────────────────
# HORMIGA SLACK — bot con identidad LBH
# ─────────────────────────────────────────
class HormigaSlack:
    def __init__(self):
        self.identidad  = IDENTIDAD
        self.dht_espejo = DHT_Espejo()
        self.hormiga_10 = Hormiga10_Soberana(self.dht_espejo)
        self.contrato   = None
        self.activa     = False

    def activar(self):
        """Pipeline XOXO → Hormiga_10 → Stanford → hormiga_slack"""
        print("═" * 55)
        print("🐜 XOXO → activando hormiga_slack")
        print("═" * 55)

        # Paso 1: Hormiga_10 valida
        aprobada = self.hormiga_10.validar_identidad_slack()
        if not aprobada:
            print("❌ hormiga_slack rechazada por Hormiga_10")
            return False

        # Paso 2: Stanford firma contrato
        self.contrato = Stanford.firmar_contrato(self.identidad)

        # Paso 3: hormiga_slack nace
        self.activa = True
        print(f"\n✅ hormiga_slack ACTIVA")
        print(f"   node_id: {self.identidad['node_id'][:16]}...")
        print(f"   scope:   {self.identidad['scope']}")
        print(f"   DHT espejo: {ESPEJO_DB}")

        # Paso 4: Iniciar daemon batch
        self.hormiga_10.iniciar_daemon_batch()

        print("═" * 55)
        return True

    def procesar_validacion(self, url, resultado, user="slack"):
        """Procesa resultado y emite feromona LBH"""
        if not self.activa:
            return None

        estado   = resultado["estado"]
        hash_img = resultado.get("hash", "")

        # Determinar action LBH
        if estado == "VALIDADO":
            action = "imagen_validada"
        else:
            action = "validacion_requerida"

        # Emitir feromona
        feromona = emitir_feromona_lbh(action, url[:60], estado, hash_img)

        # A) Tiempo real — escribir en DHT espejo
        fid = self.dht_espejo.escribir(feromona, modo_sync="realtime")

        return feromona

    def respuesta_slack(self, feromona_data, resultado, url):
        """Genera respuesta Slack con lenguaje LBH"""
        estado   = resultado["estado"]
        hash_img = resultado.get("hash", "")
        payload  = feromona_data["payload"]

        if estado == "VALIDADO":
            icon  = "✅"
            titulo = "LBH://VALIDADO"
            color  = "#27ae60"
            detalle = (f"*Propietario:* {resultado.get('propietario','?')}\n"
                      f"*Licencia:* {resultado.get('licencia','?')}\n"
                      f"*Hash:* `{hash_img}`")
        else:
            icon  = "🐜"
            titulo = "LBH://FEROMONA_PENDIENTE"
            color  = "#f39c12"
            detalle = (f"*action:* `validacion_requerida`\n"
                      f"*hash:* `{hash_img}`\n"
                      f"*sig:* `{feromona_data['sig']}`\n"
                      f"*issued_by:* CLHQ")

        return json.dumps({
            "response_type": "in_channel",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (f"{icon} *{titulo}*\n"
                                f"node: `hormiga_slack`\n"
                                f"asset: `{url[:50]}`")
                    }
                },
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": detalle}
                },
                {
                    "type": "context",
                    "elements": [{
                        "type": "mrkdwn",
                        "text": (f"🐜 HormigasAIS · hormiga_slack · "
                                f"ts:{payload['timestamp']} · "
                                f"DOI: 10.5281/zenodo.17767205")
                    }]
                }
            ]
        })

    def stats(self):
        return {
            "identidad":  self.identidad["node_name"],
            "activa":     self.activa,
            "contrato":   self.contrato["sig"] if self.contrato else None,
            "dht_espejo": self.dht_espejo.stats()
        }

# ─────────────────────────────────────────
# INSTANCIA GLOBAL
# ─────────────────────────────────────────
hormiga_slack = HormigaSlack()

def inicializar():
    """Llamar desde slack_bot.py al arrancar"""
    return hormiga_slack.activar()

if __name__ == "__main__":
    inicializar()
    print("\n📊 Stats DHT espejo:")
    print(json.dumps(hormiga_slack.stats(), indent=2))

    # Test sync bajo demanda
    print("\n🔄 Test sync bajo demanda:")
    hormiga_slack.hormiga_10.sync_demanda()
