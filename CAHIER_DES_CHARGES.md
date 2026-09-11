# Cahier des charges — Application ClairVoyanceMedium.com

## 1. Objectif

Créer une application mobile professionnelle, haut de gamme et évolutive pour **ClairVoyanceMedium.com**, compatible avec :

- Android smartphones
- Android tablettes
- iPhone
- iPad

URL principale du service : **https://www.clairvoyancemedium.com/**

L’application doit afficher le site dans une expérience de type application native, sans donner l’impression d’utiliser Chrome ou Safari, tout en ajoutant des fonctions natives : notifications, statistiques, tableau de bord, liens profonds, mises à jour, partage, chat et outils marketing.

Le code source doit rester sous le contrôle du propriétaire dans ce dépôt GitHub.

---

## 2. Contrainte financière absolue

La conception, le développement, les tests, les compilations, les notifications, les statistiques et l’administration doivent être réalisés avec des solutions **gratuites**.

Services autorisés en priorité :

- GitHub Free
- GitHub Actions dans les quotas gratuits ou sur runners standards gratuits pour dépôt public
- GitHub Pages
- GitHub Releases
- Firebase Spark
- Firebase Cloud Messaging
- Firebase Analytics
- Firebase Crashlytics
- Firebase Performance Monitoring
- Firebase Remote Config dans ses limites gratuites
- Firebase App Distribution
- Firebase In-App Messaging
- solutions open source gratuites
- infrastructure déjà existante de ClairVoyanceMedium.com
- tawk.to déjà présent sur le site

Interdits sans autorisation explicite :

- abonnement SaaS obligatoire
- Median payant
- WebInto payant
- AppMySite payant
- Firebase Blaze
- serveur payant obligatoire
- API facturée à l’usage
- carte bancaire obligatoire pour une brique de développement

### Exception acceptée

Les frais futurs de publication sur les boutiques officielles sont acceptés séparément :

- Google Play Console
- Apple Developer Program / App Store

---

## 3. Propriété et indépendance

- Le code appartient au propriétaire de ClairVoyanceMedium.com.
- Le dépôt GitHub constitue la source principale du projet.
- L’application ne doit pas dépendre d’un constructeur propriétaire.
- Le projet doit pouvoir être repris par un autre développeur ou une autre IA.
- Aucun secret, certificat, jeton privé ou clé d’administration ne doit être écrit en clair dans le dépôt.
- Les secrets de compilation doivent être conservés dans GitHub Secrets ou dans un mécanisme équivalent sécurisé et gratuit.

---

## 4. Plateformes

Compatibilité obligatoire :

- Android smartphone
- Android tablette
- iPhone
- iPad
- portrait et tailles d’écran variées
- zones sûres, encoches et barres système modernes

Une base de code commune doit être privilégiée lorsque cela améliore la maintenance sans dégrader la WebView, les paiements ou les notifications.

Le framework retenu doit être gratuit/open source et justifié selon :

- stabilité Android/iOS
- qualité WebView
- support Firebase
- notifications
- maintenance
- compilation automatisable via GitHub
- performances

---

## 5. Affichage principal

L’application doit charger :

**https://www.clairvoyancemedium.com/**

Expérience souhaitée :

- plein écran de type application
- aucun champ d’adresse navigateur
- écran de démarrage avec identité ClairVoyanceMedium.com
- navigation retour
- gestion du bouton Retour Android
- indicateur de chargement discret
- page hors connexion propre
- gestion des erreurs réseau
- partage natif
- téléchargement de fichiers
- ouverture correcte des liens externes
- reprise correcte après fermeture/réouverture
- conservation des sessions lorsque nécessaire

Design général : **premium noir/or, sobre, professionnel, lisible**.

---

## 6. Priorité critique : panier et sessions

Un prototype WebInto.app a présenté le bug suivant :

1. produit ajouté au panier ;
2. panier visible ;
3. saisie du prénom ;
4. saisie du nom ;
5. panier vidé automatiquement.

Le même parcours fonctionne normalement dans Chrome.

La nouvelle application doit donc garantir correctement :

- cookies nécessaires
- cookies first-party
- cookies tiers lorsque nécessaires et autorisés
- DOM Storage
- localStorage
- sessionStorage
- JavaScript
- IndexedDB lorsque nécessaire
- persistance de session
- navigation sans recréation involontaire de session
- redirections sans perte du panier

### Test obligatoire

Produit → Ajouter au panier → Panier → Prénom → Nom → coordonnées → paiement.

