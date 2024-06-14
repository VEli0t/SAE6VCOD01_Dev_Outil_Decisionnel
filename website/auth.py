from flask import Flask, Blueprint, render_template, request, flash, redirect, url_for, send_from_directory, current_app
from .models import User
from werkzeug.security import generate_password_hash, check_password_hash
from . import db
from flask_login import login_user, login_required, logout_user, current_user
import os
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import folium
from folium.plugins import HeatMap
import matplotlib.patheffects as path_effects


auth = Blueprint('auth', __name__)

matplotlib.use('Agg') # Utilise le backend 'Agg' pour éviter les problèmes d'interface graphique

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()
        if user:
            if check_password_hash(user.password, password):
                flash('Connexion réussie !', category='success')
                login_user(user, remember=True)
                return redirect(url_for('auth.home'))
            else:
                flash('Mot de passe incorrect, veuillez réessayer.', category='error')
        else:
            flash('Email n\'existe pas.', category='error')

    return render_template("login.html", user=current_user)


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))


@auth.route('/sign-up', methods=['GET', 'POST'])
def sign_up():
    if request.method == 'GET' and current_user:
        logout_user()
    if request.method == 'POST':
        email = request.form.get('email')
        first_name = request.form.get('firstName')
        password1 = request.form.get('password1')
        password2 = request.form.get('password2')

        user = User.query.filter_by(email=email).first()
        if user:
            flash('Email existe déjà.', category='error')
        elif len(email) < 4:
            flash('L\'email doit comporter plus de 3 caractères.', category='error')
        elif len(first_name) < 2:
            flash('Le prénom doit comporter plus d\'un caractère.', category='error')
        elif password1 != password2:
            flash('Les mots de passe ne correspondent pas.', category='error')
        elif len(password1) < 7:
            flash('Le mot de passe doit comporter au moins 7 caractères.', category='error')
        else:
            new_user = User(email=email, first_name=first_name, password=generate_password_hash(
                password1))
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user, remember=True)
            flash('Compte créé !', category='success')
            return redirect(url_for('auth.home'))

    return render_template("sign_up.html", user=current_user)


@auth.route('/home')
@login_required
def home():
    return render_template("home.html", user=current_user)

def get_data_descriptions():
    data_folder = 'data'
    descriptions = {}

    for filename in os.listdir(data_folder):
        if filename.endswith('.csv'):
            file_path = os.path.join(data_folder, filename)
            try:
                df = pd.read_csv(file_path, nrows=1000, encoding='utf-8')
            except UnicodeDecodeError:
                df = pd.read_csv(file_path, nrows=1000, encoding='latin1')

            # Gérer les valeurs nulles
            df = df.fillna(df.mean())  # Remplir les valeurs nulles par la moyenne de la colonne

            descriptions[filename] = df.describe(include='all').to_dict()

    return descriptions


@auth.route('/presentation-data')
@login_required
def presentation_data():
    descriptions = get_data_descriptions()
    selected_dataset = request.args.get('dataset')
    return render_template("presentation-data.html", user=current_user,
                           descriptions=descriptions, selected_dataset=selected_dataset)


# Charger les données globalement
file_path = 'data/operations.csv'
operations_df = pd.read_csv(file_path, encoding='utf-8')
operations_df = operations_df.dropna(subset=['latitude', 'longitude', 'date_heure_fin_operation'])

# Extraire toutes les années disponibles et les trier
all_years = sorted(operations_df['date_heure_fin_operation'].str[:4].unique())

# Extraire toutes les catégories disponibles
all_categories = sorted(operations_df['categorie_evenement'].unique())


