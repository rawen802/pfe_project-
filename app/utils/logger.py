import logging
import os

def setup_logger(log_file="logs/network_app.log"):
    # Crée le dossier pour le fichier de log si nécessaire
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    # Création du logger
    logger = logging.getLogger("NetworkApp")
    logger.setLevel(logging.DEBUG)

    # Formatter
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")  

    # StreamHandler pour console
    ch = logging.StreamHandler()  
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    # FileHandler pour fichier
    fh = logging.FileHandler(log_file)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    return logger