Le panier ne doit jamais se vider anormalement.

---

## 7. Paiements

Compatibilité prioritaire avec :

- Stripe
- PayPal

Tester au minimum :

- ouverture du paiement
- saisie des coordonnées
- authentification 3-D Secure
- redirections
- retour vers l’application
- paiement réussi
- paiement refusé
- annulation
- retour arrière
- fermeture/réouverture

La session et le panier doivent survivre correctement au parcours de paiement.

Lorsque la sécurité ou la compatibilité l’exige, une page de paiement peut être ouverte dans un navigateur système sécurisé puis revenir dans l’application.

---

## 8. tawk.to

Le site utilise déjà **tawk.to**.

Le chat doit fonctionner dans l’application :

- widget visible
- JavaScript compatible
- clavier mobile
- saisie des messages
- liens
- fichiers/pièces jointes lorsque disponibles

Prévoir également, si pertinent, un bouton natif **Chat** ouvrant directement la conversation tawk.to.

---

## 9. Liens et communication

Doivent fonctionner correctement :

- appel téléphonique
- SMS
- e-mail
- WhatsApp
- tawk.to
- liens web externes
- téléchargements
- partage natif

Les protocoles nécessitant une autre application doivent ouvrir l’application correspondante.

---

## 10. Notifications push

Fonction majeure du projet.

Utiliser en priorité **Firebase Cloud Messaging** dans Firebase Spark.

Compatibilité :

- Android
- tablette Android
- iPhone
- iPad

L’administrateur doit pouvoir envoyer une notification à tous les utilisateurs ayant accepté les notifications.

---

## 11. Éditeur de notifications

Prévoir une interface simple permettant de saisir :

- titre
- message
- image facultative
- vidéo/média facultatif
- lien ou page de destination
- cible
- date/heure

Actions :

- **Envoyer maintenant**
- **Programmer**
- **Enregistrer comme brouillon**

Exemple :

- Titre : `Promotion aujourd'hui`
- Message : texte libre
- Image : visuel promotionnel
- Destination : page précise de ClairVoyanceMedium.com

---

## 12. Notifications enrichies

Images :

- titre
- texte
- grande image lorsque la plateforme le permet
- deep link
- boutons d’action lorsque pertinent

Vidéos :

- pièce jointe vidéo lorsque réellement supportée
- sinon miniature/image dans la notification
- toucher la notification ouvre immédiatement la vidéo dans l’application ou un lecteur approprié

Ne pas stocker inutilement de grosses vidéos dans le dépôt GitHub.

---

## 13. Segmentation

Prévoir au minimum :

- tous les utilisateurs
- Android uniquement
- iOS uniquement

Puis lorsque les données le permettent :

- smartphone
- tablette
- nouveaux utilisateurs
- utilisateurs actifs
- utilisateurs inactifs depuis X jours
- langue
- version de l’application
- autres segments pertinents

---

## 14. Programmation des notifications

Prévoir :

- immédiat
- date
- heure
- brouillons
- duplication d’une ancienne campagne
- historique
- réutilisation d’une campagne

La programmation doit rester compatible avec l’objectif **0 € d’infrastructure obligatoire**.

---

## 15. Deep links

Une notification doit pouvoir ouvrir directement la page concernée et pas seulement l’accueil.

Prévoir :

- Android App Links
- iOS Universal Links lorsque le domaine le permet
- routage interne des URL

Exemple : notification d’une offre → toucher → ouverture directe de la page de cette offre.

---

## 16. Centre de notifications interne

Si réalisable sans coût :

- notifications récentes
- lues/non lues
- date
- image
- accès direct à l’offre
- badge de notifications non lues

---

## 17. Tableau de bord administrateur

Créer une interface privée, adaptée au téléphone et à l’ordinateur.

Sections souhaitées :

- Tableau de bord
- Notifications
- Campagnes
- Statistiques
- Appareils / utilisateurs agrégés
- Versions
- Paramètres
- Erreurs / crashs
- Mises à jour

L’objectif est que l’administrateur n’ait pas à manipuler Firebase ou le code pour les opérations quotidiennes.

---

## 18. Statistiques

Afficher autant que possible :

- installations
- nouvelles installations
- utilisateurs actifs
- sessions
- ouvertures de l’application
- Android / iOS
- smartphone / tablette
- versions de l’application
- langues
- pays lorsque disponible de façon légitime
- pages consultées lorsque mesurables
- durée de session lorsque pertinente
- crashs
- erreurs
- performances

