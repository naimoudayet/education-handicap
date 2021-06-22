import pymongo
import random
import string

from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

CLIENT = pymongo.MongoClient('mongodb://localhost:27017/')

DB = CLIENT['education_handicap']
COLLECTION_USERS = DB['users']


def get_random_string(length, letters):
    result_str = ''.join(random.choice(letters) for i in range(length))
    return result_str


for i in range(20):
    nom_prenom = get_random_string(10, string.ascii_lowercase)
    data = {
        'profil_pic': 'default_user.png',
        'nom_prenom': nom_prenom,
        'email': nom_prenom+'@gmail.com',
        'mot_de_passe': generate_password_hash(nom_prenom, 'pbkdf2:sha256', 10),
        'fuseau_horaire': 'GMT+0',
        'langue': 'Français',
        'role': 'PROFESSEUR',
        'date_inscription': datetime.now(),
        'etat': 'ACTIVER'
    }

    COLLECTION_USERS.insert_one(data)

for i in range(20):
    nom_prenom = get_random_string(10, string.ascii_lowercase)
    data = {
        'profil_pic': 'default_user.png',
        'nom_prenom': nom_prenom,
        'email': nom_prenom+'@gmail.com',
        'mot_de_passe': generate_password_hash(nom_prenom, 'pbkdf2:sha256', 10),
        'fuseau_horaire': 'GMT+0',
        'langue': 'Français',
        'role': 'ETUDIANT',
        'date_inscription': datetime.now(),
        'etat': 'ACTIVER'
    }

    COLLECTION_USERS.insert_one(data)


data = {
    'profil_pic': 'default_user.png',
    'nom_prenom': 'admin admin',
    'email': 'admin@gmail.com',
    'mot_de_passe': generate_password_hash('adminadmin', 'pbkdf2:sha256', 10),
    'fuseau_horaire': 'GMT+0',
    'langue': 'Français',
    'role': 'ADMIN',
    'date_inscription': datetime.now(),
    'etat': 'ACTIVER'
}

COLLECTION_USERS.insert_one(data)
