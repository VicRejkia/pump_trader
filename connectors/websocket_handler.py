# path: connectors/websocket_handler.py

"""
Verwaltet die gesamte WebSocket-Kommunikation mit der PumpPortal-API.
Diese Klasse ist als robuster, sich selbst heilender Supervisor konzipiert, der eine
dauerhafte Verbindung sicherstellt, Abonnements verwaltet und eine saubere
Schnittstelle für den Rest der Anwendung bereitstellt.
"""

import asyncio
import json
import random
from enum import Enum
from datetime import datetime, timezone
from typing import Optional, Set, List

import websockets
from websockets import exceptions as ws_exceptions

from bot_logger import logger
from state_manager import GlobalState
from database_handler import DatabaseClient
from config.config import (
    _PUMPPORTAL_WS,
    _WEBSOCKET_SUBSCRIPTION_REFRESH_ENABLED,
    _WEBSOCKET_SUBSCRIPTION_REFRESH_INTERVAL_MINUTES,
    WEBSOCKET_PING_INTERVAL_SECONDS,
    WEBSOCKET_PONG_TIMEOUT_SECONDS,
    WEBSOCKET_RECONNECT_BACKOFF_BASE_SECONDS,
    WEBSOCKET_RECONNECT_BACKOFF_MAX_SECONDS,
    WEBSOCKET_SUBSCRIPTION_BATCH_SIZE,
    WEBSOCKET_BATCH_DELAY,
)

class ConnectionStatus(Enum):
    """Definiert die möglichen Zustände der WebSocket-Verbindung."""
    DISCONNECTED = "Disconnected"
    CONNECTING = "Connecting"
    CONNECTED = "Connected"
    RECONNECTING = "Reconnecting"
    SHUTTING_DOWN = "Shutting Down"

