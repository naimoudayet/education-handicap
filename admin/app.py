from flask import Flask, render_template, request, flash, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from bson.objectid import ObjectId
import pymongo

from functools import wraps

# connection au mongo
CLIENT = pymongo.MongoClient('mongodb://localhost:27017/')
# choisir base
DB = CLIENT['education_handicap']

# choisir collection
COLLECTION_USERS = DB['USERS']

app = Flask(__name__)
app.debug = True
app.secret_key = 'MY_APP'

# Check if user logged in


def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'connected' in session:
            if session['role'] == 'ADMIN':
                return f(*args, **kwargs)
            else:
                flash('vous n\'êtes pas autorisé à accéder à cette page.', 'warning')
                return redirect(url_for('login'))
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
                'profil_pic': 'boxed-bg.jpg',
                'nom_prenom': nom_prenom,
                'email': email,
                'mot_de_passe': generate_password_hash(mot_de_passe, 'pbkdf2:sha256', 10),
                'role': role.upper()
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
def index():
    if  session['role'] == 'ADMIN':
        return render_template('admin/index.html')
    
    if  session['role'] == 'ETUDIANT':
        return render_template('etudiant/index.html')
        
    return render_template('index.html')


@app.route('/professeurs')
@is_logged_in
def professeurs_index():
    professeurs = list(COLLECTION_USERS.find({
        'role': 'PROFESSEUR'
    }))
    return render_template('/professeurs/index.html', professeurs=professeurs)


@app.route('/professeurs/recherche', methods=['GET'])
@is_logged_in
def professeurs_recherche():

    mot_cle = request.args.get('mot_cle')

    professeurs = list(COLLECTION_USERS.find(
        {
            '$or': [
                {'nom': {'$regex': mot_cle+'.*'}},
                {'prenom': {'$regex': mot_cle+'.*'}}
            ],
            '$and': [
                {'role': 'PROFESSEUR'}
            ]
        }
    ))
    return render_template('/professeurs/resultat.html', professeurs=professeurs, mot_cle=mot_cle)


@app.route('/professeurs/details/<string:id>')
@is_logged_in
def professeurs_details(id):
    professeur = COLLECTION_USERS.find_one({
        '_id': ObjectId(id)
    })

    return render_template('/professeurs/details.html', professeur=professeur)


@app.route('/etudiants')
@is_logged_in
def etudiants_index():
    etudiants = list(COLLECTION_USERS.find({
        'role': 'ETUDIANT'
    }))
    return render_template('/etudiants/index.html', etudiants=etudiants)


@app.route('/etudiants/recherche', methods=['GET'])
@is_logged_in
def etudiants_recherche():

    mot_cle = request.args.get('mot_cle')

    etudiants = list(COLLECTION_USERS.find(
        {
            '$or': [
                {'nom': {'$regex': mot_cle+'.*'}},
                {'prenom': {'$regex': mot_cle+'.*'}}
            ],
            '$and': [
                {'role': 'ETUDIANT'}
            ]
        }
    ))
    return render_template('/etudiants/resultat.html', etudiants=etudiants, mot_cle=mot_cle)


@app.route('/etudiants/details/<string:id>')
@is_logged_in
def etudiants_details(id):
    etudiant = COLLECTION_USERS.find_one({
        '_id': ObjectId(id)
    })

    return render_template('/etudiants/details.html', etudiant=etudiant)


@app.errorhandler(404)
def page_not_found(error):
    return render_template('error.html'), 404


if __name__ == '__main__':
    app.run()
