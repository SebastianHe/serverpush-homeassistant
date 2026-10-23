# ServerPush für Home Assistant

[English](README.md) · Deutsch

<img src="custom_components/serverpush/brand/icon.png" alt="ServerPush App-Icon" width="128" height="128">

Sende Benachrichtigungen aus Home Assistant über [ServerPush.net](https://www.serverpush.net) an deine ServerPush-Chats – beispielsweise bei offenen Fenstern, abgeschlossenen Backups oder Störungen.

- Vier Notify-Entities pro Webhook-Token: `info`, `success`, `warning` und `error`.
- Versand aus Automationen und Skripten über die Standardaktion `notify.send_message`, mit optionalem Titel und Markdown im Nachrichtentext.
- Mehrere Chats oder Tokens unabhängig voneinander einrichten.
- Einrichtung über die Oberfläche mit Tokenprüfung ohne Testnachricht; Tokenwechsel erhält bestehende Entities und Automationen.
- Deutsche und englische Übersetzungen; kein Polling und keine zusätzliche YAML-Konfiguration erforderlich.

## Installation mit HACS

Voraussetzungen: Home Assistant **2026.10 oder neuer**, [installiertes und eingerichtetes HACS](https://www.hacs.xyz/docs/use/) sowie ein Webhook-Token eines ServerPush-Chats. Nachrichtentarife und Push-Einstellungen von ServerPush gelten weiterhin.

1. Öffne das Repository über diesen Button in HACS:

   [![Repository in HACS öffnen](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=SebastianHe&repository=serverpush-homeassistant&category=integration)

   Alternativ: **HACS → ⋮ → Benutzerdefinierte Repositories** öffnen, `https://github.com/SebastianHe/serverpush-homeassistant` eintragen und den Typ **Integration** auswählen. Eine Aufnahme in den HACS-Standardkatalog ist dafür nicht erforderlich.
2. Öffne **ServerPush** in HACS und wähle **Herunterladen**. Bestätige den Download.
3. Starte Home Assistant neu.
4. Öffne die Einrichtung über diesen Button:

   [![Integration hinzufügen](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow/?domain=serverpush)

   Alternativ: **Einstellungen → Geräte & Dienste → Integration hinzufügen → ServerPush**.
5. Trage das rohe Webhook-Token und optional einen Namen ein, beispielsweise `Haus`. Keine vollständige Webhook-URL eintragen.

Die Buttons nutzen [My Home Assistant](https://my.home-assistant.io/). Prüfe dort die Adresse deiner Home-Assistant-Instanz. Der HACS-Button setzt eingerichtetes HACS voraus; der Einrichtungsbutton funktioniert nach Installation und Neustart.

### Manuelle Installation

1. Kopiere den Ordner `custom_components/serverpush` aus diesem Repository nach `/config/custom_components/serverpush` deiner Home-Assistant-Installation.
2. Starte Home Assistant neu und füge **ServerPush** unter **Einstellungen → Geräte & Dienste → Integration hinzufügen** hinzu.
3. Trage das rohe Webhook-Token und optional einen Namen ein.

## Verwendung

Ein Eintrag namens `Haus` erzeugt ein Dienstgerät „ServerPush Haus“ mit vier Notify-Entities. Bei englischen Entity-Namen sind die anfänglichen IDs beispielsweise:

| Entity | ServerPush-Status |
| --- | --- |
| `notify.serverpush_haus_info` | `info` |
| `notify.serverpush_haus_success` | `success` |
| `notify.serverpush_haus_warning` | `warning` |
| `notify.serverpush_haus_error` | `error` |

Die Namen sind deutsch und englisch übersetzt. Je nach Sprache und bestehenden Entities können die tatsächlichen Entity-IDs abweichen, beispielsweise `notify.serverpush_haus_warnung`. Wähle das Ziel im Automationseditor oder übernimm seine ID aus **Einstellungen → Geräte & Dienste → Entitäten**.

```yaml
action: notify.send_message
target:
  entity_id: notify.serverpush_haus_warning
data:
  title: "Fenster offen"
  message: "Das Schlafzimmerfenster ist seit 30 Minuten offen."
```

`message` ist erforderlich (1–20.000 Zeichen). `title` ist optional (maximal 200 Zeichen). Markdown wird unverändert an ServerPush übergeben. Die ausgewählte Entity bestimmt den Status; die Aktion benötigt kein zusätzliches `status`-Feld. Verwende für eine einzelne Nachricht nur eine der vier Entities, sonst wird pro ausgewählter Entity eine Nachricht gesendet.

Weitere Tokens werden über **Integration hinzufügen → ServerPush** als weitere Einträge derselben Integration eingerichtet. Dasselbe Token kann nur einmal eingerichtet werden. Verschiedene Tokens dürfen auch zum selben Chat gehören; hierfür werden jeweils eigene Entities angelegt.

## Token prüfen und wechseln

Die Einrichtung prüft das Token über `GET /api/v1/chats/:token/validate`, bevor der Eintrag angelegt wird. Ungültige oder widerrufene Tokens und Tokens gelöschter Chats werden abgelehnt. Die Prüfung sendet keine Nachricht und erzeugt keine Push-Aufträge. Sie verbraucht weder Nachrichtenkontingent noch Webhook-Anfragelimit und funktioniert auch bei ausgeschöpften Limits. Bei Verbindungsproblemen oder unerwarteten API-Antworten bleibt das Formular für einen erneuten Versuch geöffnet.

Eine erfolgreiche Prüfung bestätigt die Gültigkeit zum Zeitpunkt der Anfrage. Der spätere Nachrichtenversand kann weiterhin an Limits oder einem zwischenzeitlichen Widerruf scheitern.

Über das Menü des Integrationseintrags → **Neu konfigurieren** lassen sich Name und Token ändern. Ein leeres Tokenfeld behält das bisherige Token. Die internen Entity-IDs hängen am Integrationseintrag, nicht am Token: Ein neues Token wird vor dem Speichern ebenfalls geprüft. Ein Tokenwechsel erhält Entities und bestehende Automationen. Das gilt auch bei einer Namensänderung; bereits registrierte Entity-IDs bleiben bestehen.

Bei einem abgelehnten Token startet Home Assistant einen Dialog zur erneuten Authentifizierung. Das dort eingetragene Ersatz-Token wird vor dem Speichern geprüft. Fehlgeschlagene Nachrichten werden nicht gespeichert oder nachträglich versendet.

## Fehler und Grenzen

- Ungültige/widerrufene Tokens, Netzwerkfehler, API-Fehler und erreichte Limits werden als Fehler an die aufrufende Automation gemeldet.
- Nachrichtenlimits und Push-Einstellungen des ServerPush-Chats gelten weiterhin. Eine angenommene Nachricht bedeutet nicht, dass jedes Endgerät eine Push-Benachrichtigung erhält.
- POST-Anfragen werden bei Fehlern **nicht automatisch wiederholt**. Nach einem Timeout kann die Nachricht bereits angenommen worden sein; prüfe vor erneutem Versand den Chat.
- Es gibt kein Polling und keine Warteschlange. Der gespeicherte Entity-Zustand zeigt den letzten von Home Assistant erfolgreich bestätigten Versand, keine Empfangsbestätigung eines Endgeräts.
- Das Token wird in der Home-Assistant-Konfiguration gespeichert. Formulare zeigen es nicht vorab an; die Integration protokolliert weder Tokens noch geheime Webhook-URLs. Schütze deine Home-Assistant-Backups entsprechend.
- Der Versand erfolgt ausschließlich per HTTPS an `https://www.serverpush.net`. Eigene Serveradressen sind in dieser Version nicht konfigurierbar.

## Entwicklung

Die Testumgebung benötigt Python 3.14 und testet gegen Home Assistant 2026.10.2:

```sh
python3.14 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/pytest --cov=custom_components.serverpush --cov-report=term-missing
```

Die Tests verwenden Home Assistants echte Config-Flow-, Entity-Registry- und Notify-Infrastruktur. HTTP-Anfragen werden simuliert; echte Tokens und Nachrichten sind für Tests nicht nötig. Sockets sind während der Tests gesperrt.

API-Vertrag: [ServerPush-API-Dokumentation](https://www.serverpush.net/api/docs).

GitHub Actions führt zusätzlich die HACS-Validierung und Home Assistant hassfest aus. Hinweise zur Veröffentlichung: [RELEASING.md](RELEASING.md).

## Lizenz

[MIT](LICENSE) © 2026 Sebastian Heinisch.
