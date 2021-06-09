from flask import Flask, render_template, request, flash, redirect, url_for, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from bson.objectid import ObjectId
from datetime import datetime

from dotenv import load_dotenv
from flask import Flask, render_template, request, abort
from twilio.jwt.access_token import AccessToken
from twilio.jwt.access_token.grants import VideoGrant, ChatGrant
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

import os
import pymongo

load_dotenv()
twilio_account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
twilio_api_key_sid = os.environ.get('TWILIO_API_KEY_SID')
twilio_api_key_secret = os.environ.get('TWILIO_API_KEY_SECRET')
twilio_client = Client(twilio_api_key_sid, twilio_api_key_secret,
                       twilio_account_sid)

from functools import wraps

from technologie import technologies
from timezone import timezones
from langue import langues

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
target = os.path.join(APP_ROOT, r"static\img")

# connection au mongo
CLIENT = pymongo.MongoClient('mongodb://localhost:27017/')
# choisir base
DB = CLIENT['education_handicap']

# choisir collection
COLLECTION_USERS = DB['users']
COLLECTION_A_PROPOS = DB['a_propos']
COLLECTION_COMPETENCES = DB['competences']
COLLECTION_AVIS = DB['avis']
COLLECTION_COURS = DB['cours']
COLLECTION_CONVERSATION = DB['conversations']
COLLECTION_MESSAGES = DB['messages']

app = Flask(__name__)
app.debug = True
app.secret_key = 'MY_APP'

def get_chatroom(name):
    for conversation in twilio_client.conversations.conversations.list():
        if conversation.friendly_name == name:
            return conversation

    # a conversation with the given name does not exist ==> create a new one
    return twilio_client.conversations.conversations.create(
        friendly_name=name)


# Check if user logged in
def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'connected' in session:
            return f(*args, **kwargs)
        else:
            flash('Veuillez vous connecter', 'warning')
            return redirect(url_for('login'))
    return wrap


# Logout
@app.route('/logout')
@is_logged_in
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        mot_de_passe = request.form['mot_de_passe']

        result = COLLECTION_USERS.find_one({
            'email': email
        })

        if result:
            if check_password_hash(result['mot_de_passe'], mot_de_passe):

                session['connected'] = True
                session['_id'] = str(result['_id'])
                session['nom_prenom'] = result['nom_prenom']
                session['profil_pic'] = result['profil_pic']
                session['role'] = result['role']

                return redirect(url_for('index'))

            else:
                flash('svp, vérifiez votre email et mot de passe.', 'danger')
                return redirect(url_for('login'))
        else:
            flash('svp, vérifiez votre email et mot de passe.', 'danger')
            return redirect(url_for('login'))

    # GET
    return render_template('login.html')


@app.route('/inscription', methods=['GET', 'POST'])
def inscription():

    if 'connected' in session:
        return redirect(url_for('index'))

    if request.method == 'POST':
        role = request.form['role']
        nom_prenom = request.form['nom_prenom']
        email = request.form['email']
        mot_de_passe = request.form['mot_de_passe']

        result = COLLECTION_USERS.find_one({
            'email': email
        })

        if result:
            flash('Vous êtes déjà inscrit.', 'danger')
            return redirect(url_for('login'))
        else:

            result = COLLECTION_USERS.insert_one({
                'profil_pic': 'default_user.png',
                'nom_prenom': nom_prenom,
                'email': email,
                'mot_de_passe': generate_password_hash(mot_de_passe, 'pbkdf2:sha256', 10),
                'fuseau_horaire': 'GMT+0',
                'langue': 'Français',
                'role': role.upper(),
                'date_inscription': datetime.now()
            })

            if result:
                flash('Compte créé.', 'success')
                return redirect(url_for('login'))
            else:
                flash(
                    'vous ne pouvez pas vous s\'inscrire maintenant, réessayez plus tard.', 'danger')
                return redirect(url_for('inscription'))

    return render_template('inscription.html')


