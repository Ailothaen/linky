# linky

(This README is in French only because this subject is specific to France)

Ce dépôt Github contient un script Python permettant de lire les données en provenance du bornier "Téléinformation" (TIC) d'un compteur Linky.

Pour plus d'informations sur comment brancher et configurer la liaison série, lisez ces articles :
- [Partie 1](https://notes.ailothaen.fr/post/2022/07/Mesures-et-graphiques-de-la-consommation-d-un-compteur-Linky-avec-un-Raspberry-Pi-et-Grafana-%E2%80%93-Partie-1/2-%28mat%C3%A9riel%29)
- [Partie 2](https://notes.ailothaen.fr/post/2022/07/Mesures-et-graphiques-d-un-compteur-Linky-avec-un-Raspberry-Pi-et-Grafana-%E2%80%93-Partie-2/2-%28logiciel%29)


## Installation

Pour fonctionner, ce script requiert une base de données type MySQL/MariaDB. Sur Debian, vous pouvez installer un serveur MariaDB avec:

```bash
apt install mariadb-server
```

Voici les commandes classiques sur MariaDB pour créer une base de données, créer un utilisateur, et donner tous les droits à cet utilisateur sur cette base de données :

```bash
# pas de mot de passe à taper
mysql -u root -p
mysql> CREATE DATABASE linky;
mysql> CREATE USER 'linky'@'localhost' IDENTIFIED BY 'motdepasse';
mysql> GRANT ALL PRIVILEGES ON linky.* TO 'linky'@'localhost';
mysql> FLUSH PRIVILEGES;
```

Copiez le contenu du dépôt Github dans un dossier sur le serveur (ou terminal, ou Raspberry...).

```bash
git clone https://github.com/Ailothaen/linky.git
cd linky
```

Installez les dépendances Python (dans un environnement virtuel):

```bash
apt install python3-venv
python3 -m venv env
source env/bin/activate
pip install -r requirements.txt
```

> [!NOTE]
> Si vous avez une erreur pendant l'installation des dépendances (notamment `mysqlclient`), exécutez :
> ```bash
> # sur Debian et dérivés
> apt install python3-dev default-libmysqlclient-dev build-essential pkg-config
>
> # sur Red Hat et dérivés
> yum install python3-devel mysql-devel pkgconfig
> ```

Mettez le fichier `linky.service` dans `/etc/systemd/system` (sur Debian ; l'emplacement est peut-être différent selon la distribution).  
Éditez le fichier selon l'endroit où vous mettrez les scripts, et l'utilisateur que vous utiliserez.


## Configuration

La configuration se fait dans le fichier config.yml.

|Paramètre|Description|Obligatoire|
|---|---|---|
|database.server|Serveur MariaDB|oui|
|database.name|Nom de la base de données|oui|
|database.user|Utilisateur qui va se connecter au serveur MariaDB|oui|
|database.password|Mot de passe de l'utilisateur|oui|
|device|Fichier représentant la connexion série (souvent `/dev/ttyS0` ou `/dev/ttyAMA0`)|oui|
|contract|Type de contrat d'électricité. Valeurs possibles : `base` (contrat de base), `hchp` (heures creuses/pleines), `tempo` (Tempo), `ejp` (EJP). Selon le type de contrat, les colonnes de la base de données ne sont pas les mêmes, regardez plus bas pour en savoir plus.|non (par défaut `base`)|
|mode|Mode de téléinformation client (TIC) du Linky (`historique` ou `standard`). On peut le voir sur le compteur (rubrique "MODE TIC")|non (par défaut `historique`)|
|utc|Si `true`, l'heure et la date seront enregistrés en UTC (temps universel). Si `false`, cela sera en heure locale (attention, car cela peut provoquer des heures en double, notamment aux jours de changement d'heure)|non (par défaut `true`)|
|interval|Toutes les combien de secondes on récupère les informations|non (par défaut `60`)|
|debug|Si `true`, plus d'informations seront écrites dans le fichier de logs.|non (par défaut `false`)|


## Démarrage

Avant de démarrer le service, je vous conseille de tester la liaison série pour être sûr qu'elle fonctionne bien :

```bash
# si TIC Linky en mode historique
picocom -b 1200 -d 7 -f n -y e -p 1 /dev/ttyAMA0

# si TIC Linky en mode standard
picocom -b 9600 -d 7 -f n -y e -p 1 /dev/ttyAMA0
```

Remplacez `/dev/ttyAMA0` par le chemin de votre liaison série si besoin.

> [!WARNING]
> Si vous êtes sur Raspberry Pi, et que la liaison fonctionne mais que les données sont corrompues (cela peut arriver surtout en mode standard), vous devez configurer votre Raspberry Pi pour qu'il utilise le pilote matériel pour l'entrée série. Écrivez ceci à la fin de `/boot/firmware/config.txt` :
>
> ```
> dtoverlay=disable-bt
> ```
>
> Notez cependant que cela désactivera le Bluetooth. ([Plus d'infos ici](https://www.framboise314.fr/utiliser-le-port-serie-du-raspberry-pi-3-et-du-pi-zero/))

Vous pouvez maintenant activer le service :

```bash
systemctl daemon-reload
systemctl enable linky
systemctl start linky
```

Si vous avez bien tout installé, vous devriez commencer à voir des lignes (une ligne par minute) dans la table "stream".

```
MariaDB [linky]> SELECT * FROM stream;
+---------------------+----+----------+------+------+------+------+------+------+------+------+------+-------+
| clock               | P  | E1       | E2   | E3   | E4   | E5   | E6   | E7   | E8   | E9   | E10  | Ediff |
+---------------------+----+----------+------+------+------+------+------+------+------+------+------+-------+
| 2025-12-14 15:29:25 | 70 | 14999249 | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL |     0 |
| 2025-12-14 15:30:26 | 70 | 14999249 | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL |     0 |
| 2025-12-14 15:31:27 | 90 | 14999250 | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL |     1 |
| 2025-12-14 15:32:28 | 90 | 14999251 | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL |     1 |
+---------------------+----+----------+------+------+------+------+------+------+------+------+------+-------+
4 rows in set (0.002 sec)
```

Sinon, regardez les logs du script (`logs`) ou du service (`journalctl -u linky`)


## Structure de la base de données

La base de données contient deux tables: **stream** et **dailies**.

**stream** est la table contenant chaque relevé des compteurs faits sur le Linky chaque minute. La colonne **P** est la puissance instantanée (en volt-ampères), la colonne **Ediff** est le nombre de watt-heures consommés depuis le relevé précédent.  
Les colonnes **E** (en watt-heures) à utiliser dépendent de votre contrat :

||Base|Heure creuses / pleines|Tempo|EJP|
|---|---|---|---|---|
|E1|Base|Heures creuses|Jours bleus HC|Heures normales|
|E2||Heures pleines|Jours bleus HP|Heures de pointe|
|E3|||Jours blancs HC||
|E4|||Jours blancs HP||
|E5|||Jours rouges HC||
|E6|||Jours rouges HP||
|E7|||||
|E8|||||
|E9|||||
|E10|||||

**dailies** est similaire à **stream**, mais ici il y aura seulement une ligne par jour. **Jdiff** est le nombre de Wh consommés sur le jour complet.

Je ne sais pas quelles sont les bonnes colonnes avec des fournisseurs autres qu'EDF : si vous êtes dans ce cas, n'hésitez pas à dire ce que vous voyez !
