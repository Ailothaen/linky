# linky

(This README is in French only because this subject is specific to France)

Ce dépôt Github contient un script Python permettant de lire les données en provenance du bornier "Téléinformation" d'un compteur Linky.

Pour plus d'informations sur comment brancher et configurer la liaison série, lisez ces articles :
- [Partie 1](https://notes.ailothaen.fr/post/2022/07/Mesures-et-graphiques-de-la-consommation-d-un-compteur-Linky-avec-un-Raspberry-Pi-et-Grafana-%E2%80%93-Partie-1/2-%28mat%C3%A9riel%29)
- [Partie 2](https://notes.ailothaen.fr/post/2022/07/Mesures-et-graphiques-d-un-compteur-Linky-avec-un-Raspberry-Pi-et-Grafana-%E2%80%93-Partie-2/2-%28logiciel%29)

## Dépendances

Pour fonctionner, ce script requiert une base de données type MySQL, ainsi que quelques dépendances Python.

Voici les commandes classiques sur MariaDB pour créer une base de données, créer un utilisateur, et donner tous les droits à cet utilisateur sur cette base de données :

```
mysql> CREATE DATABASE linky;
mysql> CREATE USER 'linky'@'localhost' IDENTIFIED BY 'motdepasse';
mysql> GRANT ALL PRIVILEGES ON linky.* TO 'linky'@'localhost';
mysql> FLUSH PRIVILEGES;
```

Installez les dépendances Python avec `python3 -m pip install -r requirements.txt`


## Mise en place du service

Mettez le fichier `linky.service` dans `/etc/systemd/system` (sur Debian ; l'emplacement est peut-être différent selon la distribution).  
Éditez le fichier selon l'endroit où vous mettrez les scripts, et l'utilisateur que vous utiliserez.


## Configuration

La configuration se fait dans le fichier config.yml. La documentation sur ce fichier est dans CONFIG.md.


## Démarrage

```
systemctl daemon-reload
systemctl enable linky
systemctl start linky
```

Si vous avez bien tout installé, vous devriez commencer à voir des lignes (une ligne par minute) dans la table "stream".

```
MariaDB [linky]> select * from stream;
+---------------------+---------+------+-----------+
| clock               | BASE    | PAPP | BASE_diff |
+---------------------+---------+------+-----------+
| 2022-07-14 17:02:55 | 2086442 |   70 |         0 |
| 2022-07-14 17:03:57 | 2086443 |   70 |         1 |
| 2022-07-14 17:04:58 | 2086443 |   70 |         0 |
+---------------------+---------+------+-----------+
4 rows in set (0.002 sec)
```

Sinon, regardez les logs du script (`logs`) ou du service (`journalctl -u linky`)