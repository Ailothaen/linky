#!/usr/bin/python3

# stdlib
import serial, MySQLdb, datetime, sys, logging, logging.handlers

# 3rd party
import yaml


def init_log_system():
    """
    Initializes log system
    """
    log = logging.getLogger('linky')
    log.setLevel(logging.DEBUG) # Define minimum severity here
    handler = logging.handlers.RotatingFileHandler('./logs/linky.log', maxBytes=1000000, backupCount=5) # Log file of 1 MB, 5 previous files kept
    formatter = logging.Formatter('[%(asctime)s][%(module)s][%(levelname)s] %(message)s', '%Y-%m-%d %H:%M:%S %z') # Custom line format and time format to include the module and delimit all of this well
    handler.setFormatter(formatter)
    log.addHandler(handler)
    return log


def load_config():
    """
    Loads config file
    """
    try:
        with open('config.yml', 'r') as f:
            config = yaml.safe_load(f)
    except Exception as e:
        log.critical('Something went wrong while opening config file:', exc_info=True)
        print('Something went wrong while opening config file. See logs for more info.', file=sys.stderr)
        raise SystemExit(3)
    else:
        return config


def setup_serial(dev):
    """
    Builds the serial connection object.

    Args:
        dev (str): Linux device of the connector (like "/dev/ttyS0")
    """
    terminal = serial.Serial()
    terminal.port = dev
    terminal.baudrate = 1200
    terminal.stopbits = serial.STOPBITS_ONE
    terminal.bytesize = serial.SEVENBITS
    return terminal


def test_db_connection(server, user, password, name):
    """
    Tests DB connection, and also creates the schema if missing

    Args:
        server (str): Database server
        user (str): Database user
        password (str): Database user password
        name (str): Database name
    """
    # testing connection
    db, cr = open_db(server, user, password, name)

    # create schema if first connection
    stream_exists = cr.execute(f"SELECT * FROM information_schema.tables WHERE table_schema = '{name}' AND table_name = 'stream' LIMIT 1;")
    dailies_exists = cr.execute(f"SELECT * FROM information_schema.tables WHERE table_schema = '{name}' AND table_name = 'dailies' LIMIT 1;")

    if stream_exists == 0 or dailies_exists == 0:
        log.info("Database schema is not there, creating it...")
        try:
            cr.execute("CREATE TABLE `dailies` (`id` int(10) UNSIGNED NOT NULL,`clock` date NOT NULL,`BASE_diff` int(11) NOT NULL) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;")
            cr.execute("CREATE TABLE `stream` (`id` int(20) UNSIGNED NOT NULL,`clock` datetime NOT NULL,`BASE` int(11) NOT NULL,`PAPP` int(11) NOT NULL,`BASE_diff` int(11) NOT NULL) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;")
            cr.execute("ALTER TABLE `dailies` ADD PRIMARY KEY (`id`), ADD KEY `clock` (`clock`);")
            cr.execute("ALTER TABLE `stream` ADD PRIMARY KEY (`id`), ADD KEY `clock` (`clock`);")
            cr.execute("ALTER TABLE `dailies` MODIFY `id` int(10) UNSIGNED NOT NULL AUTO_INCREMENT;")
            cr.execute("ALTER TABLE `stream` MODIFY `id` int(10) UNSIGNED NOT NULL AUTO_INCREMENT;")
            db.commit()
        except MySQLdb._exceptions.OperationalError:
            log.critical('Something went wrong while trying to create database schema:', exc_info=True)
            print('Something went wrong while trying to create database schema. See logs for more info.', file=sys.stderr)
            raise SystemExit(4)
        else:
            log.info("Database schema created successfully")


def open_db(server, user, password, name):
    """
    Connects to database

    Args:
        server (str): Database server
        user (str): Database user
        password (str): Database user password
        name (str): Database name
    """
    try:
        db = MySQLdb.connect(server, user, password, name)
        cr = db.cursor()
        return db, cr
    except MySQLdb._exceptions.OperationalError:
        log.critical('Something went wrong while connecting to database server:', exc_info=True)
        print('Something went wrong while connecting to database server. See logs for more info.', file=sys.stderr)
        raise SystemExit(4)


def close_db(db):
    """
    Closes connection to database

    Args:
        db (type): MySQLdb database object
    """
    db.close()


def insert_stream(config, db, cr, BASE, PAPP):
    """
    Insert a record in the stream table

    Args:
        config (dict): Loaded config from yaml file
        db (type): MySQLdb database object
        cr (type): MySQLdb cursor object
        BASE (int): Linky BASE value (Wh meter)
        PAPP (int): Linky PAPP value (current VA power)
    """
    # generating time
    if config.get('use_utc', False):
        now = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    else:
        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # retrieving previous BASE and calculating BASE_diff
    cr.execute("SELECT BASE FROM stream ORDER BY clock DESC LIMIT 1;")
    try:
        previous = cr.fetchone()[0]
    except TypeError:
        # no records yet
        BASE_diff = 0
    else:
        BASE_diff = BASE-int(previous)

    # inserting records
    cr.execute(f'INSERT INTO stream VALUES (NULL, %(now)s, %(BASE)s, %(PAPP)s, %(BASE_diff)s);', {"now": now, "BASE": BASE, "PAPP": PAPP, "BASE_diff": BASE_diff})
    db.commit()


def insert_dailies(config, db, cr, BASE):
    """
    Inserts a record in the dailies table

    Args:
        config (dict): Loaded config from yaml file
        db (type): MySQLdb database object
        cr (type): MySQLdb cursor object
        BASE (int): Linky BASE value (Wh meter)
    """
    # getting previous day midnight BASE value
    cr.execute("SELECT clock, BASE from `stream` INNER JOIN (SELECT MIN(clock) AS firstOfTheDay FROM `stream` GROUP BY DATE(clock)) joint ON `stream`.clock = joint.firstOfTheDay ORDER BY `stream`.clock DESC LIMIT 1;")
    try:
        previous = cr.fetchone()[1]
    except TypeError:
        # no records yet
        diff = 0
    else:
        diff = BASE-previous
    
    if config.get('use_utc', False):
        now = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d')
    else:
        now = datetime.datetime.now().strftime('%Y-%m-%d')

    cr.execute(f'INSERT INTO dailies VALUES (NULL, %(now)s, %(diff)s)', {"now": now, "diff": diff})
    db.commit()


# Initializing log system
log = init_log_system()
