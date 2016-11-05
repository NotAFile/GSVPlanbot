## GSVPlanBot

Telepot Telegram Bot um den Untis Vertretungsplan abzurufen. Funktioniert wahrscheinlich nicht
sofort für alle Schulen.

### Installation

Ich empfehle...

```
# ordnere erstellen
mkdir GSVPlanBot
cd GSVPlanBot

# env erstellen, methode ist egal, ich mache:
pyvenv env
source env/bin/activate # wenn du nicht Bash benuzt das entsprechende Script auswählen

# repo clonen
git clone [URL hier einfügen]

# abhängigkeiten installieren
pip -r GSVPlanBot/requirements.txt

# config erstellen
$EDITOR keyfile
```

### Beispielconfig

Per standard benutzt GSVPlanBot HTTP Basic Auth, wer das nicht braucht oder sich anders authentifizieren muss, muss wohl leider den Code selber patchen oder ein Issue öffnen.

```
token = 239001870:AALHFajkALahdASDkljhfOIucoOQuipOQDk
url = http://untis.schulserver.de/VPlan/sus/w/{weeknum:02}/w00000.htm
user = http_benutzer
pass = http_passwort
```

token: der Token, den du von dem Botfather bekommen hast

url: URL, auf dem sich der VPlan befindet, als Python `str.format()` formatierung. `weeknum`, die aktuelle ISO Wochennummer is aktuell
die einzige Variable die unterstützt wird, das wäre aber einfach zu ändern.

user: HTTP Basic Auth Benutzername

pass: HTTP Basic Auth Passwort
