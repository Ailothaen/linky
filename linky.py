#!/usr/bin/python3

# Third party modules
import MySQLdb, serial, yaml

# Standard modules
import datetime, logging, logging.handlers, sys, time


# ----------------------------- #
# Classes                       #
# ----------------------------- #

class Database():
    """
    Connection to database, and insert/update functions.
    """
    def __init__(self, server, user, password, name, check_schema=True):
        """
        Initiate connection to database, and create schema if needed.

        Args:
            server (str): Database server address or hostname
            user (str): Username for the database server
            password (str): Password for the username
            name (str): Database name
            check_schema (bool, optional): Whether to create schema if it does not exist.
        """
        try:
            self.database = MySQLdb.connect(server, user, password, name)

            if check_schema:
                cursor = self.database.cursor()
                stream_exists = cursor.execute(f"SELECT * FROM information_schema.tables WHERE table_schema = %(name)s AND table_name = 'stream' LIMIT 1", {"name": name})
                dailies_exists = cursor.execute(f"SELECT * FROM information_schema.tables WHERE table_schema = %(name)s AND table_name = 'dailies' LIMIT 1", {"name": name})
                
                if stream_exists == 0 or dailies_exists == 0:
                    log.info("Database schema does not exist, creating it...")
                    self.create_schema(cursor)
                    log.info("Database schema created successfully!")
                cursor.close()
        except MySQLdb._exceptions.OperationalError:
            log.critical('Something went wrong while connecting to database server:', exc_info=True)
            print('Something went wrong while connecting to database server. See logs for more info.', file=sys.stderr)
            raise SystemExit(4)


    def create_schema(self, cursor):
        """
        Create database structure.

        Args:
            cursor (_type_): Database cursor
        """
        cursor.execute("CREATE TABLE `dailies` (`clock` date NOT NULL, `Ediff` int(11) NOT NULL) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;")
        cursor.execute("CREATE TABLE `stream` (`clock` datetime NOT NULL, `P` int(11) NOT NULL, `E1` int(11) DEFAULT NULL, `E2` int(11) DEFAULT NULL, `E3` int(11) DEFAULT NULL, `E4` int(11) DEFAULT NULL, `E5` int(11) DEFAULT NULL, `E6` int(11) DEFAULT NULL, `E7` int(11) DEFAULT NULL, `E8` int(11) DEFAULT NULL, `E9` int(11) DEFAULT NULL, `E10` int(11) DEFAULT NULL, `Ediff` int(11) NOT NULL) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;")
        cursor.execute("ALTER TABLE `dailies` ADD PRIMARY KEY (`clock`);")
        cursor.execute("ALTER TABLE `stream` ADD PRIMARY KEY (`clock`);")
        self.database.commit()


    def insert_stream(self, P, E1, E2, E3, E4, E5, E6, E7, E8, E9, E10):
        """
        Insert a record in the stream table.

        Args:
            P (int): Linky BASE value (Wh meter)
            E1 to E10 (int): Linky power meters. It depends of the contract (Base, HC/HP, Tempo...). See README for more explanations.
        """
        # generating time
        if config.get('utc', False):
            now = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
        else:
            now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        cursor = self.database.cursor()

        # retrieving previous J values and calculating Ediff
        cursor.execute("SELECT E1, E2, E3, E4, E5, E6, E7, E8, E9, E10 FROM stream ORDER BY clock DESC LIMIT 1")
        try:
            previous = sum(filter(None, cursor.fetchone()))
        except TypeError:
            # no records yet
            Ediff = 0
        else:
            current = sum(filter(None, (E1, E2, E3, E4, E5, E6)))
            Ediff = current-previous

        # inserting records
        cursor.execute(f'INSERT INTO stream VALUES (%(now)s, %(P)s, %(E1)s, %(E2)s, %(E3)s, %(E4)s, %(E5)s, %(E6)s, %(E7)s, %(E8)s, %(E9)s, %(E10)s, %(Ediff)s);', {"now": now, "P": P, "E1": E1, "E2": E2, "E3": E3, "E4": E4, "E5": E5, "E6": E6, "E7": E7, "E8": E8, "E9": E9, "E10": E10, "Ediff": Ediff})
        self.database.commit()
        cursor.close()


    def insert_dailies(self, E1, E2, E3, E4, E5, E6, E7, E8, E9, E10):
        """
        Inserts a record in the dailies table.

        Args:
            E1 to E10 (int): Linky power meters. It depends of the contract (Base, HC/HP, Tempo...). See README for more explanations.
        """
        if config.get('utc', False):
            now = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d')
        else:
            now = datetime.datetime.now().strftime('%Y-%m-%d')

        cursor = self.database.cursor()

        # getting previous day midnight Ediff value
        cursor.execute("SELECT clock, E1, E2, E3, E4, E5, E6, E7, E8, E9, E10 FROM `stream` INNER JOIN (SELECT MIN(clock) AS firstOfTheDay FROM `stream` GROUP BY DATE(clock)) joint ON `stream`.clock = joint.firstOfTheDay ORDER BY `stream`.clock DESC LIMIT 1")
        try:
            previous_values = cursor.fetchone()
            previous = sum(filter(None, previous_values[1:11]))
        except TypeError:
            # no records yet
            Ediff = 0
        else:
            current = sum(filter(None, (E1, E2, E3, E4, E5, E6, E7, E8, E9, E10)))
            Ediff = current-previous

        # inserting records
        cursor.execute(f'INSERT INTO dailies VALUES (%(now)s, %(Ediff)s)', {"now": now, "Ediff": Ediff})
        self.database.commit()
        cursor.close()