@app.route('/')
@is_logged_in
def index():
    if session['role'] == 'ADMIN':

        etudiants = list(COLLECTION_USERS.find(
            {'role': 'ETUDIANT'}).limit(3).sort("date_inscription", -1))
        professeurs = list(COLLECTION_USERS.find(
            {'role': 'PROFESSEUR'}).limit(3).sort("date_inscription", -1))
        cours = list(COLLECTION_COURS.find())

        return render_template('admin/index.html', etudiants=etudiants, professeurs=professeurs, cours=cours)

    if session['role'] == 'ETUDIANT':

        users = list(
            COLLECTION_USERS.find({
                'role': 'PROFESSEUR'
            })
        )
        competences = list(
            COLLECTION_COMPETENCES.find()
        )
        a_propos = list(
            COLLECTION_A_PROPOS.find()
        )

        return render_template('etudiant/index.html', users=users, competences=competences, a_propos=a_propos)

    if session['role'] == 'PROFESSEUR':
        return render_template('index.html')

    return render_template('index.html')


######################################################################################
# Partie ADMIN                                                                       #
######################################################################################
@app.route('/admin/professeurs')
@is_logged_in
def professeurs_index():
    professeurs = list(COLLECTION_USERS.find({
        'role': 'PROFESSEUR'
    }))
    return render_template('/admin/professeurs/index.html', professeurs=professeurs)


@app.route('/admin/professeurs/recherche', methods=['GET'])
@is_logged_in
def professeurs_recherche():

    mot_cle = request.args.get('mot_cle')

    professeurs = list(COLLECTION_USERS.find(
        {
            '$or': [
                {'nom_prenom': {'$regex': mot_cle+'.*', '$options': 'i'}}
            ],
            '$and': [
                {'role': 'PROFESSEUR'}
            ]
        }
    ))
    return render_template('/admin/professeurs/resultat.html', professeurs=professeurs, mot_cle=mot_cle)


@app.route('/admin/professeurs/details/<string:id>')
@is_logged_in
def professeurs_details(id):
    professeur = COLLECTION_USERS.find_one({'_id': ObjectId(id)})
    competences = list(COLLECTION_COMPETENCES.find({'id_utilisateur': id}))
    a_propos = COLLECTION_A_PROPOS.find_one({'id_utilisateur': id})
    avis = list(COLLECTION_AVIS.find({'id_professeur': id}))

    print(competences)
    return render_template('/admin/professeurs/details.html',
                           professeur=professeur,
                           avis=avis,
                           competences=competences,
                           a_propos=a_propos)


@app.route('/admin/etudiants')
@is_logged_in
def etudiants_index():
    etudiants = list(COLLECTION_USERS.find({
        'role': 'ETUDIANT'
    }))
    return render_template('/admin/etudiants/index.html', etudiants=etudiants)


@app.route('/admin/etudiants/recherche', methods=['GET'])
@is_logged_in
def etudiants_recherche():

    mot_cle = request.args.get('mot_cle')

    etudiants = list(COLLECTION_USERS.find(
        {
            '$or': [
                {'nom_prenom': {'$regex': mot_cle+'.*', '$options': 'i'}}
            ],
            '$and': [
                {'role': 'ETUDIANT'}
            ]
        }
    ))
    return render_template('/admin/etudiants/resultat.html', etudiants=etudiants, mot_cle=mot_cle)


@app.route('/admin/etudiants/details/<string:id>')
@is_logged_in
def etudiants_details(id):
    etudiant = COLLECTION_USERS.find_one({
        '_id': ObjectId(id)
    })

    return render_template('/admin/etudiants/details.html', etudiant=etudiant)


@app.route('/admin/cours')
@is_logged_in
def admin_cours_index():
    cours = list(COLLECTION_COURS.find().sort('date_creation', -1))
    users = list(COLLECTION_USERS.find())
    competences = list(COLLECTION_COMPETENCES.find())
    return render_template('/admin/cours/index.html', cours=cours, users=users, competences=competences)