@auth.route('/operation', methods=['GET', 'POST'])
def operation():
    selected_year = request.form.get('year')
    selected_categories = request.form.getlist('categories')

    # Si filtre null, alors on l'initialise
    if selected_year is None:
        selected_year = '2024'

    # Filtrer les données par an
    if selected_year:
        filtered_df = operations_df[operations_df['date_heure_fin_operation'].str[:4] == selected_year]
    else:
        filtered_df = operations_df

    # Filtrer les données par catégories si des catégories sont sélectionnées
    if selected_categories:
        filtered_df = filtered_df[filtered_df['categorie_evenement'].isin(selected_categories)]

    # Créer une carte centrée sur un point central (ex: le centre du planisphère)
    m = folium.Map(location=[0, 0], zoom_start=2)

    # Préparer les données pour la heatmap
    heat_data = [[row['latitude'], row['longitude']] for index, row in filtered_df.iterrows()]

    # Définir un gradient personnalisé pour la heatmap
    gradient = {
        0.0: 'blue',
        0.2: 'lime',
        0.4: 'yellow',
        0.6: 'orange',
        0.8: 'red',
        1.0: 'maroon'
    }

    # Ajouter la heatmap à la carte
    HeatMap(heat_data, gradient=gradient, radius=25, blur=15, max_zoom=1).add_to(m)

    # Sauvegarder la carte dans un fichier HTML dans le répertoire static
    map_path = os.path.join('website', 'static', 'map.html')
    os.makedirs(os.path.dirname(map_path), exist_ok=True)
    m.save(map_path)

    # Passage au template
    return render_template('operation.html', user=current_user, operations_df=operations_df,
                           all_years=all_years, all_categories=all_categories, selected_year=selected_year,
                           selected_categories=selected_categories)


# Charger les données pour analyse
stats_file_path = 'data/operations_stats.csv'
stats_df = pd.read_csv(stats_file_path, encoding='utf-8')

# Dictionnaire pour mapper les numéros de mois aux noms de mois
mois_noms = {
    1: "Janvier", 2: "Février", 3: "Mars", 4: "Avril",
    5: "Mai", 6: "Juin", 7: "Juillet", 8: "Août",
    9: "Septembre", 10: "Octobre", 11: "Novembre", 12: "Décembre"
}


@auth.route('/analyse', methods=['GET', 'POST'])
def analyse():
    selected_year = request.form.get('year')

    # Si filtre null, alors on l'initialise
    if selected_year is None:
        selected_year = '2014'

    # Filtrer les données par an
    if selected_year == 'all':
        filtered_df = stats_df
    else:
        filtered_df = stats_df[stats_df['annee'] == int(selected_year)]

    ## Calcul des KPI
    kpi_operations = filtered_df['operation_id'].count()
    kpi_deces = filtered_df['nombre_personnes_tous_deces_ou_disparues'].sum()
    kpi_assistance = filtered_df['nombre_personnes_impliquees'].sum()
    kpi_blesses = filtered_df['nombre_personnes_blessees'].sum()

    ## 1er graphique

    # Grouper les données par mois et compter le nombre d'opérations par mois
    monthly_operations = filtered_df.groupby('mois')['operation_id'].count().reset_index()

    # Trier les données par mois si nécessaire
    monthly_operations = monthly_operations.sort_values(by='mois')

    # Remplacer les numéros de mois par les noms de mois
    monthly_operations['mois'] = monthly_operations['mois'].map(mois_noms)

    # Tracer les données
    plt.figure(figsize=(10, 6))
    plt.plot(monthly_operations['mois'], monthly_operations['operation_id'], marker='o')
    plt.title('Nombre d\'opérations par mois')
    plt.xlabel('Mois')
    plt.ylabel('Nombre d\'opérations')
    plt.grid(True)
    plt.xticks(rotation=45)
    plt.tight_layout()

    # Sauvegarder le graphique dans un fichier
    plot_path = os.path.join('website', 'static', 'curved_plot.png')
    os.makedirs(os.path.dirname(plot_path), exist_ok=True)
    plt.savefig(plot_path)
    plt.close()

    ## 2e graphique à double échelle

    # Grouper les données par mois pour les différentes métriques
    monthly_metrics = filtered_df.groupby('mois').agg({
        'nombre_personnes_blessees': 'sum',
        'nombre_personnes_tous_deces_ou_disparues': 'sum',
        'nombre_personnes_impliquees': 'sum'
    }).reset_index()

    # Trier les données par mois si nécessaire
    monthly_metrics = monthly_metrics.sort_values(by='mois')

    # Remplacer les numéros de mois par les noms de mois
    monthly_metrics['mois'] = monthly_metrics['mois'].map(mois_noms)

    # Tracer les données avec une double échelle
    fig, ax1 = plt.subplots(figsize=(10, 6))

    ax2 = ax1.twinx()
    ax1.plot(monthly_metrics['mois'], monthly_metrics['nombre_personnes_blessees'], 'r-', label='Blessées')
    ax1.plot(monthly_metrics['mois'], monthly_metrics['nombre_personnes_tous_deces_ou_disparues'], 'black',
             label='Décédées ou disparus')
    ax2.plot(monthly_metrics['mois'], monthly_metrics['nombre_personnes_impliquees'], 'g-', label='Impliquées')

    ax1.set_xlabel('Mois')
    ax1.set_ylabel('Nombre de personnes blessées ou décédées & disparus')

    ax2.set_ylabel('Nombre de personnes impliquées', color='g')
    ax1.grid(True)
    ax1.set_xticklabels(monthly_metrics['mois'], rotation=45)

    # Ajouter le titre avec ajustement de la mise en page
    plt.title('Statistique sur les sauvetages')
    fig.tight_layout(rect=[0, 0, 1, 0.95])

    # Ajouter des légendes
    lines_labels = [ax.get_legend_handles_labels() for ax in [ax1, ax2]]
    lines, labels = [sum(lol, []) for lol in zip(*lines_labels)]
    ax1.legend(lines, labels, loc=1)

    # Sauvegarder le graphique dans un fichier
    plot_path2 = os.path.join('website', 'static', 'double_scale_plot.png')
    plt.savefig(plot_path2)
    plt.close()

    # Passage au template
    return render_template('analyse.html', user=current_user, stats_df=stats_df,
                           all_years=all_years, all_categories=all_categories, selected_year=selected_year,
                           plot_path='static/curved_plot.png', plot_path2='static/double_scale_plot.png',
                           kpi_operations=kpi_operations, kpi_deces=kpi_deces, kpi_assistance=kpi_assistance,
                           kpi_blesses=kpi_blesses)


