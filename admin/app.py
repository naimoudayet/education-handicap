from flask import Flask, render_template, request, flash, redirect, url_for

app = Flask(__name__)
app.debug = True
app.secret_key = 'MY_APP'

@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':
        email = request.form['email']
        mot_de_passe = request.form['mot_de_passe']
        
        if email == 'admin@gmail.com' and mot_de_passe == 'adminadmin':
            return redirect(url_for('index'))
        else:
            flash('svp, vérifiez votre email et mot de passe.')
            return redirect(url_for('login'))


    # GET
    return render_template('login.html')


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/professeurs')
def professeurs_index():
    return render_template('/professeurs/index.html')

@app.route('/professeurs/ajouter')
def professeurs_ajouter():
    return render_template('/professeurs/ajouter.html')

@app.route('/professeurs/modifier')
def professeurs_modifier():
    return render_template('/professeurs/modifier.html')

@app.route('/etudiants')
def etudiants_index():
    return render_template('/etudiants/index.html')

@app.route('/etudiants/ajouter')
def etudiants_ajouter():
    return render_template('/etudiants/ajouter.html')

@app.route('/etudiants/modifier')
def etudiants_modifier():
    return render_template('/etudiants/modifier.html')


if __name__ == '__main__':
    app.run()