@app.route('/admin/cours/details/<string:id>')
@is_logged_in
def admin_cours_details(id):
    if ObjectId.is_valid(id):
        users = list(COLLECTION_USERS.find())
        competences = list(COLLECTION_COMPETENCES.find())
        cours = COLLECTION_COURS.find_one({
            '_id': ObjectId(id)
        })
        if cours:
            return render_template('/admin/cours/details.html', cours=cours, users=users, competences=competences)

    return redirect(url_for('cours_index'))


@app.route('/admin/messages')
@is_logged_in
def admin_messages_index():
    id_user = session['_id']
    conversations = list(COLLECTION_CONVERSATION.find({
        '$or': [
            {
                'id_sender': id_user
            },
            {
                'id_receiver': id_user
            },
        ]
    }))
    users = list(COLLECTION_USERS.find({
        '_id': {'$ne': ObjectId(id_user)}
    }))
    return render_template('/admin/messages/index.html', users=users, conversations=conversations)


@app.route('/admin/messages/details/<string:id>')
@is_logged_in
def admin_messages_details(id):
    conversation = COLLECTION_CONVERSATION.find_one({
        '_id': ObjectId(id)
    })
    messages = list(COLLECTION_MESSAGES.find({
        'id_conversation': id
    })) 
    users = list(COLLECTION_USERS.find())
    return render_template('/admin/messages/details.html', users=users, conversation=conversation, messages=messages)


