# Compte-Rendu de Réunion & Cadrage Fonctionnel
**Projet :** Plateforme Intelligente de Veille & Studio de Design Génératif en Lunetterie  
**Date :** 29 Septembre 2026  
**Statut :** Document de travail / Cahier des charges préliminaire  

---

## 1. Synthèse & Vision Stratégique

Le projet a pour vocation de concevoir une double solution logicielle dédiée aux créateurs et industriels de la lunetterie (notamment pour valoriser l'ADN de la marque, e.g. *Noe Noah*) :
1. **Un Radar de Veille et d'Analyse des Tendances :** Capable d'ingérer, classifier et synthétiser les évolutions stylistiques du marché international (hors Asie).
2. **Un Studio de Coloration et de Design Assisté par IA :** Capable de transformer des dessins techniques (croquis 2D en noir et blanc) en déclinaisons réalistes de montures, en appliquant des règles précises de lamination d'acétates et de matières issues de catalogues fournisseurs réels.

---

## 2. Module 1 : Radar de Tendances & Veille Concurrentielle

### 2.1 Périmètre Géographique & Cibles
* **Marchés prioritaires :** Europe, États-Unis, Maghreb, Tunisie.
* **Marchés exclus :** Asie (spécificités morphologiques et stylistiques hors cible actuelle).
* **Événements de référence :** Surveillance active des salons internationaux (ex. SILMO Paris) et des flux éditoriaux du secteur.

### 2.2 Données Surveillées & Détection de Tendances
* **Composants & Morphologie de monture :**
  * Formes de faces (rondes, pantos, géométriques, œil-de-chat, etc.).
  * Types de branches, manchons, tenons et technologies de charnières.
  * Systèmes hybrides : montures optiques avec clip-on solaire magnétique, verres photochromiques.
* **Matières & Traitements :**
  * Acétates (translucidités, écailles, marbrures), métaux (titane, acier inoxydable), bio-acétates.
  * Teintes et dégradés des verres solaires et lentilles.
* **Couleurs & Laminations populaires :**
  * Détection des associations récurrentes de plaques d'acétate (ex. bi-couches, tri-couches : rose + rouge + crème).
  * Identification statistique des « best-sellers » et des designs les plus partagés/visibles.

### 2.3 Règles Métier, Filtrage de Données & DataViz
* **Filtrage Anti-Bruit :** Algorithme de détection d'objets pour isoler strictement les montures lunetières parmi les flux d'images web/réseaux sociaux.
* **Hiérarchie Produits :** Seules les **marques créateurs/fabricants** sont analysées (ex. *Woodys, Etnia Barcelona, Morel, Ana Hickmann, Carolina Herrera, WOOW Eyewear, Made in Italy*), en excluant les distributeurs/opticiens généralistes afin d'éviter la redondance d'inventaire.
* **Standardisation Colorimétrique :** Remplacement des désignations génériques (« noir », « bleu ») par une nomenclature à trois niveaux :
  * Palier 1 : Famille générale de couleur.
  * Palier 2 : Nuance précise / Code hexadécimal / Référence Pantone.
  * Palier 3 : Identifiant matière fournisseur (ex. code acétate fabricant).
* **Fidélité Chromatique de la DataViz (Courbes de Tendances) :** Dans tous les graphiques de suivi temporel et de popularité, la couleur de la courbe/tracé doit obligatoirement correspondre à la teinte réelle observée (ex. la courbe d'évolution d'une nuance « noir » s'affiche impérativement en noir/gris profond, et non avec une couleur arbitraire par défaut de la bibliothèque graphique comme le bleu). Cette fidélité chromatique s'appuie directement sur les codes hexadécimaux définis au Palier 2.

---

## 3. Module 2 : Gestion de l'ADN de Marque (Brand DNA)

* **Bibliothèque de Référence :** Base de données propriétaire regroupant les modèles signatures de la marque.
* **Apprentissage du Style :** Entraînement du modèle pour reconnaître :
  * Les proportions et signatures stylistiques récurrentes.
  * Les codes d'assemblage et de finitions propres à la marque.
  * Les règles de compatibilité entre formes et matières.
* **Objectif :** Permettre à l'IA de proposer des évolutions de modèles qui s'inscrivent naturellement dans la continuité de la collection existante.

---

## 4. Module 3 : Studio de Design IA & Coloration (Sketch-to-Lamination)

### 4.1 Entrées du Système (Inputs)
1. **Croquis technique 2D :** Dessin technique vectoriel ou bitmap en noir et blanc (face et/ou branches).
2. **Catalogues Fournisseurs Réels :** Extraction depuis des fiches techniques/PDF des nuanciers d'acétates disponibles chez les fabricants partenaires (évite les rendus irréalistes ou non usinables).

### 4.2 Fonctionnalités de l'Éditeur Graphique
* **Intervention Humaine Guidée :**
  * Le designer définit sur le sketch des zones ou tracés pour délimiter les découpes et laminations (collages d'acétates).
  * Choix guidé des teintes de face, branches, charnières et verres.
* **Rendu Réaliste :**
  * L'IA applique les textures de matière, l'épaisseur des laminations, la brillance et les reflets photoréalistes.
* **Aide Générative Intelligente :**
  * L'outil suggère des combinaisons de couleurs harmonieuses et tendances issues du Radar de veille.

### 4.3 Faisabilité Technique & Contraintes d'Industrialisation
* Intégration de garde-fous techniques afin de réduire les erreurs de prototypage :
  * Respect des épaisseurs minimales pour le collage de plaques d'acétate.
  * Cohérence mécanique des tenons pour l'ancrage des charnières.
  * Tolérances d'usinage sur machine CNC.

---

## 5. Feuille de Route Prévisionnelle (Roadmap)

| Phase | Objectifs Clés | Livrables |
| :--- | :--- | :--- |
| **Phase 1 : Data & Radar** | Scraping ciblé, classification d'images, taxonomie des couleurs et marques. | Dashboard de veille sur les tendances couleurs (avec courbes dynamiques fidèles aux teintes réelles), formes et matières (focus salons/marques clés). |
| **Phase 2 : Ingestion & Bibliothèque ADN** | Structuration des catalogues fournisseurs (PDF acétates) et constitution du catalogue de référence. | Base de données de matières exploitables + référentiel de marque. |
| **Phase 3 : Studio Interactif (Sketch-to-Color)** | Interface utilisateur d'édition de sketch N&B avec délimitation manuelle des zones de lamination et rendu IA. | MVP du configurateur de montures basé sur les stocks réels de matières. |
| **Phase 4 : Génération Avancée & Automatisation** | Suggestions autonomes de palettes et de laminations basées sur les corrélations du marché et l'ADN. | Assistant IA autonome générant des déclinaisons de collection prêtes pour l'échantillonnage. |

---

## 6. Prochaines Actions Immédiates

- [ ] **Data :** Valider la liste définitive des 15 marques de référence à surveiller prioritairement.
- [ ] **Technique :** Définir la structure du schéma de données pour les couleurs (Famille, Code, Référence plaque fournisseur).
- [ ] **DataViz :** Établir la charte d'affichage dynamique pour que chaque courbe de tendance hérite du code chromatique hexadécimal de la nuance représentée.
- [ ] **Design :** Rassembler un jeu d'essai de 20 croquis 2D noir et blanc pour tester le pipeline de rendu IA.
- [ ] **Fournisseurs :** Récupérer 2 à 3 catalogues PDF de fabricants de plaques d'acétate pour calibrer le module d'extraction.