# ----------------------------- #
# Constants                     #
# ----------------------------- #

CONSTANTS = {
    "historique": {
        "tags": {
            "p": "PAPP",
            "base": {
                "BASE": "E1"
            },
            "hchp": {
                "HCHC": "E1",
                "HCHP": "E2"
            },
            "tempo": {
                "BBHCJB": "E1",
                "BBHPJB": "E2",
                "BBHCJW": "E3",
                "BBHPJW": "E4",
                "BBHCJR": "E5",
                "BBHPJR": "E6",
            },
            "ejp": {
                "EJPHN": "E1",
                "EJPHPM": "E2"
            }
        }
    },
    "standard": {
        "tags": {
            "p": "SINSTS",
            "base": {
                "EASF01": "E1"
            },
            "hchp": {
                "EASF01": "E1",
                "EASF02": "E2"
            },
            "tempo": {
                "EASF01": "E1",
                "EASF02": "E2",
                "EASF03": "E3",
                "EASF04": "E4",
                "EASF05": "E5",
                "EASF06": "E6",
            },
            "ejp": {
                "EASF01": "E1",
                "EASF02": "E2"
            }
        }
    }
}


# ----------------------------- #
# Functions                     #
# ----------------------------- #

def init_logs():
    """
    Setup the log file.
    """
    log = logging.getLogger('linky')
    log.setLevel(logging.DEBUG)
    handler = logging.handlers.RotatingFileHandler('./logs/linky.log', maxBytes=1000000, backupCount=5) # Log file of 1 MB, 5 previous files kept
    formatter = logging.Formatter('[%(asctime)s][%(levelname)s] %(message)s', '%Y-%m-%d %H:%M:%S %z')
    handler.setFormatter(formatter)
    log.addHandler(handler)
    return log


def init_config():
    """
    Load configuration.
    """
    try:
        with open('config.yml', 'r') as f:
            config = yaml.safe_load(f)
    except Exception as e:
        log.critical(f'Something went wrong while opening config file: {e}', exc_info=True)
        print('Something went wrong while opening config file. See logs for more info.', file=sys.stderr)
        raise SystemExit(3)
    return config


def init_serial(device, mode="historique"):
    """
    Setup the serial connection.

    Args:
        dev (str): Linux device of the connector (like "/dev/ttyS0")
        mode (str): Linky mode: "historique" or "standard"
    """
    terminal = serial.Serial()
    terminal.port = device
    terminal.baudrate = 1200 if mode == "historique" else 9600
    terminal.stopbits = serial.STOPBITS_ONE
    terminal.bytesize = serial.SEVENBITS
    return terminal


def rechecksum(line, mode="historique"):
    """
    Check the line with its checksum in accordance to the algorithm.

    Args:
        line (str): The whole line from the serial output
        mode (str): Mode of the Linky. Defaults to "historique".
    """
    if mode == "historique":
        tag, value, checksum = line.split(chr(0x20), maxsplit=2)
        line_to_check = f"{tag} {value}"
    elif mode == "standard":
        line_to_check, checksum = line.rsplit(chr(0x09), maxsplit=1)
        line_to_check += chr(0x09)
    return (checksum == chr((sum([ord(i) for i in line_to_check]) & 0x3f) + 0x20))


