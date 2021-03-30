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

    if 'connected' in session:
        return redirect(url_for('index'))

    if request.method == 'POST':
        email = request.form['email']
        mot_de_passe = request.form['mot_de_passe']

        result = COLLECTION_USERS.find_one({
            'email': email
        })

        if result:
            if check_password_hash(result['mot_de_passe'], mot_de_passe):
                if result['role'] == 'ADMIN':

                    session['connected'] = True
                    session['_id'] = str(result['_id'])
                    session['nom_prenom'] = result['nom']+' '+result['prenom']
                    session['photo'] = result['photo']
                    session['role'] = result['role']

                    return redirect(url_for('index'))
                else:
                    flash(
                        'vous n\'êtes pas autorisé à accéder à cette page.', 'warning')
                    return redirect(url_for('login'))
            else:
                flash('svp, vérifiez votre email et mot de passe.', 'danger')
                return redirect(url_for('login'))
        else:
            flash('svp, vérifiez votre email et mot de passe.', 'danger')
            return redirect(url_for('login'))

    # GET
    return render_template('login.html')


@app.route('/')
@is_logged_in
def index():
    return render_template('index.html')


@app.route('/professeurs')
@is_logged_in
def professeurs_index():
    professeurs = list(COLLECTION_USERS.find({
        'role': 'PROFESSEUR'
    }))
    return render_template('/professeurs/index.html', professeurs=professeurs)


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


@app.route('/etudiants/ajouter')
@is_logged_in
def etudiants_ajouter():
    return render_template('/etudiants/ajouter.html')


@app.route('/etudiants/modifier')
@is_logged_in
def etudiants_modifier():
    return render_template('/etudiants/modifier.html')



@app.errorhandler(404)
def page_not_found(error):
    return render_template('error.html'),404


if __name__ == '__main__':
    app.run()