@app.route('/admin/messages/ajouter', methods=['GET', 'POST'])
@is_logged_in
def admin_messages_ajouter():
    id_user = session['_id']
    users = list(COLLECTION_USERS.find({
        '_id': {'$ne': ObjectId(id_user)}
    }))
    if request.method == 'POST':
        user = request.form['user']
        sujet = request.form['sujet']
        message = request.form['message']

        COLLECTION_CONVERSATION.insert_one({
            'id_sender': id_user,
            'id_receiver': user,
            'sujet': sujet,
            'message': message,
            'date_creation': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        flash('message envoyer', 'success')
        return redirect(url_for('admin_messages_index'))
    return render_template('/admin/messages/ajouter.html', users=users)


@app.route('/admin/messages/repondre/<string:id>', methods=['POST'])
@is_logged_in
def admin_messages_repondre(id):
    if ObjectId.is_valid(id):
        id_user = session['_id']

        message = request.form['message']
        COLLECTION_MESSAGES.insert_one({
            'id_conversation': id,
            'id_user': id_user,
            'message': message,
            'date_creation': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        return redirect(url_for('admin_messages_details', id=id))


@app.route('/admin/profil')
@is_logged_in
def admin_profil():
    return render_template('/admin/profil.html')


######################################################################################
# Partie Etudiant                                                                    #
######################################################################################


@app.route('/professeur/<string:id>')
def professeur_details(id):
    if ObjectId.is_valid(id):

        user = COLLECTION_USERS.find_one({
            '_id': ObjectId(id),
            'role': 'PROFESSEUR'
        })
        competences = list(
            COLLECTION_COMPETENCES.find({
                'id_utilisateur': id
            })
        )
        avis = list(
            COLLECTION_AVIS.find({
                'id_professeur': id
            })
        )

        note = 0
        if avis:
            for item in avis:
                note += int(item['avis'])

            note = note / len(avis)

        etudiants = list(
            COLLECTION_USERS.find({
                'role': 'ETUDIANT'
            })
        )
        a_propos = COLLECTION_A_PROPOS.find_one({
            'id_utilisateur': id
        })
        if user:
            return render_template('professeur/index.html', note=note, technologies=technologies, professeur=user,
                                   competences=competences, a_propos=a_propos, avis=avis, etudiants=etudiants)

    return redirect(url_for('index'))


######################################################################################
# Partie                                                                             #
######################################################################################


@app.route('/profil')
@is_logged_in
def profil_index():
    a_propos = COLLECTION_A_PROPOS.find_one({
        'id_utilisateur': session['_id']
    })
    competences = list(COLLECTION_COMPETENCES.find({
        'id_utilisateur': session['_id']
    }))
    profil = COLLECTION_USERS.find_one({
        '_id': ObjectId(session['_id'])
    })
    return render_template('/profil/index.html', profil=profil, a_propos=a_propos, competences=competences)


@app.route('/profil/modifier')
@is_logged_in
def profil_modifier():
    a_propos = COLLECTION_A_PROPOS.find_one({
        'id_utilisateur': session['_id']
    })
    competences = list(COLLECTION_COMPETENCES.find({
        'id_utilisateur': session['_id']
    }))
    profil = COLLECTION_USERS.find_one({
        '_id': ObjectId(session['_id'])
    })
    return render_template('/profil/modifier.html',
                           a_propos=a_propos,
                           competences=competences,
                           profil=profil,
                           timezones=timezones,
                           langues=langues
                           )


@app.route('/profil/update', methods=['POST'])
@is_logged_in
def profil_update():
    if request.method == 'POST':
        nom_prenom = request.form['nom_prenom']
        email = request.form['email']
        fuseau_horaire = request.form['fuseau_horaire']
        langue = request.form['langue']

        # upload image
        for upload in request.files.getlist('profil_pic'):
            # get file name
            img = upload.filename
            if img == '':
                # modifier
                result = COLLECTION_USERS.update_one({
                    '_id': ObjectId(session['_id'])
                }, {
                    '$set': {
                        'nom_prenom': nom_prenom,
                        'email': email,
                        'fuseau_horaire': fuseau_horaire,
                        'langue': langue
                    }
                })
                if result:
                    flash('Profil modifier.', 'success')
                    return redirect(url_for('profil_modifier'))
                else:
                    flash(
                        'vous ne pouvez pas vous modifier votre profil maintenant, réessayez plus tard.', 'danger')
                    return redirect(url_for('profil_modifier'))
            else:
                # get file extension
                ext = img.split('.')[1].lower()
                if ext in ['png', 'jpg', 'jpeg']:
                    # save image in target
                    destination = '/'.join([target, img])
                    upload.save(destination)

                    # modifier
                    result = COLLECTION_USERS.update_one({
                        '_id': ObjectId(session['_id'])
                    }, {
                        '$set': {
                            'profil_pic': img,
                            'nom_prenom': nom_prenom,
                            'email': email,
                            'fuseau_horaire': fuseau_horaire
                        }
                    })
                    if result:
                        flash('Profil modifier.', 'success')
                        return redirect(url_for('profil_modifier'))
                    else:
                        flash(
                            'vous ne pouvez pas vous modifier votre profil maintenant, réessayez plus tard.', 'danger')
                        return redirect(url_for('profil_modifier'))
                flash(
                    'Seuls les fichiers {png, jpg, jpeg} sont autorisés...', 'danger')
                return render_template('entreprise/create.html')

    return render_template('/profil/modifier.html')


@app.route('/profil/update_password', methods=['POST'])
@is_logged_in
def profil_update_password():
    if request.method == 'POST':
        mot_de_passe_actuel = request.form['mot_de_passe_actuel']
        nouveau_pass = request.form['nouveau_pass']
        confirmer_pass = request.form['confirmer_pass']

        user = COLLECTION_USERS.find_one({
            '_id': ObjectId(session['_id'])
        })

        if check_password_hash(user['mot_de_passe'], mot_de_passe_actuel):
            if nouveau_pass == confirmer_pass:
                # modifier
                result = COLLECTION_USERS.update_one({
                    '_id': ObjectId(session['_id'])
                }, {
                    '$set': {
                        'mot_de_passe': generate_password_hash(nouveau_pass, 'pbkdf2:sha256', 10),
                    }
                })
                if result:
                    flash('Profil modifier.', 'success')
                    return redirect(url_for('profil_modifier'))
                else:
                    flash(
                        'vous ne pouvez pas vous modifier votre profil maintenant, réessayez plus tard.', 'danger')
                    return redirect(url_for('profil_modifier'))
            else:
                flash('mot de passe non identiques.', 'danger')
                return redirect(url_for('profil_modifier'))
        else:
            flash('svp, vérifiez votre mot de passe.', 'danger')
            return redirect(url_for('profil_modifier'))

    return render_template('/profil/modifier.html')


@app.route('/profil/a_propos', methods=['POST'])
@is_logged_in
def profil_a_propos():
    if request.method == 'POST':
        describe_you = request.form['describe_you']
        biographie = request.form['biographie']

        result = COLLECTION_A_PROPOS.find_one({
            'id_utilisateur': session['_id']
        })

        if result:
            # modifier
            result = COLLECTION_A_PROPOS.update_one({
                '_id': result['_id']
            }, {
                '$set': {
                    'describe_you': describe_you,
                    'biographie': biographie
                }
            })
            if result:
                flash('Profil modifier.', 'success')
                return redirect(url_for('profil_modifier'))
            else:
                flash(
                    'vous ne pouvez pas vous modifier votre profil maintenant, réessayez plus tard.', 'danger')
                return redirect(url_for('profil_modifier'))
        else:
            # ajouter
            data = {
                'id_utilisateur': session['_id'],
                'describe_you': describe_you,
                'biographie': biographie
            }

            result = COLLECTION_A_PROPOS.insert_one(data)

            if result:
                flash('Profil modifier.', 'success')
                return redirect(url_for('profil_modifier'))
            else:
                flash(
                    'vous ne pouvez pas vous modifier votre profil maintenant, réessayez plus tard.', 'danger')
                return redirect(url_for('profil_modifier'))

    return render_template('/profil/modifier.html')


@app.route('/profil/modifier/competence/ajouter', methods=['GET', 'POST'])
@is_logged_in
def competence_ajouter():
    if request.method == 'POST':
        categorie = request.form['categorie']
        technologie = request.form['technologie']
        annee_experience = request.form['annee_experience']
        technologie_connexes = request.form['technologie_connexes']
        experience_technologie = request.form['experience_technologie']

        # ajouter
        data = {
            'id_utilisateur': session['_id'],
            'categorie': categorie,
            'technologie': technologie,
            'annee_experience': annee_experience,
            'technologie_connexes': technologie_connexes,
            'experience_technologie': experience_technologie
        }

        result = COLLECTION_COMPETENCES.insert_one(data)

        if result:
            flash('Compétences ajouter.', 'success')
            return redirect(url_for('profil_modifier'))
        else:
            flash(
                'vous ne pouvez pas vous modifier votre profil maintenant, réessayez plus tard.', 'danger')
            return redirect(url_for('profil_modifier'))

    return render_template('/profil/competence/ajouter.html', technologies=technologies)


@app.route('/profil/modifier/competence/modifier/<string:id>', methods=['GET', 'POST'])
@is_logged_in
def competence_modifier(id):
    if ObjectId.is_valid(id):
        competence = COLLECTION_COMPETENCES.find_one({
            '_id': ObjectId(id)
        })
        if competence:
            if request.method == 'POST':
                categorie = request.form['categorie']
                technologie = request.form['technologie']
                annee_experience = request.form['annee_experience']
                technologie_connexes = request.form['technologie_connexes']
                experience_technologie = request.form['experience_technologie']

                # modifier

                result = COLLECTION_COMPETENCES.update_one({
                    '_id': ObjectId(id)
                },  {
                    '$set': {
                        'categorie': categorie,
                        'technologie': technologie,
                        'annee_experience': annee_experience,
                        'technologie_connexes': technologie_connexes,
                        'experience_technologie': experience_technologie
                    }
                })

                if result:
                    flash('Compétences modifier.', 'success')
                    return redirect(url_for('profil_modifier'))
                else:
                    flash(
                        'vous ne pouvez pas vous modifier votre profil maintenant, réessayez plus tard.', 'danger')
                    return redirect(url_for('profil_modifier'))

            return render_template('/profil/competence/modifier.html', competence=competence, technologies=technologies)

    flash('Compétences introuvable.', 'success')
    return redirect(url_for('profil_modifier'))


@app.route('/profil/modifier/competence/supprimer/<string:id>', methods=['POST'])
@is_logged_in
def competence_supprimer(id):
    if ObjectId.is_valid(id):
        competence = COLLECTION_COMPETENCES.find_one({
            '_id': ObjectId(id)
        })
        if competence:
            if request.method == 'POST':

                # modifier
                result = COLLECTION_COMPETENCES.delete_one({
                    '_id': ObjectId(id)
                })

                if result:
                    flash('Compétences supprimer.', 'success')
                    return redirect(url_for('profil_modifier'))
                else:
                    flash(
                        'vous ne pouvez pas vous modifier votre profil maintenant, réessayez plus tard.', 'danger')
                    return redirect(url_for('profil_modifier'))

    flash('Compétences introuvable.', 'success')
    return redirect(url_for('profil_modifier'))


@app.route('/avis_ajouter/<string:id>', methods=['POST'])
@is_logged_in
def avis_ajouter(id):
    commentaire = request.form['commentaire']
    avis = request.form['avis']

    result = COLLECTION_AVIS.find_one({
        'id_professeur': id,
        'id_etudiant': session['_id']
    })

    if result:
        return redirect(url_for('professeur_details', id=id))
    else:
        now = datetime.now()
        dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
        COLLECTION_AVIS.insert_one({
            'id_professeur': id,
            'id_etudiant': session['_id'],
            'commentaire': commentaire,
            'avis': avis,
            'date_heure': dt_string
        })
        return redirect(url_for('professeur_details', id=id))


def searchCategorie(cat, competences):
    for comp in competences:

        if cat == comp['categorie']:
            return True

    return False


@app.route('/api/professeurs/<int:categories>/<int:horaires>/<int:langues>')
def api_professeurs(categories, horaires, langues):

    etudiant = COLLECTION_USERS.find_one({
        '_id': ObjectId(session['_id'])
    })

    #mon_horaire = etudiant['horaire']
    mon_horaire = 0
    horaires_filter = [
        mon_horaire,
        3,
        7,
        12
    ]

    langues_filter = [
        'Arabe',
        'Français',
        'Anglais'
    ]

    categories_filter = [
        'Développement web',
        'Développement d\'applications mobiles',
        'Langages de programmation',
        'Data science',
        'Bases de données'
    ]

    users = list(
        COLLECTION_USERS.find({
            'role': 'PROFESSEUR'
        })
    )

    professeurs = []
    for user in users:

        apropos = COLLECTION_A_PROPOS.find_one({
            'id_utilisateur': str(user['_id'])
        })

        if apropos:
            apropos = {
                '_id': str(apropos['_id']),
                'describe_you': apropos['describe_you'],
                'biographie': apropos['biographie'],
            }
        else:
            apropos = {}

        results = list(
            COLLECTION_COMPETENCES.find({
                'id_utilisateur': str(user['_id'])
            })
        )
        competences = []
        for result in results:
            competence = {
                '_id': str(result['_id']),
                'categorie': result['categorie'],
                'technologie': result['technologie'],
                'annee_experience': result['annee_experience'],
                'technologie_connexes': result['technologie_connexes'],
                'experience_technologies': result['experience_technologie'],
            }
            competences.append(competence)

        professeur = {
            '_id': str(user['_id']),
            'profil_pic': user['profil_pic'],
            'nom_prenom': user['nom_prenom'],
            'email': user['email'],
            'fuseau_horaire': user['fuseau_horaire'],
            'langue': user['langue'],
            'a_propos': apropos,
            'competences': competences
        }

        if categories == 0:
            if horaires == 0:
                if langues == 0:
                    professeurs.append(professeur)
                elif langues != 0:
                    if langues_filter[langues-1] == professeur['langue']:
                        professeurs.append(professeur)
            elif horaires != 0:
                fuseau = int(professeur['fuseau_horaire'].split('+')[1])
                if langues == 0:
                    if horaires_filter[horaires-1] <= fuseau:
                        professeurs.append(professeur)
                elif langues != 0:
                    if langues_filter[langues-1] == professeur['langue'] and horaires_filter[horaires-1] <= fuseau:
                        professeurs.append(professeur)
        elif categories != 0:
            cat = categories_filter[int(categories)-1]
            if horaires == 0:
                if langues == 0:
                    if searchCategorie(cat, competences):
                        professeurs.append(professeur)
                elif langues != 0:
                    if langues_filter[langues-1] == professeur['langue'] and searchCategorie(cat, competences):
                        professeurs.append(professeur)
            elif horaires != 0:
                fuseau = int(professeur['fuseau_horaire'].split('+')[1])
                if langues == 0:
                    if horaires_filter[horaires-1] <= fuseau and searchCategorie(cat, competences):
                        professeurs.append(professeur)
                elif langues != 0:
                    if langues_filter[langues-1] == professeur['langue'] and horaires_filter[horaires-1] <= fuseau and searchCategorie(cat, competences):
                        professeurs.append(professeur)

    return jsonify(professeurs)


@app.route('/cours')
def cours():
    id_professeur = session['_id']

    cours = list(COLLECTION_COURS.find({
        'id_professeur': id_professeur
    }))

    etudiants = list(COLLECTION_USERS.find({
        'role': 'ETUDIANT'
    }))

    competences = list(COLLECTION_COMPETENCES.find({
        'id_utilisateur': id_professeur
    }))
    return render_template('/cours/index.html', cours=cours, etudiants=etudiants, competences=competences)


@app.route('/cours/details/<string:id>')
def cours_details(id):
    if ObjectId.is_valid(id):

        id_professeur = session['_id']
        cours = COLLECTION_COURS.find_one({
            '_id': ObjectId(id)
        })

        if cours:
            etudiants = list(COLLECTION_USERS.find({
                'role': 'ETUDIANT'
            }))

            competences = list(COLLECTION_COMPETENCES.find({
                'id_utilisateur': id_professeur
            }))
            return render_template('/cours/details.html', cours=cours, etudiants=etudiants, competences=competences)
    
    return redirect(url_for('cours'))

@app.route('/cours_login', methods=['POST'])
def cours_login():
    username = request.get_json(force=True).get('username')
    if not username:
        abort(401)

    conversation = get_chatroom('My Room')
    try:
        conversation.participants.create(identity=username)
    except TwilioRestException as exc:
        # do not error if the user is already in the conversation
        if exc.status != 409:
            raise

    token = AccessToken(twilio_account_sid, twilio_api_key_sid,
                        twilio_api_key_secret, identity=username)
    token.add_grant(VideoGrant(room='My Room'))
    token.add_grant(ChatGrant(service_sid=conversation.chat_service_sid))

    return {'token': token.to_jwt().decode(),
            'conversation_sid': conversation.sid}


@app.route('/cours/ajouter', methods=['GET', 'POST'])
def cours_ajouter():
    id_professeur = session['_id']

    etudiants = list(COLLECTION_USERS.find({
        'role': 'ETUDIANT'
    }))
    competences = list(COLLECTION_COMPETENCES.find({
        'id_utilisateur': id_professeur
    }))

    if request.method == 'POST':
        module = request.form['module']
        etudiant = request.form['etudiant']
        date = request.form['date']
        heure = request.form['heure']

        result = COLLECTION_COURS.find_one({
            'id_etudiant': etudiant,
            'date': date,
            'heure': heure
        })

        if result:
            flash('cours déja ajouter', 'danger')
            return render_template('/cours/ajouter.html', etudiants=etudiants, competences=competences)
        else:
            COLLECTION_COURS.insert_one({
                'id_professeur': id_professeur,
                'id_etudiant': etudiant,
                'id_competence': module,
                'date': date,
                'heure': heure,
                'date_creation': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })

            flash('cours ajouter', 'success')
            return redirect(url_for('cours'))

    return render_template('/cours/ajouter.html', etudiants=etudiants, competences=competences)


@app.route('/messages')
def messages_index():
    id_user = session['_id']

    conversations = list(COLLECTION_CONVERSATION.find({
        '$or': [
            {
                'id_sender': id_user
            },
            {
                'id_receiver': id_user
            },
        ]
    }))

    if session['role'] == 'ETUDIANT':

        users = list(COLLECTION_USERS.find({
            'role': 'PROFESSEUR'
        }))
        apropos = list(COLLECTION_A_PROPOS.find())
    else:
        users = list(COLLECTION_USERS.find({
            'role': 'ETUDIANT'
        }))
        apropos = []
    return render_template('/messages/index.html', conversations=conversations, users=users, apropos=apropos)


@app.route('/messages/<string:id>')
def messages_details(id):
    id_user = session['_id']

    conversation = COLLECTION_CONVERSATION.find_one({
        '$or': [
            {
                '$and': [
                    {'id_sender': id_user},
                    {'id_receiver': id},
                ]
            },
            {
                '$and': [
                    {'id_receiver': id_user},
                    {'id_sender': id},
                ]
            }
        ]
    })

    if conversation:
        messages = list(COLLECTION_MESSAGES.find({
            'id_conversation': str(conversation['_id'])
        }))

        if session['role'] == 'ETUDIANT':

            users = list(COLLECTION_USERS.find({
                'role': 'PROFESSEUR'
            }))
        else:
            users = list(COLLECTION_USERS.find({
                'role': 'ETUDIANT'
            }))

        is_new = len(conversation)
    else:
        messages = []
        users = []
        is_new = 0

    return render_template('/messages/details.html',
                           id=id, conversation=conversation, messages=messages, is_new=is_new, users=users)


@app.route('/messages/send/<string:id>/<int:is_new>/<string:id_convo>', methods=['POST'])
def messages_send(id, is_new, id_convo):

    id_sender = session['_id']
    message = request.form['message']

    if is_new == 0:
        # create new convo
        COLLECTION_CONVERSATION.insert_one({
            'id_sender': id_sender,
            'id_receiver': id,
            'message': message,
            'date_creation': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
    else:
        COLLECTION_MESSAGES.insert_one({
            'id_conversation': id_convo,
            'id_user': id_sender,
            'message': message,
            'date_creation': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })

    return redirect(url_for('messages_details', id=id))


@app.route('/etudiant/cours')
def etudiant_cours():
    id_etudiant = session['_id']

    cours = list(COLLECTION_COURS.find({
        'id_etudiant': id_etudiant
    }))

    professeurs = list(COLLECTION_USERS.find({
        'role': 'PROFESSEUR'
    }))

    competences = list(COLLECTION_COMPETENCES.find())
    return render_template('/etudiant/cours/index.html', cours=cours, professeurs=professeurs, competences=competences)


@app.route('/etudiant/cours/details/<string:id>')
def etudiant_cours_details(id):
    if ObjectId.is_valid(id):
 
        cours = COLLECTION_COURS.find_one({
            '_id': ObjectId(id)
        })

        if cours:
            professeur = COLLECTION_USERS.find_one({
                 '_id': ObjectId( cours['id_professeur'])
            })

            competence = COLLECTION_COMPETENCES.find_one({
                '_id': ObjectId( cours['id_competence'])
            })
            return render_template('/etudiant/cours/details.html', cours=cours, professeur=professeur, competence=competence)
    
    return redirect(url_for('etudiant_cours'))

@app.errorhandler(404)
def page_not_found(error):
    return render_template('error.html'), 404


if __name__ == '__main__':
    app.run(ssl_context=('cert.pem', 'key.pem'), host='0.0.0.0')