# ----------------------------- #
# Initialization                #
# ----------------------------- #

# Logs
log = init_logs()

# Config
config = init_config()
log.setLevel(logging.DEBUG if config["debug"] else logging.INFO)
log.debug(f'Config loaded! Values: {config}')

# Serial connection to Linky
terminal = init_serial(config['device'], config["mode"])

# Database connection test. (We also create the schema, if it does not exist)
database = Database(config['database']['server'], config['database']['user'], config['database']['password'], config['database']['name'])


# ----------------------------- #
# Main loop                     #
# ----------------------------- #

if config.get('utc', False):
    current_loop_day = datetime.datetime.now(datetime.timezone.utc).day
    previous_loop_day = datetime.datetime.now(datetime.timezone.utc).day
else:
    current_loop_day = datetime.datetime.now().day
    previous_loop_day = datetime.datetime.now().day 

while True:
    log.debug("Cycle begins")

    if config.get('utc', False):
        current_loop_day = datetime.datetime.now(datetime.timezone.utc).day
    else:
        current_loop_day = datetime.datetime.now().day

    # Setting which values we want depending of the contract
    # "Tags" = prefixes on the serial output ("BASE", "HCHP"...)
    # "Meters" = "converted" columns E1, E2... depending on the contract
    tags = CONSTANTS[config["mode"]]["tags"][config["contract"]].keys()
    meters = CONSTANTS[config["mode"]]["tags"][config["contract"]].values()
    data = {meter: None for meter in meters}
    data["P"] = None

    # Now beginning to read data from Linky
    log.debug("Opening terminal...")
    terminal.open()

    # Reading continously output until we have all the data that interests us
    loop_count = 0
    while True:
        line_raw = terminal.readline()
        line = line_raw.decode('ascii').rstrip('\r\n')
        log.debug(f"Current line: {line} ({line_raw})")

        try:
            if config["mode"] == "historique":
                tag, value, checksum = line.split(chr(0x20), maxsplit=2)
            elif config["mode"] == "standard":
                particles = line.split(chr(0x09))
                if len(particles) == 4:
                    tag, value, timestamp, checksum = particles
                elif len(particles) == 3:
                    tag, value, checksum = particles
                else:
                    raise ValueError
        except ValueError:
            # Can happen if this is the first line
            continue
        
        if tag in tags:
            if rechecksum(line, config["mode"]):
                data[CONSTANTS[config["mode"]]["tags"][config["contract"]][tag]] = int(value)
        if tag in ("PAPP", "SINSTS"):
            if rechecksum(line, config["mode"]):
                data["P"] = int(value)
                loop_count += 1

        # Checking if we collected everything we need
        if all(value is not None for value in data.values()):
            log.debug(f"Output fully parsed: {data}. Closing terminal.")
            terminal.close()
            break

        if loop_count >= 10:
            log.error('Required data could not be found in the Linky output. Check if you specified "contract" and "mode" correctly in the configuration.')
            raise SystemExit(5)
    
    # Connecting to database
    log.debug("Connecting to database")

    # first record of the day? generating dailies
    if current_loop_day != previous_loop_day:
        log.debug(f"First record of the day! Inserting dailies record.")
        database.insert_dailies(data.get("E1"), data.get("E2"), data.get("E3"), data.get("E4"), data.get("E5"), data.get("E6"), data.get("E7"), data.get("E8"), data.get("E9"), data.get("E10"))

    if config.get('utc', False):
        previous_loop_day = datetime.datetime.now(datetime.timezone.utc).day
    else:
        previous_loop_day = datetime.datetime.now().day

    # inserting values
    log.debug("Inserting stream record")
    database.insert_stream(data.get("P"), data.get("E1"), data.get("E2"), data.get("E3"), data.get("E4"), data.get("E5"), data.get("E6"), data.get("E7"), data.get("E8"), data.get("E9"), data.get("E10"))

    log.debug(f"Cycle ends, sleeping for {config.get('interval', 60)} seconds")
    time.sleep(config.get('interval', 60))