Ne jamais présenter une estimation comme une mesure exacte.

---

## 19. Désinstallations

Afficher les désinstallations uniquement lorsqu’une source fiable Apple/Google ou un mécanisme technique autorisé fournit cette donnée.

Indiquer clairement si la donnée est :

- exacte
- différée
- dépendante du consentement
- indisponible sur une plateforme

Ne jamais fabriquer un compteur de désinstallations.

---

## 20. Statistiques de campagnes

Pour chaque notification/campagne, afficher lorsque disponible :

- cible
- envoyées
- délivrées
- ouvertes
- clics
- taux d’ouverture
- taux de clic
- destination
- date/heure
- plateforme
- conversions attribuables lorsque mesurables

L’architecture doit permettre ultérieurement de comparer :

- meilleurs titres
- meilleurs messages
- meilleures images
- meilleurs jours
- meilleurs horaires
- campagnes les plus ouvertes
- campagnes générant le plus de clics
- campagnes générant le plus de conversions

---

## 21. Firebase

Rester sur **Firebase Spark** sauf autorisation explicite contraire.

Utiliser lorsque pertinent :

- Cloud Messaging
- Analytics
- Crashlytics
- Performance Monitoring
- Remote Config
- App Distribution
- In-App Messaging
- App Check

Éviter toute architecture exigeant obligatoirement Firebase Blaze ou Cloud Functions payantes.

---

## 22. Sécurité

Obligatoire :

- aucune clé privée dans l’application
- aucune clé FCM serveur dans du JavaScript public
- secrets protégés
- HTTPS
- authentification de l’administration
- contrôle des URL
- validation des entrées
- permissions minimales
- séparation des droits administrateur/utilisateur
- aucune possibilité pour un utilisateur standard d’envoyer une notification

Les opérations privilégiées de notification doivent utiliser un mécanisme sécurisé, sans exposer les secrets dans GitHub Pages ou dans l’application.

---

## 23. Mises à jour

Deux circuits :

### Boutiques officielles

- Google Play
- App Store

### Distribution directe lorsque possible

Pour Android :

- APK signé
- numéro de version
- notification d’une nouvelle version
- bouton Mettre à jour
- téléchargement de la nouvelle version

---

## 24. Distribution Android hors Play Store

Le propriétaire veut pouvoir transmettre directement un lien d’installation Android, sans passage obligatoire par Google Play.

Prévoir :

- APK signé
- GitHub Release ou hébergement gratuit adapté
- checksum lorsque pertinent
- page de téléchargement
- instructions simples
- mécanisme de mise à jour

---

## 25. Distribution Apple

Prévoir l’App Store comme canal principal lorsque le compte Apple Developer sera disponible.

Étudier également les méthodes de distribution Web autorisées par Apple dans l’Union européenne si le propriétaire remplit réellement les conditions d’éligibilité.

Ne jamais promettre qu’un simple fichier IPA pourra être librement installé sur n’importe quel iPhone.

---

## 26. Lien unique de téléchargement

Objectif : **un seul lien public**.

Exemple souhaité :

`https://www.clairvoyancemedium.com/app`

ou une URL équivalente contrôlée par le propriétaire.

Comportement :

- Android → APK direct et/ou Google Play
- tablette Android → APK direct et/ou Google Play
- iPhone/iPad → App Store ou méthode Apple autorisée disponible
- ordinateur → page présentant les possibilités

---

## 27. QR code unique

Générer un QR code correspondant au lien universel.

Un seul QR code doit pouvoir être utilisé sur :

- cartes
- affiches
- réseaux sociaux
- site
- documents
- publicités

---

## 28. Mesure du lien de téléchargement

Mesurer lorsque possible :

- clics
- date
- heure
- Android/iOS
- campagne/source
- destination

Ne jamais confondre **clic de téléchargement** et **installation réelle**.

---

## 29. Configuration à distance

Utiliser Remote Config ou une alternative gratuite lorsque pertinent afin de modifier certains comportements sans reconstruire systématiquement l’application.

Exemples :

- message
- promotion
- URL
- fonction activée/désactivée
- mode maintenance
- paramètres marketing

---

## 30. Mode maintenance

Prévoir un mode maintenance activable à distance lorsque cela est réalisable gratuitement.

---

## 31. Erreurs, crashs et performances

Utiliser Crashlytics et Performance Monitoring ou alternatives gratuites.

Suivre :