@auth.route('/category', methods=['GET', 'POST'])
@login_required
def category():
    selected_year = request.form.get('year')

    # Si filtre null, alors on l'initialise
    if selected_year is None:
        selected_year = '2014'

    # Filtrer les données par an
    if selected_year == 'all':
        filtered_operation_categorie_df = operations_df
    else:
        filtered_operation_categorie_df = operations_df[operations_df['date_heure_fin_operation'].str[:4] == selected_year]

    ## 1er graphique

    # Grouper les données par catégorie d’événement et compter le nombre d'opérations par catégorie
    category_operations = filtered_operation_categorie_df['categorie_evenement'].value_counts().reset_index()
    category_operations.columns = ['categorie_evenement', 'nombre_operations']

    # Tracer les données
    plt.figure(figsize=(10, 6))
    plt.bar(category_operations['categorie_evenement'], category_operations['nombre_operations'])
    plt.title('Nombre d\'opérations par catégorie d\'événement')
    plt.xlabel('Catégorie d\'événement')
    plt.ylabel('Nombre d\'opérations')
    plt.xticks(rotation=45)
    plt.tight_layout()

    # Sauvegarder le graphique dans un fichier
    plot_path2 = os.path.join('website', 'static', 'barplot.png')
    plt.savefig(plot_path2)
    plt.close()

    # 2e graphique - Pie chart sur le type d'opération

    # Grouper les données par type d’opération et compter le nombre d'opérations par type
    type_operations = filtered_operation_categorie_df['type_operation'].value_counts().reset_index()
    type_operations.columns = ['type_operation', 'nombre_operations']

    # Tracer les données
    plt.figure(figsize=(10, 6))
    patches, texts, autotexts = plt.pie(
        type_operations['nombre_operations'],
        labels=type_operations['type_operation'],
        autopct='%1.1f%%',
        startangle=140,
        textprops={'fontsize': 14, 'weight': 'bold'}
    )
    plt.title('Répartition des types d\'opérations', fontsize=16, weight='bold')

    # Ajouter une ombre au texte pour plus de lisibilité
    for text in texts + autotexts:
        text.set_path_effects([path_effects.Stroke(linewidth=3, foreground='white'), path_effects.Normal()])

    plt.tight_layout()

    # Sauvegarder le graphique dans un fichier
    plot_path3 = os.path.join('website', 'static', 'piechart.png')
    plt.savefig(plot_path3)
    plt.close()

    # Passer operations_df, all_years, all_categories, selected_year et selected_categories au template
    return render_template('category.html', user=current_user, operations_df=operations_df,
                           all_years=all_years, all_categories=all_categories, selected_year=selected_year,
                           plot_path='static/barplot.png', plot_path2='static/piechart.png')