class WebSocketHandler:
    """Ein Supervisor für eine persistente WebSocket-Verbindung."""

    def __init__(self, db_client: DatabaseClient, state_manager: GlobalState, config: dict):
        self.db_client = db_client
        self.state = state_manager
        self.config = config
        self.trade_queue = asyncio.Queue()

        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._status = ConnectionStatus.DISCONNECTED
        self._reconnect_delay = WEBSOCKET_RECONNECT_BACKOFF_BASE_SECONDS
        self._last_pong_time: float = 0.0
        self._last_message_time: float = 0.0

        # Speichert den Status der globalen Abonnements
        self._subscribed_to_new_token = False
        self._subscribed_to_migration = False

        # Haupt-Task für die Verbindungsverwaltung
        self._manager_task: Optional[asyncio.Task] = None

    def start(self):
        """Startet den Verbindungsmanager als Hintergrund-Task."""
        if self._manager_task is None or self._manager_task.done():
            self._manager_task = asyncio.create_task(self._connection_supervisor(), name="websocket_supervisor")
            logger.info("🚀 WebSocket Connection Supervisor gestartet.")
        else:
            logger.warning("WebSocket Connection Supervisor läuft bereits.")

    async def shutdown(self):
        """Fährt die WebSocket-Verbindung und alle zugehörigen Tasks ordnungsgemäß herunter."""
        if self._status == ConnectionStatus.SHUTTING_DOWN:
            return
            
        logger.info("🔌 WebSocket-Handler wird heruntergefahren...")
        self._set_status(ConnectionStatus.SHUTTING_DOWN)

        # Alle Abonnements kündigen
        if self._ws and self._ws.open:
            logger.debug("Kündige alle offenen Abonnements vor dem Herunterfahren.")
            all_subs = list(await self.state.get_token_subscriptions())
            await self._unsubscribe_in_batches(all_subs, "shutdown")
            self._subscribed_to_new_token = False
            self._subscribed_to_migration = False

        # Den Manager-Task beenden
        if self._manager_task and not self._manager_task.done():
            self._manager_task.cancel()
            try:
                await self._manager_task
            except asyncio.CancelledError:
                pass # Erwarteter Fehler beim Abbrechen

        # Finale Bereinigung
        await self._close_connection("Shutdown requested")
        logger.info("✅ WebSocket-Handler erfolgreich heruntergefahren.")

    # --- Öffentliche Methoden für andere Module ---

    async def unsubscribe_from_trades(self, mints: List[str], reason: str):
        """
        Öffentliche Methode, um `subscribeTokenTrade` für eine Liste von Mints zu kündigen.
        Wird von `rugcheck_handler` und dem `_dead_token_monitor` verwendet.
        """
        if not mints:
            return
        
        logger.info(f"Anfrage zum Kündigen von {len(mints)} Token-Abonnements erhalten (Grund: {reason}).")
        await self._unsubscribe_in_batches(mints, reason)

    def get_status(self) -> dict:
        """Gibt einen detaillierten Statusbericht für `monitor_tasks` zurück."""
        now = asyncio.get_event_loop().time()
        time_since_last_msg = now - self._last_message_time if self._last_message_time else -1
        time_since_last_pong = now - self._last_pong_time if self._last_pong_time else -1

        return {
            "connection_status": self._status.value,
            "is_connected": self._ws is not None and self._ws.open,
            "new_token_subscribed": self._subscribed_to_new_token,
            "migration_subscribed": self._subscribed_to_migration,
            "trade_subscriptions_count": len(self.state.active_token_subscriptions),
            "time_since_last_message_s": round(time_since_last_msg, 1),
            "time_since_last_pong_s": round(time_since_last_pong, 1),
        }
        
    # --- Interne Logik: Der Connection Supervisor ---

    def _set_status(self, new_status: ConnectionStatus):
        if self._status != new_status:
            logger.info(f"WebSocket-Status geändert: {self._status.value} -> {new_status.value}")
            self._status = new_status

    async def _connection_supervisor(self):
        """
        Die Hauptschleife, die sicherstellt, dass die Verbindung immer aktiv ist.
        Implementiert exponentielles Backoff mit Jitter für die Wiederverbindung.
        """
        while self._status != ConnectionStatus.SHUTTING_DOWN:
            try:
                self._set_status(ConnectionStatus.CONNECTING)
                async for websocket in websockets.connect(
                    _PUMPPORTAL_WS,
                    ping_interval=WEBSOCKET_PING_INTERVAL_SECONDS,
                    ping_timeout=WEBSOCKET_PONG_TIMEOUT_SECONDS,
                    open_timeout=20,
                    extra_headers={"Origin": "https://pumpportal.fun"}
                ):
                    self._ws = websocket
                    self._set_status(ConnectionStatus.CONNECTED)
                    logger.info("✅ WebSocket-Verbindung erfolgreich hergestellt.")
                    self._reconnect_delay = WEBSOCKET_RECONNECT_BACKOFF_BASE_SECONDS # Reset bei Erfolg
                    
                    # Starte die Session-Logik
                    await self._session_handler()
            
            except ws_exceptions.WebSocketException as e:
                logger.warning(f"WebSocket-Verbindungsfehler: {e}. Wiederverbindung wird versucht.")
            except asyncio.CancelledError:
                logger.info("Connection Supervisor wurde abgebrochen.")
                break
            except Exception as e:
                logger.error(f"Unerwarteter Fehler im Connection Supervisor: {e}", exc_info=True)

            if self._status == ConnectionStatus.SHUTTING_DOWN:
                break
            
            # Logik für Wiederverbindung mit Backoff
            self._set_status(ConnectionStatus.RECONNECTING)
            jitter = random.uniform(0.5, 1.5)
            wait_time = min(self._reconnect_delay * jitter, WEBSOCKET_RECONNECT_BACKOFF_MAX_SECONDS)
            logger.info(f"Warte {wait_time:.2f} Sekunden vor dem nächsten Verbindungsversuch...")
            
            await asyncio.sleep(wait_time)
            self._reconnect_delay = min(self._reconnect_delay * 2, WEBSOCKET_RECONNECT_BACKOFF_MAX_SECONDS)

        logger.info("🛑 WebSocket Connection Supervisor wurde beendet.")

    # --- Interne Logik: Session- und Nachrichten-Handling ---

    async def _session_handler(self):
        """
        Verwaltet eine aktive WebSocket-Sitzung: Abonnements, Nachrichtenempfang und Health Checks.
        """
        if not self._ws: return

        # Setzt die Zeitstempel beim Start der Sitzung zurück
        now = asyncio.get_event_loop().time()
        self._last_pong_time = now
        self._last_message_time = now

        # Führt alle Hintergrundtasks für die Sitzung aus
        session_tasks = [
            asyncio.create_task(self._message_receiver(), name="ws_receiver"),
            asyncio.create_task(self._health_checker(), name="ws_health_checker"),
            asyncio.create_task(self._subscription_refresher(), name="ws_subscription_refresher"),
            asyncio.create_task(self._dead_token_monitor(), name="ws_dead_token_monitor")
        ]
        
        try:
            # Initialisiere alle Abonnements
            await self._initialize_subscriptions()
            
            # Wartet, bis einer der Tasks endet (was auf ein Problem hindeutet)
            done, pending = await asyncio.wait(session_tasks, return_when=asyncio.FIRST_COMPLETED)
            
            # Loggt den Grund für das Ende der Sitzung
            for task in done:
                if task.exception():
                    logger.warning(f"WebSocket-Sitzung beendet, da Task '{task.get_name()}' mit Fehler fehlgeschlagen ist: {task.exception()}")
                else:
                    logger.warning(f"WebSocket-Sitzung beendet, da Task '{task.get_name()}' unerwartet beendet wurde.")
            
            # Bricht die verbleibenden Tasks ab
            for task in pending:
                task.cancel()

        except Exception as e:
            logger.error(f"Fehler während der WebSocket-Sitzung: {e}", exc_info=True)
        finally:
            await self._close_connection("Session beendet")

    async def _message_receiver(self):
        """Empfängt und verarbeitet eingehende Nachrichten."""
        if not self._ws: return
        try:
            async for message in self._ws:
                self._last_message_time = asyncio.get_event_loop().time()
                await self._handle_incoming(message)
        except asyncio.CancelledError:
            pass # Normales Beenden
        except ws_exceptions.ConnectionClosed as e:
            logger.warning(f"Verbindung im Receiver geschlossen: {e.code} {e.reason}")
            raise # Löst das Beenden der Session aus
        except Exception as e:
            logger.error(f"Fehler im Nachrichten-Receiver: {e}", exc_info=True)
            raise

    async def _handle_incoming(self, raw_message: str):
        """
        Verarbeitet die Logik für eine einzelne eingehende Nachricht.
        Entspricht der alten `_handle_incoming`-Funktion.
        """
        try:
            data = json.loads(raw_message)
            tx_type = data.get("txType")

            if tx_type == "create":
                mint = data.get("mint")
                if not mint: return
                
                # Die Logik zum Einfügen in die DB und zur Überprüfung des Erstellers ist in `insert_token` gekapselt.
                # `insert_token` gibt `True` zurück, wenn der Token neu ist und die Kriterien erfüllt.
                is_new_and_valid = await self.db_client.insert_token(data)
                
                if is_new_and_valid:
                    logger.info(f"Neuer valider Token erkannt: {mint}. Abonniere Trades.")
                    await self._send_json({"method": "subscribeTokenTrade", "keys": [mint]})
                    await self.state.add_token_subscription(mint)

            elif tx_type == "migrate":
                mint = data.get("mint")
                if mint and await self.db_client.is_token_active_in_db(mint):
                    await self.db_client.mark_token_as_migrated(mint)
                    await self.db_client.insert_migration(data)

            elif tx_type in ["buy", "sell"]:
                await self.trade_queue.put(data)
                
        except json.JSONDecodeError:
            logger.debug(f"Nicht-JSON-Nachricht empfangen: {raw_message[:100]}")
        except Exception as e:
            logger.error(f"Fehler bei der Verarbeitung der eingehenden Nachricht: {e}", exc_info=True)

    # --- Interne Logik: Abonnements & Health Checks ---

    async def _initialize_subscriptions(self):
        """Abonniert alle notwendigen Streams bei Verbindungsaufbau."""
        logger.info("Initialisiere Abonnements...")
        
        # Globale Streams
        await self._send_json({"method": "subscribeNewToken"})
        self._subscribed_to_new_token = True
        logger.debug("-> 'subscribeNewToken' gesendet.")
        
        await self._send_json({"method": "subscribeMigration"})
        self._subscribed_to_migration = True
        logger.debug("-> 'subscribeMigration' gesendet.")

        # Bestehende aktive Token
        active_tokens = await self.db_client.get_active_tokens()
        mints_to_subscribe = [record["mint"] for record in active_tokens]
        
        if mints_to_subscribe:
            logger.info(f"Setze {len(mints_to_subscribe)} bestehende Token-Abonnements fort...")
            await self._subscribe_in_batches(mints_to_subscribe)
            
        logger.info("✅ Alle initialen Abonnements abgeschlossen.")

    async def _subscribe_in_batches(self, mints: List[str]):
        """Abonniert eine Liste von Mints in Stapeln."""
        for i in range(0, len(mints), WEBSOCKET_SUBSCRIPTION_BATCH_SIZE):
            if self._status != ConnectionStatus.CONNECTED: break
            batch = mints[i:i + WEBSOCKET_SUBSCRIPTION_BATCH_SIZE]
            await self._send_json({"method": "subscribeTokenTrade", "keys": batch})
            for mint in batch:
                await self.state.add_token_subscription(mint)
            logger.debug(f"Stapel von {len(batch)} Token-Abonnements gesendet.")
            await asyncio.sleep(WEBSOCKET_BATCH_DELAY)

    async def _unsubscribe_in_batches(self, mints: List[str], reason: str):
        """Kündigt Abonnements in Stapeln und aktualisiert den Zustand."""
        for i in range(0, len(mints), WEBSOCKET_SUBSCRIPTION_BATCH_SIZE):
            # Sende Kündigung auch wenn nicht verbunden, um den Zustand zu bereinigen
            batch = mints[i:i + WEBSOCKET_SUBSCRIPTION_BATCH_SIZE]
            
            if self._ws and self._ws.open:
                await self._send_json({"method": "unsubscribeTokenTrade", "keys": batch})
            
            # Zustand immer aktualisieren
            for mint in batch:
                await self.state.remove_token_subscription(mint)

            logger.debug(f"Stapel von {len(batch)} Token-Abmeldungen gesendet (Grund: {reason}).")
            
            # Bei Gründen wie "dead" oder "rug", auch aus der DB löschen/archivieren
            if reason in ["dead_token", "high_rugcheckscore"]:
                for mint in batch:
                    await self.db_client.backup_and_delete_token(
                        mint=mint, 
                        archived_at=datetime.now(timezone.utc),
                        reason=reason
                    )
            
            await asyncio.sleep(WEBSOCKET_BATCH_DELAY)

    async def _subscription_refresher(self):
        """Erneuert periodisch alle 'subscribeTokenTrade'-Abonnements."""
        if not _WEBSOCKET_SUBSCRIPTION_REFRESH_ENABLED:
            logger.info("Automatischer Abonnement-Refresher ist deaktiviert.")
            return

        interval = _WEBSOCKET_SUBSCRIPTION_REFRESH_INTERVAL_MINUTES * 60
        logger.info(f"🔄 Abonnement-Refresher gestartet. Intervall: {interval / 60} Minuten.")

        while self._status == ConnectionStatus.CONNECTED:
            await asyncio.sleep(interval)
            logger.info("Starte periodische Erneuerung der Abonnements...")
            
            current_subs = list(await self.state.get_token_subscriptions())
            if current_subs:
                await self._unsubscribe_in_batches(current_subs, "periodic_refresh")
                
            await asyncio.sleep(2) # Kurze Pause
            
            active_tokens_now = await self.db_client.get_active_tokens()
            mints_to_resubscribe = [r["mint"] for r in active_tokens_now]
            
            if mints_to_resubscribe:
                await self._subscribe_in_batches(mints_to_resubscribe)
            
            logger.info(f"✅ Periodische Erneuerung abgeschlossen. {len(mints_to_resubscribe)} Abonnements aktiv.")
        
        logger.info("Abonnement-Refresher beendet, da die Verbindung getrennt wurde.")

    async def _dead_token_monitor(self):
        """
        Überwacht periodisch, ob Token inaktiv geworden sind und gekündigt werden müssen.
        Entspricht der alten `unsubscribe_checker`-Funktion.
        """
        interval = self.config.get("INACTIVITY_PERIOD", 60) * 30 # Prüft in halben Inaktivitätsperioden
        logger.info(f"🗑️ Monitor für tote Token gestartet. Intervall: {interval / 60:.1f} Minuten.")
        
        while self._status == ConnectionStatus.CONNECTED:
            await asyncio.sleep(interval)
            try:
                tokens_to_unsub = await self.db_client.get_tokens_to_unsubscribe(
                    self.config["MC_DROP_THRESHOLD"],
                    self.config["INACTIVITY_PERIOD"],
                    self.config["MIN_TOKEN_AGE"]
                )
                
                if tokens_to_unsub:
                    mints = [record["mint"] for record in tokens_to_unsub]
                    logger.info(f"Gefundene {len(mints)} tote/inaktive Token. Kündige Abonnements.")
                    await self.unsubscribe_from_trades(mints, "dead_token")

            except Exception as e:
                logger.error(f"Fehler im Monitor für tote Token: {e}", exc_info=True)
                
        logger.info("Monitor für tote Token beendet, da die Verbindung getrennt wurde.")

    async def _health_checker(self):
        """Überwacht die Gesundheit der Verbindung durch Pongs und Nachrichtenfluss."""
        while self._status == ConnectionStatus.CONNECTED:
            await asyncio.sleep(WEBSOCKET_PING_INTERVAL_SECONDS)
            if not self._ws or not self._ws.open: break

            # 1. Pong-Check: `websockets` handelt dies intern und wirft einen TimeoutError.
            # Wir überwachen zusätzlich die Zeit seit dem letzten erfolgreichen Pong.
            now = asyncio.get_event_loop().time()
            if now - self._last_pong_time > (WEBSOCKET_PONG_TIMEOUT_SECONDS + 5):
                logger.warning("Kein Pong in der erwarteten Zeit erhalten. Verbindung wird als tot betrachtet.")
                raise ConnectionError("Pong-Timeout")

            # 2. Nachrichtenfluss-Check
            if now - self._last_message_time > (WEBSOCKET_PING_INTERVAL_SECONDS * 4):
                logger.warning(f"Seit über {now - self._last_message_time:.0f}s keine Nachricht erhalten. Verbindung könnte tot sein.")
                raise ConnectionError("Stale connection")
    
    # --- Hilfsfunktionen ---

    async def _send_json(self, data: dict):
        """Sendet ein JSON-Objekt sicher über den WebSocket."""
        if self._ws and self._ws.open:
            try:
                await self._ws.send(json.dumps(data))
            except ws_exceptions.ConnectionClosed:
                logger.warning("Versuch, auf einer geschlossenen Verbindung zu senden.")
                raise # Signalisiert das Ende der Session
            except Exception as e:
                logger.error(f"Fehler beim Senden von Daten: {e}")
                raise
        else:
            logger.warning("Sendeversuch, aber WebSocket ist nicht verbunden.")
            raise ConnectionError("WebSocket is not open")

    async def _close_connection(self, reason: str):
        """Schließt die WebSocket-Verbindung, falls sie existiert."""
        if self._ws:
            logger.debug(f"Schließe WebSocket-Verbindung (Grund: {reason})...")
            try:
                await self._ws.close(code=1000, reason=reason)
            except Exception as e:
                logger.error(f"Fehler beim Schließen der WebSocket-Verbindung: {e}")
            finally:
                self._ws = None
                self._set_status(ConnectionStatus.DISCONNECTED)