- version concernée
- plateforme
- utilisateurs touchés
- nombre d’erreurs
- démarrage
- temps de chargement
- erreurs réseau
- stabilité WebView
- lenteurs importantes

L’application ne doit pas devenir sensiblement plus lente que le site dans un navigateur moderne.

---

## 32. Confidentialité

Respecter :

- RGPD
- consentements nécessaires
- règles Apple
- règles Google
- permissions minimales

Une permission ne doit être demandée que lorsqu’elle sert une fonction réelle.

---

## 33. Fonctions natives à prévoir

Lorsque pertinentes :

- bouton Chat
- bouton Appeler
- bouton SMS
- partage natif
- favoris
- historique récent
- centre de notifications
- push
- deep links
- téléchargements
- ouverture de fichiers
- badge de notifications
- actions rapides
- page hors connexion
- configuration distante

Ces fonctions contribuent également à éviter qu’iOS considère l’application comme un simple site reconditionné.

---

## 34. Compilation et releases

Automatiser autant que possible avec GitHub Actions.

Android :

- APK de test
- APK signé pour distribution directe
- AAB pour Google Play

Apple :

- build iOS compatible avec la signature Apple lorsque compte et certificats seront disponibles

Versionnement :

- `v1.0.0`
- `v1.0.1`
- `v1.1.0`

Chaque release doit être identifiable et documentée.

---

## 35. Documentation du dépôt

Le dépôt doit progressivement contenir :

- README
- architecture
- procédure d’installation
- documentation Firebase
- documentation Android
- documentation iOS
- workflows GitHub Actions
- procédure de release
- procédure de rollback
- procédure de gestion des secrets
- changelog

---

## 36. Tests obligatoires

Tester au minimum sur :

- Android smartphone
- Android tablette
- iPhone
- iPad

Parcours fonctionnels :

- démarrage
- navigation
- retour
- tawk.to
- appel
- SMS
- e-mail
- WhatsApp
- ajout panier
- saisie prénom
- saisie nom
- panier conservé
- Stripe
- PayPal
- 3-D Secure
- retour paiement
- téléchargements
- notifications
- notification avec image
- deep link
- vidéo
- partage
- fermeture/réouverture
- perte/récupération réseau
- mise à jour

---

## 37. Phases de développement

1. Architecture GitHub + projet mobile
2. WebView professionnelle + navigation
3. Panier/sessions/cookies
4. Stripe + PayPal
5. tawk.to + communications
6. Firebase
7. Notifications push
8. Images/médias/deep links
9. Analytics/Crashlytics/Performance
10. Tableau de bord administrateur
11. Distribution Android directe + lien unique
12. Optimisation tablette/iPad
13. Préparation Google Play
14. Préparation App Store

---

## 38. Critères de validation

Le projet n’est pas terminé simplement parce qu’un APK ou un build iOS existe.

Validation lorsque :

1. le site fonctionne correctement ;
2. le panier ne disparaît pas ;
3. les formulaires fonctionnent ;
4. Stripe fonctionne ;
5. PayPal fonctionne ;
6. tawk.to fonctionne ;
7. Android smartphone fonctionne ;
8. tablette Android fonctionne ;
9. iPhone fonctionne ;
10. iPad fonctionne ;
11. notifications fonctionnent ;
12. images fonctionnent ;
13. deep links fonctionnent ;
14. statistiques fonctionnent ;
15. administration fonctionne ;
16. téléchargement direct Android fonctionne ;
17. aucune infrastructure payante obligatoire n’a été introduite.

---

## 39. Règle finale pour tout développeur ou IA

Ne jamais remplacer une fonctionnalité demandée par une solution payante simplement parce qu’elle est plus facile.

Ordre de recherche :

1. fonctionnalité native Android/iOS ;
2. solution open source ;
3. GitHub ;
4. Firebase Spark ;
5. autre solution gratuite sans carte bancaire.

Toute proposition entraînant un abonnement, une facturation à l’usage ou une carte bancaire obligatoire doit être signalée avant intégration et nécessite l’accord explicite du propriétaire.

Les seuls frais acceptés par défaut sont, ultérieurement, les frais officiels de publication Google Play et Apple App Store.

## Objectif final

Construire une application **ClairVoyanceMedium.com** indépendante, moderne, haut de gamme, mesurable, pilotable, évolutive et aussi ouverte que les plateformes Android/iOS le permettent, avec un coût de conception et d’infrastructure initiale de **0 €**.