# envlayer-audit: Konfigurationsschichten prüfen

[English](../README.md) · [简体中文](zh-CN.md) · [Русский](ru.md)

Das Werkzeug zeigt, aus welcher Schicht ein Schlüssel stammt und in welcher Zeile
er überschrieben wird. Richtlinien erkennen unerlaubte Überschreibungen.
Werte werden nicht ausgegeben; Dateien und Prozessumgebung bleiben unverändert.
Python 3.10 oder neuer genügt. Im Repository sind keine Laufzeitabhängigkeiten nötig.

## Schnellstart

Im Stammverzeichnis des Repositorys ausführen:

```sh
python -m envlayer_audit examples/base.env examples/production.env --policy examples/policy.json
python -m envlayer_audit examples/base.env examples/production.env --format json
python -m unittest discover -s tests -v
```

Dateien werden nach aufsteigender Priorität angegeben. `L1` ist die erste Datei;
die Zahl nach dem Doppelpunkt ist die Zeile. `LOG_LEVEL: L1:4 -> L2:1 (1 overrides)`
zeigt eine Überschreibung in der zweiten Datei. Die letzte gültige Zuweisung
gewinnt, auch bei Wiederholungen innerhalb derselben Datei. Identische Werte
zählen ebenfalls: Das Werkzeug vergleicht keine Werte. Es sucht keine Dateien
automatisch und wertet `NODE_ENV` nicht aus.

Optional: `python -m pip install .` installiert den Befehl `envlayer-audit`.
Dafür wird setuptools 77+ benötigt; pip kann das Bauwerkzeug herunterladen.
Das Projekt ist noch nicht auf PyPI veröffentlicht.

## Richtlinien

Eine UTF-8-JSON-Datei mit `--policy` übergeben:

```json
{"required":["REGION"],"allowed":["REGION","LOG_LEVEL"],"protected":["REGION"]}
```

- `required`: Schlüssel müssen vorkommen. Leere Werte zählen als vorhanden.
- `allowed`: vollständige Liste zulässiger Schlüssel. Ohne dieses Feld gibt es
  keine Einschränkung; eine leere Liste erlaubt keinen Schlüssel.
- `protected`: höchstens eine Zuweisung über alle Schichten hinweg, einschließlich
  Wiederholungen in derselben Datei. Für Pflichtschlüssel zusätzlich `required` nutzen.

Namen werden exakt und unter Beachtung der Groß-/Kleinschreibung geprüft, ohne
Platzhalter. Unbekannte Felder, doppelte Listeneinträge oder JSON-Felder, ungültige
Namen und Pflichtschlüssel außerhalb von `allowed` werden abgelehnt.
Bei einem Syntaxfehler ist `complete` gleich `false`; alle Richtlinienprüfungen
werden übersprungen und der Aufruf schlägt fehl. Ein Teilbericht ist keine
validierte endgültige Konfiguration.

## Syntax und Grenzen

UTF-8 ohne BOM, LF/CRLF, Leerzeilen, `#`-Kommentare, optionales `export` und
`KEY=value` werden unterstützt. Namen entsprechen `[A-Za-z_][A-Za-z0-9_]*`.
Werte sind einzeilig: leer, ohne Anführungszeichen oder in einfachen/doppelten
Anführungszeichen. In doppelten Anführungszeichen schützt ein Backslash das
nächste Zeichen bei der Suche nach dem Abschluss; in einfachen gibt es keine
Escape-Verarbeitung. Nach dem Abschluss sind nur Leerraum oder ein durch
Leerraum abgetrennter Kommentar erlaubt. Unquotierte Werte dürfen keine
Anführungszeichen enthalten und nicht mit einem Backslash enden.
Mehrzeilige Werte, Zeilenfortsetzungen und Schlüssel ohne `=` sind nicht erlaubt.
Variablen und Befehle werden nicht ausgeführt oder expandiert. Dies ist ein
begrenzter Audit-Dialekt, keine vollständige dotenv- oder Shell-Implementierung.
Die vollständige Spezifikation und die Bibliotheks-API stehen im englischen README.

Exitcodes: `0` erfolgreich; `1` Syntax- oder Richtlinienverstoß;
`2` Datei-, UTF-8-, Richtlinien- oder Argumentfehler. Lese- und Richtlinienladefehler
erscheinen auch im JSON-Modus als allgemeine stderr-Meldung.

Berichte enthalten gültige Schlüsselnamen und Zeilennummern, jedoch keine Pfade,
Werte oder Hashes der Werte. Keine Geheimnisse in Schlüsselnamen verwenden.
Eingaben bleiben im Prozessspeicher; Dateien werden vollständig eingelesen.
Der Bericht ersetzt keine Tests des tatsächlichen Konfigurationsladers.
Alle Beispiele verwenden erfundene Werte. Siehe [Beitragen](../CONTRIBUTING.md),
[Sicherheit](../SECURITY.md) und [MIT-Lizenz](../LICENSE).
