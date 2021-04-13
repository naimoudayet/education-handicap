import pymongo
from werkzeug.security import generate_password_hash, check_password_hash

#hashed_pass = 'pbkdf2:sha256:150000$7yBkxSN7O9$c45f88ba8dd9b511eaf1943c10a819f211d58dde6b40115bd645c783c8aa303e'

# print(check_password_hash(hashed_pass,'passwo8d'))

#print(generate_password_hash('password', 'pbkdf2:sha256', 10))


# connection au mongo
CLIENT = pymongo.MongoClient('mongodb://localhost:27017/')
# choisir base
DB = CLIENT['education_handicap']

# choisir collection
COLLECTION_USERS = DB['USERS']

data_1 = {
    'photo': 'user2-160x160.jpg',
    'nom': 'admin',
    'prenom': 'admin',
    'email': 'admin@gmail.com',
    # pass, mathod, salt
    'mot_de_passe': generate_password_hash('adminadmin', 'pbkdf2:sha256', 10),
    'role': 'ADMIN'
}
data_2 = {
    'photo': 'user2-160x160.jpg',
    'nom': 'test',
    'prenom': 'test',
    'email': 'test@gmail.com',
    # pass, mathod, salt
    'mot_de_passe': generate_password_hash('test', 'pbkdf2:sha256', 10),
    'role': 'ETUDIANT'
}
data_3 = {
    'photo': 'user2-160x160.jpg',
    'nom': 'prof',
    'prenom': 'prof',
    'email': 'prof@gmail.com',
    # pass, mathod, salt
    'mot_de_passe': generate_password_hash('test', 'pbkdf2:sha256', 10),
    'role': 'PROFESSEUR'
}

COLLECTION_USERS.insert_one(data_1)
COLLECTION_USERS.insert_one(data_2)
COLLECTION_USERS.insert_one(data_3)
