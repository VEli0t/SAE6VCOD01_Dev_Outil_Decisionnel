from website import create_app
from flask import Flask, render_template, redirect, url_for
from flask_login import current_user

app = create_app()

# Gestion erreur 404
@app.errorhandler(404)
def page_not_found(e):
    return render_template('error404.html', user=current_user)


@app.route('/')
def home():
    return redirect(url_for('login'))


@app.route('/login')
def login():
    return render_template('login.html')


if __name__ == '__main__':
    app.run(debug=True)

