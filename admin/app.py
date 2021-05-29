from flask import Flask, render_template, request, flash, redirect, url_for, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from bson.objectid import ObjectId
from datetime import datetime

import os
import pymongo

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

app = Flask(__name__)
app.debug = True
app.secret_key = 'MY_APP'

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

    return render_template('index.html')


######################################################################################
# Partie ADMIN                                                                       #
######################################################################################
@app.route('/professeurs')
@is_logged_in
def professeurs_index():
    professeurs = list(COLLECTION_USERS.find({
        'role': 'PROFESSEUR'
    }))
    return render_template('/admin/professeurs/index.html', professeurs=professeurs)


@app.route('/professeurs/recherche', methods=['GET'])
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


@app.route('/professeurs/details/<string:id>')
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


@app.route('/etudiants')
@is_logged_in
def etudiants_index():
    etudiants = list(COLLECTION_USERS.find({
        'role': 'ETUDIANT'
    }))
    return render_template('/admin/etudiants/index.html', etudiants=etudiants)


@app.route('/etudiants/recherche', methods=['GET'])
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


@app.route('/etudiants/details/<string:id>')
@is_logged_in
def etudiants_details(id):
    etudiant = COLLECTION_USERS.find_one({
        '_id': ObjectId(id)
    })

    return render_template('/admin/etudiants/details.html', etudiant=etudiant)


@app.route('/admin/profil')
@is_logged_in
def admin_profil():
    return render_template('/admin/profil.html')
######################################################################################
# Partie                                                                             #
######################################################################################


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
            apropos= {
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
            'langue': user['langue'] ,
            'a_propos':apropos,
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


@app.errorhandler(404)
def page_not_found(error):
    return render_template('error.html'), 404


if __name__ == '__main__':
    app.run()
