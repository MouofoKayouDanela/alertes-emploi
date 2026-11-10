# Alertes emploi – développement, région de Québec

Ce petit programme vérifie toutes les 15 minutes les nouvelles offres d'emploi en développement
et t'envoie une notification sur ton téléphone dès qu'une offre correspond à ton profil.
Il tourne gratuitement sur GitHub : ton ordinateur peut rester éteint.

## Ce qu'il surveille

- **Sources** : le Guichet-Emplois du gouvernement du Canada (sans configuration), et Adzuna
  si tu ajoutes une clé (recommandé, voir l'étape 4).
- **Postes** : développeuse, programmeuse, full-stack, back-end, front-end, web, logiciel, .NET,
  Java, etc. Toutes les années d'expérience sont acceptées.
- **Lieux** :
  - 📍 **Région de Québec** (environ 1 h de route : Québec, Lévis, Saint-Augustin, Beauce, Portneuf,
    Côte-de-Beaupré…) ; notification prioritaire.
  - 🏠 **Télétravail ou hybride**, partout ; notification prioritaire.
  - 🚗 **Ailleurs au Québec**, seulement si c'est un vrai poste de développement ou s'il mentionne
    une technologie de ton profil ; notification normale.

Pour modifier les mots-clés ou les villes, change les listes en haut de `job_alerts.py`.

---

## Installation (environ 15 minutes)

### 1. Installer l'application ntfy sur ton téléphone

1. Installe **ntfy** depuis le Play Store (Android) ou l'App Store (iPhone).
2. Ouvre-la, appuie sur **+** (s'abonner à un sujet) et tape exactement :

   ```
   danela-emplois-d77ffd9556aa
   ```

3. Valide. C'est tout : aucun compte n'est nécessaire.

> Ce nom de sujet sert de mot de passe : toute personne qui le connaît peut voir tes alertes.
> Ne le partage pas. Il ne contient rien de personnel et tu peux en changer à tout moment.

### 2. Créer le dépôt sur GitHub

1. Va sur <https://github.com/new>.
2. Nom du dépôt : `alertes-emploi`.
3. Choisis **Public**. Les vérifications sont alors gratuites et illimitées. Le dépôt ne contient
   que le programme et des numéros d'offres. Ton sujet ntfy et tes clés restent secrets (étape 3).
4. Clique sur **Create repository**, puis sur **uploading an existing file**.
5. Glisse **tout le contenu** du dossier `alertes-emploi`, y compris le dossier `.github`.
   S'il n'apparaît pas dans l'Explorateur Windows, active **Affichage → Éléments masqués**.
6. Clique sur **Commit changes**.

### 3. Ajouter ton sujet ntfy comme secret

1. Dans ton dépôt : **Settings → Secrets and variables → Actions → New repository secret**.
2. Name : `NTFY_TOPIC`, Secret : `danela-emplois-d77ffd9556aa`, puis **Add secret**.

### 4. (Recommandé) Ajouter Adzuna pour beaucoup plus d'offres

Le Guichet-Emplois publie peu d'offres en informatique à Québec. Adzuna regroupe les offres
de nombreux sites d'emploi.

1. Crée un compte gratuit sur <https://developer.adzuna.com/signup>.
2. Tu obtiendras un **Application ID** et une **Application Key**.
3. Ajoute-les comme deux secrets (même méthode qu'à l'étape 3) :
   `ADZUNA_APP_ID` et `ADZUNA_APP_KEY`.

### 5. Lancer le premier essai

1. Onglet **Actions** de ton dépôt. Si GitHub le demande, clique sur
   **I understand my workflows, go ahead and enable them**.
2. Choisis **Alertes emploi** dans la liste de gauche, puis **Run workflow**.
3. Après environ 30 secondes, tu dois recevoir sur ton téléphone :
   **« Alertes emploi activées ✅ »**.

Au premier lancement, les offres déjà en ligne sont mémorisées sans t'être envoyées, pour ne pas
inonder ton téléphone. Ensuite, chaque nouvelle offre qui correspond déclenche une notification.
Appuie dessus pour ouvrir l'offre.

---

## Bon à savoir

- **Délai** : GitHub lance la vérification toutes les 15 minutes environ, avec parfois quelques
  minutes de retard aux heures chargées.
- **Pause** : onglet **Actions → Alertes emploi → ⋯ → Disable workflow**. Pour reprendre,
  utilise **Enable workflow**.
- **Si ça ne marche plus** : onglet **Actions**, ouvre la dernière exécution marquée d'une croix
  rouge pour voir le message d'erreur.
- **Essai sur ton ordinateur** : `python job_alerts.py --dry-run` affiche les offres trouvées
  sans rien envoyer.
