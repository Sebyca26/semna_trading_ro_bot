import os
import sys
import runpy
import urllib.request
import urllib.parse

CFG = "cfg.txt"
SCANNER = None
for name in ("sp.py", "scanner_pro.py"):
    if os.path.exists(name):
        SCANNER = name
        break
if SCANNER is None:
    print("Nu gasesc sp.py. Copiaza scanner_pro.py ca sp.py in acest folder.")
    sys.exit(1)

if not os.path.exists(CFG):
    print("Prima rulare. Cheile se salveaza doar pe telefonul tau.")
    tok = input("Lipeste tokenul de la BotFather: ").strip()
    cid = input("Lipeste Id-ul de la userinfobot: ").strip()
    with open(CFG, "w") as f:
        f.write(tok + "\n" + cid + "\n")
    print("Salvat.")

with open(CFG) as f:
    lines = [x.strip() for x in f.read().splitlines() if x.strip()]
if len(lines) < 2:
    os.remove(CFG)
    print("Fisierul cfg.txt era gresit si a fost sters. Ruleaza din nou.")
    sys.exit(1)

TOKEN, CHAT = lines[0], lines[1]
os.environ["TELEGRAM_TOKEN"] = TOKEN
os.environ["TELEGRAM_CHAT_ID"] = CHAT


def send(text):
    try:
        url = "https://api.telegram.org/bot" + TOKEN + "/sendMessage"
        data = urllib.parse.urlencode({"chat_id": CHAT, "text": text}).encode()
        urllib.request.urlopen(urllib.request.Request(url, data=data), timeout=20)
        print("Telegram OK:", text)
        return True
    except Exception as e:
        print("TELEGRAM EROARE:", e)
        print("401 = token gresit. 400 sau 403 = Id gresit sau nu ai apasat Start pe botul tau.")
        print("Daca vrei sa reintroduci cheile: rm cfg.txt")
        return False


tf = "1h"
for a in sys.argv[1:]:
    if a in ("5m", "15m", "1h"):
        tf = a

if not send("Test: botul e conectat. Pornesc scanarea " + tf + "..."):
    sys.exit(1)

sys.argv = [SCANNER, "all", "--telegram", "--tf=" + tf]
print("Rulez scanarea", tf, "... dureaza cateva minute.")
try:
    runpy.run_path(SCANNER, run_name="__main__")
except SystemExit:
    pass
except Exception as e:
    print("EROARE scanner:", e)
    send("Scanarea a dat eroare: " + str(e)[:200])
    sys.exit(1)

send("Scanare " + tf + " terminata. Daca nu ai primit alt mesaj intre timp, nu exista semnal activ acum.")
