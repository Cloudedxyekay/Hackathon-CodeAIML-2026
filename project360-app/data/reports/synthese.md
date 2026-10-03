# Synthèse du projet NOVA

État documentaire au 2026-09-29.

Cible approuvée : 2026-10-22. Conditionnelle : oui.

Les engagements restent documentés ; leur réalisation n’est pas déduite. Les dates planifiées ne sont pas des réalisations.

## Décisions importantes

### Charte Projet NOVA v1

Statut : approved. Responsable : Non précisé (aucun rôle attribué).

Date documentée / début : 2026-07-07. Échéance : Non précisée.

CHARTE DE PROJET NOVA - VERSION 1 Date : 7 juillet 2026 Chargée de projet : Élodie Caron Fournisseur : Boréal Numérique Budget initial : 180 000 $ CAD Date cible de mise en production : 15 octobre 2026 Objectif Remplacer le suivi dispersé par courriel et fichiers locaux par un portail centralisé de demandes opérationnelles. Portée phase 1 - Authentification SSO - Création et suivi de demandes - Ajout de pièces jointes - Workflow de traitement - Tableau de suivi - Rapports standards Cette charte constitue le point de départ du projet et n'est pas mise à jour automatiquement après chaque décision de comité.

Source : 04_Documents_projet/Charte_Projet_NOVA_v1.txt — Document (doc-029).

> CHARTE DE PROJET NOVA - VERSION 1
> Date : 7 juillet 2026
> 
> Chargée de projet : Élodie Caron
> Fournisseur : Boréal Numérique
> Budget initial : 180 000 $ CAD
> Date cible de mise en production : 15 octobre 2026
> 
> Objectif
> Remplacer le suivi dispersé par courriel et fichiers locaux par un portail centralisé de demandes opérationnelles.
> 
> Portée phase 1
> - Authentification SSO
> - Création et suivi de demandes
> - Ajout de pièces jointes
> - Workflow de traitement
> - Tableau de suivi
> - Rapports standards
> 
> Cette charte constitue le point de départ du projet et n'est pas mise à jour automatiquement après chaque décision de comité.

### M01 CR Demarrage 07juillet

Statut : approved. Responsable : Non précisé (aucun rôle attribué).

Date documentée / début : 2026-07-07. Échéance : Non précisée.

PROJET NOVA - COMPTE RENDU DE DÉMARRAGE Date : 7 juillet 2026 Participants : Élodie Caron, Nicolas Perron, Marc Gervais, Sophie Lambert, Camille Beaulieu, représentant Boréal Objectif Lancer officiellement le projet NOVA et confirmer la portée de la phase 1. Décisions - Élodie Caron agit comme chargée de projet. - Budget initial maximal : 180 000 $ CAD. - Cible de mise en production : 15 octobre 2026. - La phase 1 comprend SSO, création/suivi de demandes, pièces jointes, workflow, tableau de suivi et rapports standards. Actions - Boréal : fournir le premier schéma d'architecture. - Marc : confirmer les modalités du connecteur interne. - Sophie : préparer les exigences de sécurité. Note L'expérience mobile avancée n'a pas été discutée comme livrable distinct pendant cette rencontre.

Source : 02_Reunions/M01_CR_Demarrage_07juillet.txt — Document (doc-013).

> PROJET NOVA - COMPTE RENDU DE DÉMARRAGE
> Date : 7 juillet 2026
> Participants : Élodie Caron, Nicolas Perron, Marc Gervais, Sophie Lambert, Camille Beaulieu, représentant Boréal
> 
> Objectif
> Lancer officiellement le projet NOVA et confirmer la portée de la phase 1.
> 
> Décisions
> - Élodie Caron agit comme chargée de projet.
> - Budget initial maximal : 180 000 $ CAD.
> - Cible de mise en production : 15 octobre 2026.
> - La phase 1 comprend SSO, création/suivi de demandes, pièces jointes, workflow, tableau de suivi et rapports standards.
> 
> Actions
> - Boréal : fournir le premier schéma d'architecture.
> - Marc : confirmer les modalités du connecteur interne.
> - Sophie : préparer les exigences de sécurité.
> 
> Note
> L'expérience mobile avancée n'a pas été discutée comme livrable distinct pendant cette rencontre.

### Architecture NOVA v1

Statut : approved. Responsable : Non précisé (aucun rôle attribué).

Date documentée / début : 2026-07-18. Échéance : Non précisée.

[page 1] Architecture NOVA - v1 - 18 juillet 2026 Version initiale préparée avant la décision de localisation des données. Utilisateur Portail NOVA API Données East US Schéma fictif - Projet 360

Source : 06_Architecture_et_decisions/Architecture_NOVA_v1.pdf — Page 1 (doc-042).

> [page 1] Architecture NOVA - v1 - 18 juillet 2026
> Version initiale préparée avant la décision de localisation des données.
> Utilisateur
> Portail NOVA
> API
> Données
>  East US
> Schéma fictif - Projet 360

### Donc on tranche Canada Central?

Statut : approved. Responsable : Non précisé (aucun rôle attribué).

Date documentée / début : 2026-07-23. Échéance : Non précisée.

09:10 Élodie : Donc on tranche Canada Central?

Source : 02_Reunions/M02_Transcript_Architecture_23juillet.txt — 09:10 · ligne 13 (doc-014).

> 09:10 Élodie : Donc on tranche Canada Central?

### ADR 007 Localisation donnees

Statut : approved. Responsable : Non précisé (aucun rôle attribué).

Date documentée / début : 2026-07-23. Échéance : Non précisée.

# ADR-007 - Localisation des données de production **Date de décision :** 23 juillet 2026 **Statut :** Acceptée ## Contexte L'architecture initiale de NOVA utilisait une région américaine. L'équipe sécurité demande que les données de production du projet demeurent au Canada. ## Décision L'environnement de production de NOVA sera déployé dans **Canada Central**. L'architecture v1 doit être considérée comme remplacée sur ce point. ## Conséquences - Boréal doit migrer les ressources prévues. - L'équipe architecture doit publier une version mise à jour du schéma. - Une validation technique doit confirmer la migration avant les tests de production.

Source : 06_Architecture_et_decisions/ADR-007_Localisation_donnees.md — Document (doc-041).

> # ADR-007 - Localisation des données de production
> 
> **Date de décision :** 23 juillet 2026  
> **Statut :** Acceptée
> 
> ## Contexte
> L'architecture initiale de NOVA utilisait une région américaine. L'équipe sécurité demande que les données de production du projet demeurent au Canada.
> 
> ## Décision
> L'environnement de production de NOVA sera déployé dans **Canada Central**. L'architecture v1 doit être considérée comme remplacée sur ce point.
> 
> ## Conséquences
> - Boréal doit migrer les ressources prévues.
> - L'équipe architecture doit publier une version mise à jour du schéma.
> - Une validation technique doit confirmer la migration avant les tests de production.

### CR 01 Rapports avances APPROUVE

Statut : approved. Responsable : Non précisé (aucun rôle attribué).

Date documentée / début : 2026-08-14. Échéance : Non précisée.

[page 1] Document fictif - Changement approuvé Page 1 DEMANDE DE CHANGEMENT CR-01 Objet Ajout de rapports avancés et export de synthèse. Impact financier Montant 24 000 $ Décision APPROUVÉE Date de décision 14 août 2026 Autorité Comité de projet Impact calendrier Aucun changement de la date cible annoncé au moment de l’approbation.

Source : 05_Contrats_et_finances/CR-01_Rapports_avances_APPROUVE.pdf — Page 1 (doc-036).

> [page 1] Document fictif - Changement approuvé
> Page 1
>  DEMANDE DE CHANGEMENT CR-01
> Objet
> Ajout de rapports avancés et export de synthèse.
> Impact financier
>  Montant
> 24 000 $
> Décision
> APPROUVÉE
> Date de décision
> 14 août 2026
> Autorité
> Comité de projet
> Impact calendrier
> Aucun changement de la date cible annoncé au moment de l’approbation.

### M03 CR Comite 27aout

Statut : approved. Responsable : Non précisé (aucun rôle attribué).

Date documentée / début : 2026-08-27. Échéance : Non précisée.

COMITÉ PROJET NOVA - 27 AOÛT 2026 Participants : Élodie, Marc, Sophie, Mélissa, Camille, Boréal Résumé de gestion - La migration de l'architecture vers Canada Central est déclarée terminée par Boréal et vérifiée par l'équipe architecture. - Le développement fonctionnel avance selon la portée de phase 1. - Les tests d'accessibilité ont identifié plusieurs anomalies. Certaines sont déjà corrigées, d'autres restent en traitement. - Le connecteur interne demeure un point d'attention mais aucun retard officiel de la date du 15 octobre n'est approuvé à ce moment. Points discutés Mélissa confirme que les anomalies de labels et de contraste ont été corrigées et validées les 15 et 20 août. Elle veut toutefois faire un deuxième passage clavier sur les modales. Sophie rappelle que la journalisation administrateur devra être vérifiée en situation réelle. Camille confirme que le premier lot de migration a produit quelques doublons à investiguer. Action : Boréal doit fournir une build de stabilisation début septembre.

Source : 02_Reunions/M03_CR_Comite_27aout.txt — Document (doc-015).

> COMITÉ PROJET NOVA - 27 AOÛT 2026
> Participants : Élodie, Marc, Sophie, Mélissa, Camille, Boréal
> 
> Résumé de gestion
> - La migration de l'architecture vers Canada Central est déclarée terminée par Boréal et vérifiée par l'équipe architecture.
> - Le développement fonctionnel avance selon la portée de phase 1.
> - Les tests d'accessibilité ont identifié plusieurs anomalies. Certaines sont déjà corrigées, d'autres restent en traitement.
> - Le connecteur interne demeure un point d'attention mais aucun retard officiel de la date du 15 octobre n'est approuvé à ce moment.
> 
> Points discutés
> Mélissa confirme que les anomalies de labels et de contraste ont été corrigées et validées les 15 et 20 août. Elle veut toutefois faire un deuxième passage clavier sur les modales. Sophie rappelle que la journalisation administrateur devra être vérifiée en situation réelle. Camille confirme que le premier lot de migration a produit quelques doublons à investiguer.
> 
> Action : Boréal doit fournir une build de stabilisation début septembre.

### Donc **approuvé**. Le 22 devient la date officielle. On doit mettre les plans et communications à jour.

Statut : approved. Responsable : Non précisé (aucun rôle attribué).

Date documentée / début : 2026-09-10. Échéance : Non précisée.

15:25 Élodie : Donc **approuvé**. Le 22 devient la date officielle. On doit mettre les plans et communications à jour.

Source : 02_Reunions/M04_Transcript_Comite_direction_10sept.txt — 15:25 · ligne 23 (doc-016).

> 15:25 Élodie : Donc **approuvé**. Le 22 devient la date officielle. On doit mettre les plans et communications à jour.

### Très bon point. On ferme. Nouvelle date officielle : 22 octobre. Mobile : aucune décision de dépense.

Statut : approved. Responsable : Non précisé (aucun rôle attribué).

Date documentée / début : 2026-09-10. Échéance : Non précisée.

15:40 Élodie : Très bon point. On ferme. Nouvelle date officielle : 22 octobre. Mobile : aucune décision de dépense.

Source : 02_Reunions/M04_Transcript_Comite_direction_10sept.txt — 15:40 · ligne 35 (doc-016).

> 15:40 Élodie : Très bon point. On ferme. Nouvelle date officielle : 22 octobre. Mobile : aucune décision de dépense.

### De mon côté, je ne veux pas compresser les tests sécurité pour sauver le 15. Le 22 me semble plus réalist

Statut : conditional. Responsable : Non précisé (aucun rôle attribué).

Date documentée / début : 2026-09-10. Échéance : Non précisée.

15:08 Sophie : De mon côté, je ne veux pas compresser les tests sécurité pour sauver le 15. Le 22 me semble plus réaliste, sous réserve des validations.

Source : 02_Reunions/M04_Transcript_Comite_direction_10sept.txt — 15:08 · ligne 10 (doc-016).

> 15:08 Sophie : De mon côté, je ne veux pas compresser les tests sécurité pour sauver le 15. Le 22 me semble plus réaliste, sous réserve des validations.

### Pas selon la portée actuelle. On va traiter ça séparément, aucune approbation aujourd'hui.

Statut : not_approved. Responsable : Non précisé (aucun rôle attribué).

Date documentée / début : 2026-09-10. Échéance : Non précisée.

15:37 Élodie : Pas selon la portée actuelle. On va traiter ça séparément, aucune approbation aujourd'hui.

Source : 02_Reunions/M04_Transcript_Comite_direction_10sept.txt — 15:37 · ligne 33 (doc-016).

> 15:37 Élodie : Pas selon la portée actuelle. On va traiter ça séparément, aucune approbation aujourd'hui.

### Je vais formuler la décision. La date cible de mise en production NOVA est déplacée du 15 octobre au **22

Statut : approved. Responsable : Non précisé (aucun rôle attribué).

Date documentée / début : 2026-09-10. Échéance : Non précisée.

15:22 Élodie : Je vais formuler la décision. La date cible de mise en production NOVA est déplacée du 15 octobre au **22 octobre 2026**. Est-ce que quelqu'un s'oppose?

Source : 02_Reunions/M04_Transcript_Comite_direction_10sept.txt — 15:22 · ligne 17 (doc-016).

> 15:22 Élodie : Je vais formuler la décision. La date cible de mise en production NOVA est déplacée du 15 octobre au **22 octobre 2026**. Est-ce que quelqu'un s'oppose?

### Non, attention : le comité a approuvé le 22 octobre le 10 septembre. Le plan projet n'a visiblement pas e

Statut : approved. Responsable : Non précisé (aucun rôle attribué).

Date documentée / début : 2026-09-15. Échéance : Non précisée.

09:18 - Nicolas : Non, attention : le comité a approuvé le 22 octobre le 10 septembre. Le plan projet n'a visiblement pas encore été corrigé.

Source : 07_Conversations_Teams/Teams_15sept_ProjetNOVA.txt — 09:18 · ligne 5 (doc-045).

> 09:18 - Nicolas : Non, attention : le comité a approuvé le 22 octobre le 10 septembre. Le plan projet n'a visiblement pas encore été corrigé.

### Petit rappel : à partir d'aujourd'hui, Nicolas reprend officiellement NOVA. Merci de l'inclure dans les s

Statut : approved. Responsable : Non précisé (aucun rôle attribué).

Date documentée / début : 2026-09-16. Échéance : Non précisée.

08:45 - Élodie : Petit rappel : à partir d'aujourd'hui, Nicolas reprend officiellement NOVA. Merci de l'inclure dans les suivis et décisions. Je reste joignable quelques jours pour la transition.

Source : 07_Conversations_Teams/Teams_16sept_Transition.txt — 08:45 · ligne 4 (doc-046).

> 08:45 - Élodie : Petit rappel : à partir d'aujourd'hui, Nicolas reprend officiellement NOVA. Merci de l'inclure dans les suivis et décisions. Je reste joignable quelques jours pour la transition.

### NOVA - transition de la charge de projet

Statut : approved. Responsable : Non précisé (aucun rôle attribué).

Date documentée / début : 2026-09-16. Échéance : Non précisée.

Bonjour, Comme convenu, Nicolas Perron prend officiellement la charge du projet NOVA à compter d'aujourd'hui, 16 septembre. Je demeure disponible quelques jours pour assurer le transfert, mais merci de diriger les décisions et suivis futurs vers Nicolas. Merci à tous, Élodie

Source : 01_Courriels/E06_Transition_charge_projet.eml — Corps du courriel (doc-006).

> Bonjour,
> Comme convenu, Nicolas Perron prend officiellement la charge du projet NOVA à compter d'aujourd'hui, 16 septembre.
> Je demeure disponible quelques jours pour assurer le transfert, mais merci de diriger les décisions et suivis futurs vers Nicolas.
> Merci à tous,
> Élodie

### Note transition Elodie 16sept

Statut : approved. Responsable : Non précisé (aucun rôle attribué).

Date documentée / début : 2026-09-16. Échéance : Non précisée.

NOTE DE TRANSITION - NOVA 16 septembre 2026 À compter d'aujourd'hui, Nicolas Perron reprend le rôle de chargé de projet NOVA. À surveiller : - faire mettre à jour la date dans tous les plans (le comité a approuvé le 22 octobre); - ne pas considérer le mobile avancé comme approuvé; - suivre le connecteur jusqu'à fermeture formelle; - obtenir le go sécurité et exploitation avant production. Élodie

Source : 04_Documents_projet/Note_transition_Elodie_16sept.txt — Document (doc-030).

> NOTE DE TRANSITION - NOVA
> 16 septembre 2026
> 
> À compter d'aujourd'hui, Nicolas Perron reprend le rôle de chargé de projet NOVA.
> 
> À surveiller :
> - faire mettre à jour la date dans tous les plans (le comité a approuvé le 22 octobre);
> - ne pas considérer le mobile avancé comme approuvé;
> - suivre le connecteur jusqu'à fermeture formelle;
> - obtenir le go sécurité et exploitation avant production.
> 
> Élodie

### M05 CR Suivi 18sept

Statut : approved. Responsable : Non précisé (aucun rôle attribué).

Date documentée / début : 2026-09-18. Échéance : Non précisée.

SUIVI LIVRAISON - 18 SEPTEMBRE 2026 Participants : Nicolas Perron, Marc Gervais, Sophie Lambert, Mélissa Gagnon, Olivier Côté, Boréal Faits saillants - INT-101 : le connecteur interne a été validé et fermé le 17 septembre. - DATA-401 : la correction d'idempotence a été validée; aucun doublon dans le dernier rejeu. - PERF-501 : performance revenue sous la cible de 1 seconde sur les essais de recherche. - SEC-210 : Boréal prépare un correctif concernant la journalisation des exports administrateur. La validation sécurité restera requise après livraison. - Accessibilité : ACC-301 et ACC-302 sont fermés. Un scénario de navigation clavier sur modal doit encore être vérifié. - Exploitation : le runbook n'est pas final. Le 22 octobre reste la date approuvée. Les participants rappellent toutefois que la date n'annule pas les critères de go-live.

Source : 02_Reunions/M05_CR_Suivi_18sept.txt — Document (doc-017).

> SUIVI LIVRAISON - 18 SEPTEMBRE 2026
> 
> Participants : Nicolas Perron, Marc Gervais, Sophie Lambert, Mélissa Gagnon, Olivier Côté, Boréal
> 
> Faits saillants
> - INT-101 : le connecteur interne a été validé et fermé le 17 septembre.
> - DATA-401 : la correction d'idempotence a été validée; aucun doublon dans le dernier rejeu.
> - PERF-501 : performance revenue sous la cible de 1 seconde sur les essais de recherche.
> - SEC-210 : Boréal prépare un correctif concernant la journalisation des exports administrateur. La validation sécurité restera requise après livraison.
> - Accessibilité : ACC-301 et ACC-302 sont fermés. Un scénario de navigation clavier sur modal doit encore être vérifié.
> - Exploitation : le runbook n'est pas final.
> 
> Le 22 octobre reste la date approuvée. Les participants rappellent toutefois que la date n'annule pas les critères de go-live.

### La compatibilité de base oui. Le package d'optimisation CR-04 à 18k non. Il n'est pas approuvé.

Statut : not_approved. Responsable : Non précisé (aucun rôle attribué).

Date documentée / début : 2026-09-22. Échéance : Non précisée.

13:06 - Nicolas : La compatibilité de base oui. Le package d'optimisation CR-04 à 18k non. Il n'est pas approuvé.

Source : 07_Conversations_Teams/Teams_22sept_Mobile.txt — 13:06 · ligne 5 (doc-048).

> 13:06 - Nicolas : La compatibilité de base oui. Le package d'optimisation CR-04 à 18k non. Il n'est pas approuvé.

### Decision Portee Phase2

Statut : not_approved. Responsable : Non précisé (aucun rôle attribué).

Date documentée / début : 2026-09-24. Échéance : Non précisée.

# Décision de portée - expérience mobile avancée **Date :** 24 septembre 2026 **Décision :** Les optimisations mobiles avancées associées à la demande CR-04 sont reportées à la phase 2. La phase 1 doit demeurer utilisable sur mobile, mais les travaux d'optimisation avancée proposés par Boréal ne font pas partie de la portée approuvée de la phase 1. Aucune dépense additionnelle liée à CR-04 ne doit être engagée sans nouvelle approbation.

Source : 06_Architecture_et_decisions/Decision_Portee_Phase2.md — Document (doc-044).

> # Décision de portée - expérience mobile avancée
> 
> **Date :** 24 septembre 2026  
> **Décision :** Les optimisations mobiles avancées associées à la demande CR-04 sont reportées à la phase 2.
> 
> La phase 1 doit demeurer utilisable sur mobile, mais les travaux d'optimisation avancée proposés par Boréal ne font pas partie de la portée approuvée de la phase 1. Aucune dépense additionnelle liée à CR-04 ne doit être engagée sans nouvelle approbation.

### NOVA - CR-04 / mobile

Statut : not_approved. Responsable : Non précisé (aucun rôle attribué).

Date documentée / début : 2026-09-24. Échéance : Non précisée.

Bonjour, Pour clarifier la portée : les optimisations mobiles avancées proposées dans CR-04 ne font pas partie de la phase 1 approuvée. Nous les reportons à la phase 2. Aucune dépense liée à CR-04 ne doit être engagée ou facturée sans nouvelle approbation. Nicolas

Source : 01_Courriels/E10_Fonction_mobile.eml — Corps du courriel (doc-010).

> Bonjour,
> Pour clarifier la portée : les optimisations mobiles avancées proposées dans CR-04 ne font pas partie de la phase 1 approuvée. Nous les reportons à la phase 2.
> Aucune dépense liée à CR-04 ne doit être engagée ou facturée sans nouvelle approbation.
> Nicolas

### Regarder, oui. Facturer du CR-04, non. Il n'est pas approuvé.

Statut : not_approved. Responsable : Non précisé (aucun rôle attribué).

Date documentée / début : 2026-09-26. Échéance : Non précisée.

10:25 Nicolas : Regarder, oui. Facturer du CR-04, non. Il n'est pas approuvé.

Source : 02_Reunions/M06_Transcript_Comite_26sept.txt — 10:25 · ligne 23 (doc-018).

> 10:25 Nicolas : Regarder, oui. Facturer du CR-04, non. Il n'est pas approuvé.

### Très bien. Je publie le compte rendu : cible 22 octobre, trois conditions de go-live.

Statut : conditional. Responsable : Non précisé (aucun rôle attribué).

Date documentée / début : 2026-09-26. Échéance : Non précisée.

10:30 Nicolas : Très bien. Je publie le compte rendu : cible 22 octobre, trois conditions de go-live.

Source : 02_Reunions/M06_Transcript_Comite_26sept.txt — 10:30 · ligne 25 (doc-018).

> 10:30 Nicolas : Très bien. Je publie le compte rendu : cible 22 octobre, trois conditions de go-live.

### OPS-601 · Nicolas : D'accord. Ceci fait partie des conditions de go-live du comité.

Statut : conditional. Responsable : Non précisé (aucun rôle attribué).

Date documentée / début : 2026-09-26. Échéance : Non précisée.

26 sept - Nicolas : D'accord. Ceci fait partie des conditions de go-live du comité.

Source : 03_Tickets/OPS-601.txt — Ligne 15 (doc-026).

> 26 sept - Nicolas : D'accord. Ceci fait partie des conditions de go-live du comité.

### Le 22 reste notre cible, mais je veux que ce soit écrit noir sur blanc : c'est conditionnel à ces trois é

Statut : conditional. Responsable : Non précisé (aucun rôle attribué).

Date documentée / début : 2026-09-26. Échéance : Non précisée.

10:15 Nicolas : Le 22 reste notre cible, mais je veux que ce soit écrit noir sur blanc : c'est conditionnel à ces trois éléments.

Source : 02_Reunions/M06_Transcript_Comite_26sept.txt — 10:15 · ligne 16 (doc-018).

> 10:15 Nicolas : Le 22 reste notre cible, mais je veux que ce soit écrit noir sur blanc : c'est conditionnel à ces trois éléments.

### NOVA - cible du 22 octobre et conditions restantes

Statut : conditional. Responsable : Non précisé (aucun rôle attribué).

Date documentée / début : 2026-09-27. Échéance : Non précisée.

Bonjour, Petit rappel pour éviter les versions différentes : la cible approuvée demeure le 22 octobre. Cette date est toutefois conditionnelle aux validations restantes : sécurité, accessibilité et préparation exploitation. Le comité du 26 septembre a précisé les éléments à fermer. Merci de ne pas communiquer le 22 comme un go garanti tant que ces validations ne sont pas terminées. Nicolas

Source : 01_Courriels/E09_Rappel_mise_en_production.eml — Corps du courriel (doc-009).

> Bonjour,
> Petit rappel pour éviter les versions différentes : la cible approuvée demeure le 22 octobre.
> Cette date est toutefois conditionnelle aux validations restantes : sécurité, accessibilité et préparation exploitation. Le comité du 26 septembre a précisé les éléments à fermer.
> Merci de ne pas communiquer le 22 comme un go garanti tant que ces validations ne sont pas terminées.
> Nicolas

## Responsables

### Charge du projet NOVA

Statut : historical. Responsable : Élodie Caron (Charge de projet).

Date documentée / début : 2026-07-07. Échéance : Non précisée.

Fin du rôle : 2026-09-16

Source : 02_Reunions/M01_CR_Demarrage_07juillet.txt — Attribution explicite de la charge de projet (doc-013).

> PROJET NOVA - COMPTE RENDU DE DÉMARRAGE
> Date : 7 juillet 2026
> Participants : Élodie Caron, Nicolas Perron, Marc Gervais, Sophie Lambert, Camille Beaulieu, représentant Boréal
> 
> Objectif
> Lancer officiellement le projet NOVA et confirmer la portée de la phase 1.
> 
> Décisions
> - Élodie Caron agit comme chargée de projet.
> - Budget initial maximal : 180 000 $ CAD.
> - Cible de mise en production : 15 octobre 2026.
> - La phase 1 comprend SSO, création/suivi de demandes, pièces jointes, workflow, tableau de suivi et rapports standards.
> 
> Actions
> - Boréal : fournir le premier schéma d'architecture.
> - Marc : confirmer les modalités du connecteur interne.
> - Sophie : préparer les exigences de sécurité.
> 
> Note
> L'expérience mobile avancée n'a pas été discutée comme livrable distinct pendant cette rencontre.

Source : 04_Documents_projet/Charte_Projet_NOVA_v1.txt — Attribution explicite de la charge de projet (doc-029).

> CHARTE DE PROJET NOVA - VERSION 1
> Date : 7 juillet 2026
> 
> Chargée de projet : Élodie Caron
> Fournisseur : Boréal Numérique
> Budget initial : 180 000 $ CAD
> Date cible de mise en production : 15 octobre 2026
> 
> Objectif
> Remplacer le suivi dispersé par courriel et fichiers locaux par un portail centralisé de demandes opérationnelles.
> 
> Portée phase 1
> - Authentification SSO
> - Création et suivi de demandes
> - Ajout de pièces jointes
> - Workflow de traitement
> - Tableau de suivi
> - Rapports standards
> 
> Cette charte constitue le point de départ du projet et n'est pas mise à jour automatiquement après chaque décision de comité.

### Charge du projet NOVA

Statut : assigned. Responsable : Nicolas Perron (Charge de projet).

Date documentée / début : 2026-09-16. Échéance : Non précisée.

Source : 01_Courriels/E06_Transition_charge_projet.eml — Attribution explicite de la charge de projet (doc-006).

> Subject: NOVA - transition de la charge de projet
> From: Élodie Caron <elodie.caron@demo.example>
> To: equipe-nova@demo.example
> Date: Wed, 16 Sep 2026 08:35:00 -0400
> Bonjour,
> 
> Comme convenu, Nicolas Perron prend officiellement la charge du projet NOVA à compter d'aujourd'hui, 16 septembre.
> 
> Je demeure disponible quelques jours pour assurer le transfert, mais merci de diriger les décisions et suivis futurs vers Nicolas.
> 
> Merci à tous,
> Élodie

Source : 04_Documents_projet/Note_transition_Elodie_16sept.txt — Attribution explicite de la charge de projet (doc-030).

> NOTE DE TRANSITION - NOVA
> 16 septembre 2026
> 
> À compter d'aujourd'hui, Nicolas Perron reprend le rôle de chargé de projet NOVA.
> 
> À surveiller :
> - faire mettre à jour la date dans tous les plans (le comité a approuvé le 22 octobre);
> - ne pas considérer le mobile avancé comme approuvé;
> - suivre le connecteur jusqu'à fermeture formelle;
> - obtenir le go sécurité et exploitation avant production.
> 
> Élodie

### Cadrage

Statut : documented. Responsable : Élodie Caron (Responsable du plan).

Date documentée / début : 2026-09-12. Échéance : Non précisée.

Attribution déclarée dans le plan ; les transitions de gouvernance prévalent.

Source : 04_Documents_projet/Plan_Projet_NOVA_v3_12sept.xlsx — Plan projet · ligne 3 (doc-032).

> P-01 | Cadrage | Terminé | Élodie Caron | 2026-07-07 | 2026-07-18 |

### Architecture

Statut : documented. Responsable : Marc Gervais (Responsable du plan).

Date documentée / début : 2026-09-12. Échéance : Non précisée.

Attribution déclarée dans le plan ; les transitions de gouvernance prévalent.

Source : 04_Documents_projet/Plan_Projet_NOVA_v3_12sept.xlsx — Plan projet · ligne 4 (doc-032).

> P-02 | Architecture | Terminé | Marc Gervais | 2026-07-14 | 2026-08-28 | Migration Canada requise

### Développement phase 1

Statut : documented. Responsable : Boréal Numérique (Responsable du plan).

Date documentée / début : 2026-09-12. Échéance : Non précisée.

Attribution déclarée dans le plan ; les transitions de gouvernance prévalent.

Source : 04_Documents_projet/Plan_Projet_NOVA_v3_12sept.xlsx — Plan projet · ligne 5 (doc-032).

> P-03 | Développement phase 1 | En cours | Boréal Numérique | 2026-07-20 | 2026-09-30 |

### Tests intégrés

Statut : documented. Responsable : Mélissa Gagnon (Responsable du plan).

Date documentée / début : 2026-09-12. Échéance : Non précisée.

Attribution déclarée dans le plan ; les transitions de gouvernance prévalent.

Source : 04_Documents_projet/Plan_Projet_NOVA_v3_12sept.xlsx — Plan projet · ligne 6 (doc-032).

> P-04 | Tests intégrés | À venir | Mélissa Gagnon | 2026-09-21 | 2026-10-05 |

### Préparation exploitation

Statut : documented. Responsable : Olivier Côté (Responsable du plan).

Date documentée / début : 2026-09-12. Échéance : Non précisée.

Attribution déclarée dans le plan ; les transitions de gouvernance prévalent.

Source : 04_Documents_projet/Plan_Projet_NOVA_v3_12sept.xlsx — Plan projet · ligne 7 (doc-032).

> P-05 | Préparation exploitation | À venir | Olivier Côté | 2026-09-28 | 2026-10-10 |

### Mise en production

Statut : documented. Responsable : Nicolas Perron (Responsable du plan).

Date documentée / début : 2026-09-12. Échéance : Non précisée.

Attribution déclarée dans le plan ; les transitions de gouvernance prévalent.

Source : 04_Documents_projet/Plan_Projet_NOVA_v3_12sept.xlsx — Plan projet · ligne 8 (doc-032).

> P-06 | Mise en production | À venir | Nicolas Perron | 2026-10-15 | 2026-10-15 | Cible de planification

## Engagements

### - Boréal : fournir le premier schéma d'architecture.

Statut : documented. Responsable : Boréal (Responsable explicitement désigné).

Date documentée / début : 2026-07-07. Échéance : Non précisée.

Engagement documenté ; réalisation non déduite. Les échéances relatives restent dans l’extrait.

Source : 02_Reunions/M01_CR_Demarrage_07juillet.txt — Ligne 15 (doc-013).

> - Boréal : fournir le premier schéma d'architecture.

### - Marc : confirmer les modalités du connecteur interne.

Statut : documented. Responsable : Marc Gervais (Responsable explicitement désigné).

Date documentée / début : 2026-07-07. Échéance : Non précisée.

Engagement documenté ; réalisation non déduite. Les échéances relatives restent dans l’extrait.

Source : 02_Reunions/M01_CR_Demarrage_07juillet.txt — Ligne 16 (doc-013).

> - Marc : confirmer les modalités du connecteur interne.

### - Sophie : préparer les exigences de sécurité.

Statut : documented. Responsable : Sophie Lambert (Responsable explicitement désigné).

Date documentée / début : 2026-07-07. Échéance : Non précisée.

Engagement documenté ; réalisation non déduite. Les échéances relatives restent dans l’extrait.

Source : 02_Reunions/M01_CR_Demarrage_07juillet.txt — Ligne 17 (doc-013).

> - Sophie : préparer les exigences de sécurité.

### Action : Boréal doit fournir une build de stabilisation début septembre.

Statut : documented. Responsable : Boréal (Responsable explicitement désigné).

Date documentée / début : 2026-08-27. Échéance : Non précisée.

Engagement documenté ; réalisation non déduite. Les échéances relatives restent dans l’extrait.

Source : 02_Reunions/M03_CR_Comite_27aout.txt — Ligne 13 (doc-015).

> Action : Boréal doit fournir une build de stabilisation début septembre.

### 10:12 Julien : On vise le correctif ACC-303 dans la prochaine build. Pour le runbook je relance notre équipe ops.

Statut : documented. Responsable : Julien Moreau (Auteur de l’engagement).

Date documentée / début : 2026-09-26. Échéance : Non précisée.

Engagement documenté ; réalisation non déduite. Les échéances relatives restent dans l’extrait.

Source : 02_Reunions/M06_Transcript_Comite_26sept.txt — Ligne 15 (doc-018).

> 10:12 Julien : On vise le correctif ACC-303 dans la prochaine build. Pour le runbook je relance notre équipe ops.

### - Boréal doit migrer les ressources prévues.

Statut : documented. Responsable : Boréal (Responsable explicitement désigné).

Date documentée / début : 2026-07-23. Échéance : Non précisée.

Engagement documenté ; réalisation non déduite. Les échéances relatives restent dans l’extrait.

Source : 06_Architecture_et_decisions/ADR-007_Localisation_donnees.md — Ligne 13 (doc-041).

> - Boréal doit migrer les ressources prévues.

### - L'équipe architecture doit publier une version mise à jour du schéma.

Statut : documented. Responsable : L'équipe architecture (Responsable explicitement désigné).

Date documentée / début : 2026-07-23. Échéance : Non précisée.

Engagement documenté ; réalisation non déduite. Les échéances relatives restent dans l’extrait.

Source : 06_Architecture_et_decisions/ADR-007_Localisation_donnees.md — Ligne 14 (doc-041).

> - L'équipe architecture doit publier une version mise à jour du schéma.

## Échéances

### Cadrage

Statut : planned. Responsable : Élodie Caron (Responsable du plan).

Date documentée / début : 2026-07-07. Échéance : 2026-07-18.

Date planifiée ; ne constitue pas une réalisation confirmée.

Source : 04_Documents_projet/Plan_Projet_NOVA_v3_12sept.xlsx — Plan projet · ligne 3 (doc-032).

> P-01 | Cadrage | Terminé | Élodie Caron | 2026-07-07 | 2026-07-18 |

### Architecture

Statut : planned. Responsable : Marc Gervais (Responsable du plan).

Date documentée / début : 2026-07-14. Échéance : 2026-08-28.

Date planifiée ; ne constitue pas une réalisation confirmée.

Source : 04_Documents_projet/Plan_Projet_NOVA_v3_12sept.xlsx — Plan projet · ligne 4 (doc-032).

> P-02 | Architecture | Terminé | Marc Gervais | 2026-07-14 | 2026-08-28 | Migration Canada requise

### Développement phase 1

Statut : planned. Responsable : Boréal Numérique (Responsable du plan).

Date documentée / début : 2026-07-20. Échéance : 2026-09-30.

Date planifiée ; ne constitue pas une réalisation confirmée.

Source : 04_Documents_projet/Plan_Projet_NOVA_v3_12sept.xlsx — Plan projet · ligne 5 (doc-032).

> P-03 | Développement phase 1 | En cours | Boréal Numérique | 2026-07-20 | 2026-09-30 |

### Tests intégrés

Statut : planned. Responsable : Mélissa Gagnon (Responsable du plan).

Date documentée / début : 2026-09-21. Échéance : 2026-10-05.

Date planifiée ; ne constitue pas une réalisation confirmée.

Source : 04_Documents_projet/Plan_Projet_NOVA_v3_12sept.xlsx — Plan projet · ligne 6 (doc-032).

> P-04 | Tests intégrés | À venir | Mélissa Gagnon | 2026-09-21 | 2026-10-05 |

### Préparation exploitation

Statut : planned. Responsable : Olivier Côté (Responsable du plan).

Date documentée / début : 2026-09-28. Échéance : 2026-10-10.

Date planifiée ; ne constitue pas une réalisation confirmée.

Source : 04_Documents_projet/Plan_Projet_NOVA_v3_12sept.xlsx — Plan projet · ligne 7 (doc-032).

> P-05 | Préparation exploitation | À venir | Olivier Côté | 2026-09-28 | 2026-10-10 |

### Mise en production

Statut : superseded. Responsable : Nicolas Perron (Responsable du plan).

Date documentée / début : 2026-10-15. Échéance : 2026-10-15.

Date périmée · cible approuvée : 2026-10-22

Source : 04_Documents_projet/Plan_Projet_NOVA_v3_12sept.xlsx — Plan projet · ligne 8 (doc-032).

> P-06 | Mise en production | À venir | Nicolas Perron | 2026-10-15 | 2026-10-15 | Cible de planification

### Mise en production NOVA

Statut : conditional. Responsable : Nicolas Perron (Charge de projet).

Date documentée / début : Non précisée. Échéance : 2026-10-22.

La cible approuvée de mise en production est le 2026-10-22. Elle reste conditionnelle aux validations explicitement citées dans la dernière source.

Source : 01_Courriels/E09_Rappel_mise_en_production.eml — Date cible et décision (doc-009).

> Subject: NOVA - cible du 22 octobre et conditions restantes
> From: Nicolas Perron <nicolas.perron@demo.example>
> To: equipe-nova@demo.example
> Date: Sun, 27 Sep 2026 17:02:00 -0400
> Bonjour,
> 
> Petit rappel pour éviter les versions différentes : la cible approuvée demeure le 22 octobre.
> 
> Cette date est toutefois conditionnelle aux validations restantes : sécurité, accessibilité et préparation exploitation. Le comité du 26 septembre a précisé les éléments à fermer.
> 
> Merci de ne pas communiquer le 22 comme un go garanti tant que ces validations ne sont pas terminées.
> 
> Nicolas

Source : 01_Courriels/E06_Transition_charge_projet.eml — Attribution explicite de la charge de projet (doc-006).

> Subject: NOVA - transition de la charge de projet
> From: Élodie Caron <elodie.caron@demo.example>
> To: equipe-nova@demo.example
> Date: Wed, 16 Sep 2026 08:35:00 -0400
> Bonjour,
> 
> Comme convenu, Nicolas Perron prend officiellement la charge du projet NOVA à compter d'aujourd'hui, 16 septembre.
> 
> Je demeure disponible quelques jours pour assurer le transfert, mais merci de diriger les décisions et suivis futurs vers Nicolas.
> 
> Merci à tous,
> Élodie

Source : 04_Documents_projet/Note_transition_Elodie_16sept.txt — Attribution explicite de la charge de projet (doc-030).

> NOTE DE TRANSITION - NOVA
> 16 septembre 2026
> 
> À compter d'aujourd'hui, Nicolas Perron reprend le rôle de chargé de projet NOVA.
> 
> À surveiller :
> - faire mettre à jour la date dans tous les plans (le comité a approuvé le 22 octobre);
> - ne pas considérer le mobile avancé comme approuvé;
> - suivre le connecteur jusqu'à fermeture formelle;
> - obtenir le go sécurité et exploitation avant production.
> 
> Élodie

## Risques

### R-04 · Accessibilité

Statut : open. Responsable : Mélissa Gagnon (Propriétaire du risque).

Date documentée / début : 2026-09-29. Échéance : Non précisée.

État déclaré dans le registre ; consulter les divergences ci-dessous.

Source : 04_Documents_projet/Registre_Risques_29sept.xlsx — Registre Risques · ligne extraite 6 (doc-034).

> R-04 | Accessibilité | Moyenne | Moyen | Mélissa Gagnon | Ouvert | Fermer ACC-303 |

### R-03 · Préparation exploitation incomplète

Statut : open. Responsable : Olivier Côté (Propriétaire du risque).

Date documentée / début : 2026-09-29. Échéance : Non précisée.

État déclaré dans le registre ; consulter les divergences ci-dessous.

Source : 04_Documents_projet/Registre_Risques_29sept.xlsx — Registre Risques · ligne extraite 5 (doc-034).

> R-03 | Préparation exploitation incomplète | Moyenne | Élevé | Olivier Côté | Ouvert | Finaliser le runbook et le rollback |

### R-01 · Retard du connecteur interne

Statut : open. Responsable : Marc Gervais (Propriétaire du risque).

Date documentée / début : 2026-09-29. Échéance : Non précisée.

État déclaré dans le registre ; consulter les divergences ci-dessous.

Source : 04_Documents_projet/Registre_Risques_29sept.xlsx — Registre Risques · ligne extraite 3 (doc-034).

> R-01 | Retard du connecteur interne | Moyenne | Élevé | Marc Gervais | Ouvert | Suivi fournisseur hebdomadaire | Suivi au 9 septembre 2026

### R-02 · Validation sécurité incomplète

Statut : open. Responsable : Sophie Lambert (Propriétaire du risque).

Date documentée / début : 2026-09-29. Échéance : Non précisée.

État déclaré dans le registre ; consulter les divergences ci-dessous.

Source : 04_Documents_projet/Registre_Risques_29sept.xlsx — Registre Risques · ligne extraite 4 (doc-034).

> R-02 | Validation sécurité incomplète | Élevée | Élevé | Sophie Lambert | Ouvert | Re-test de SEC-210 avant go-live |

### R-05 · Migration données

Statut : completed. Responsable : Camille Beaulieu (Propriétaire du risque).

Date documentée / début : 2026-09-29. Échéance : Non précisée.

État déclaré dans le registre ; consulter les divergences ci-dessous.

Source : 04_Documents_projet/Registre_Risques_29sept.xlsx — Registre Risques · ligne extraite 7 (doc-034).

> R-05 | Migration données | Faible | Moyen | Camille Beaulieu | Fermé | Contrôle de doublons |

### ACC-303 · tab dans popup

Statut : open. Responsable : Non précisé (aucun rôle attribué).

Date documentée / début : 2026-09-17. Échéance : Non précisée.

Ticket ouvert ou en validation. Le demandeur ne constitue pas un responsable assigné.

Source : 03_Tickets/ACC-303.txt — Ticket complet (doc-021).

> TICKET ACC-303
> Titre : tab dans popup
> Créé : 17 septembre 2026
> Demandeur : Mélissa Gagnon
> Priorité : Haute
> Statut : OUVERT
> 
> Description initiale :
> Je peux ouvrir la popup au clavier mais après c'est bizarre. Tab ne va pas partout et j'ai dû prendre la souris pour sauver.
> 
> Pièce jointe : ACC-303_focus.png
> 
> Commentaires :
> 17 sept 13:14 - Mélissa : Reproduit sur Chrome et Edge. Le focus reste entre le champ Nom et Commentaire; le bouton Enregistrer n'est jamais atteint avec Tab.
> 18 sept 09:50 - Boréal : On a reproduit. Le composant modal intercepte le focus avec une liste d'éléments focusables incomplète.
> 26 sept 11:03 - Mélissa : Toujours ouvert. Correctif annoncé pour la prochaine build.

### OPS-601 · runbook pas prêt

Statut : open. Responsable : Non précisé (aucun rôle attribué).

Date documentée / début : 2026-09-25. Échéance : Non précisée.

Ticket ouvert ou en validation. Le demandeur ne constitue pas un responsable assigné.

Source : 03_Tickets/OPS-601.txt — Ticket complet (doc-026).

> TICKET OPS-601
> Titre : runbook pas prêt
> Créé : 25 septembre 2026
> Demandeur : Olivier Côté
> Priorité : Haute
> Statut : OUVERT
> 
> Description initiale :
> Le doc est pas prêt pour prod.
> 
> Pièce jointe : OPS-601_runbook.png
> 
> Commentaires :
> 25 sept - Olivier : Il manque au minimum la procédure de rollback. La capture jointe identifie aussi une autre étape à compléter. J'ai besoin de quelque chose qu'une autre personne peut exécuter sans appeler l'équipe projet.
> 26 sept - Nicolas : D'accord. Ceci fait partie des conditions de go-live du comité.
> 29 sept - Olivier : Toujours pas reçu la version finale.

### SEC-210 · Audit admin incomplet sur export

Statut : in_review. Responsable : Non précisé (aucun rôle attribué).

Date documentée / début : 2026-09-12. Échéance : Non précisée.

Ticket ouvert ou en validation. Le demandeur ne constitue pas un responsable assigné.

Source : 03_Tickets/SEC-210.txt — Ticket complet (doc-028).

> TICKET SEC-210
> Titre : Audit admin incomplet sur export
> Créé : 12 septembre 2026
> Demandeur : Sophie Lambert
> Priorité : Bloquante avant production
> Statut : EN VALIDATION
> 
> Description :
> Les actions administratives sensibles doivent être traçables. Lors d'un export CSV, l'événement détaillé attendu n'apparaît pas dans le journal.
> 
> Étapes :
> 1. Se connecter avec un compte administrateur.
> 2. Ouvrir un dossier.
> 3. Exporter les données en CSV.
> 4. Consulter le journal d'audit.
> 
> Attendu : événement EXPORT_CSV avec utilisateur, horodatage et identifiant du dossier.
> Observé : une ligne EXPORT_CSV existe avec utilisateur et horodatage, mais l'objet (identifiant du dossier) et le résultat sont absents. La connexion, la consultation et la déconnexion sont présentes. Le défaut est une journalisation d'export incomplète, pas l'absence totale d'une ligne d'export.
> 
> Pièce jointe : SEC-210_audit.png
> 
> Commentaires :
> 19 sept 10:22 - Boréal : Fix déployé sur l'environnement de validation. Pour nous c'est réglé.
> 19 sept 14:05 - Sophie : Merci. Nous devons refaire notre scénario et confirmer nous-mêmes. Ne pas fermer avant validation sécurité.
> 26 sept 15:40 - Sophie : Re-test planifié. Statut maintenu EN VALIDATION.

## Divergences à vérifier

### Le plan contient une ancienne date

Le plan indique le 2026-10-15, alors que la cible approuvée est le 2026-10-22. La décision de gouvernance prévaut.

Source : 04_Documents_projet/Plan_Projet_NOVA_v3_12sept.xlsx — Plan projet · ligne 8.

> P-06 | Mise en production | À venir | Nicolas Perron | 2026-10-15 | 2026-10-15 | Cible de planification

Source : 01_Courriels/E09_Rappel_mise_en_production.eml — Date cible et décision.

> Subject: NOVA - cible du 22 octobre et conditions restantes
> From: Nicolas Perron <nicolas.perron@demo.example>
> To: equipe-nova@demo.example
> Date: Sun, 27 Sep 2026 17:02:00 -0400
> Bonjour,
> 
> Petit rappel pour éviter les versions différentes : la cible approuvée demeure le 22 octobre.
> 
> Cette date est toutefois conditionnelle aux validations restantes : sécurité, accessibilité et préparation exploitation. Le comité du 26 septembre a précisé les éléments à fermer.
> 
> Merci de ne pas communiquer le 22 comme un go garanti tant que ces validations ne sont pas terminées.
> 
> Nicolas

### Le go-live reste conditionnel

3 tickets de sécurité, d’accessibilité ou d’exploitation restent ouverts ou en validation. Une livraison fournisseur ne constitue pas une acceptation.

Source : 03_Tickets/ACC-303.txt — Ticket complet.

> TICKET ACC-303
> Titre : tab dans popup
> Créé : 17 septembre 2026
> Demandeur : Mélissa Gagnon
> Priorité : Haute
> Statut : OUVERT
> 
> Description initiale :
> Je peux ouvrir la popup au clavier mais après c'est bizarre. Tab ne va pas partout et j'ai dû prendre la souris pour sauver.
> 
> Pièce jointe : ACC-303_focus.png
> 
> Commentaires :
> 17 sept 13:14 - Mélissa : Reproduit sur Chrome et Edge. Le focus reste entre le champ Nom et Commentaire; le bouton Enregistrer n'est jamais atteint avec Tab.
> 18 sept 09:50 - Boréal : On a reproduit. Le composant modal intercepte le focus avec une liste d'éléments focusables incomplète.
> 26 sept 11:03 - Mélissa : Toujours ouvert. Correctif annoncé pour la prochaine build.

Source : 03_Tickets/OPS-601.txt — Ticket complet.

> TICKET OPS-601
> Titre : runbook pas prêt
> Créé : 25 septembre 2026
> Demandeur : Olivier Côté
> Priorité : Haute
> Statut : OUVERT
> 
> Description initiale :
> Le doc est pas prêt pour prod.
> 
> Pièce jointe : OPS-601_runbook.png
> 
> Commentaires :
> 25 sept - Olivier : Il manque au minimum la procédure de rollback. La capture jointe identifie aussi une autre étape à compléter. J'ai besoin de quelque chose qu'une autre personne peut exécuter sans appeler l'équipe projet.
> 26 sept - Nicolas : D'accord. Ceci fait partie des conditions de go-live du comité.
> 29 sept - Olivier : Toujours pas reçu la version finale.

Source : 03_Tickets/SEC-210.txt — Ticket complet.

> TICKET SEC-210
> Titre : Audit admin incomplet sur export
> Créé : 12 septembre 2026
> Demandeur : Sophie Lambert
> Priorité : Bloquante avant production
> Statut : EN VALIDATION
> 
> Description :
> Les actions administratives sensibles doivent être traçables. Lors d'un export CSV, l'événement détaillé attendu n'apparaît pas dans le journal.
> 
> Étapes :
> 1. Se connecter avec un compte administrateur.
> 2. Ouvrir un dossier.
> 3. Exporter les données en CSV.
> 4. Consulter le journal d'audit.
> 
> Attendu : événement EXPORT_CSV avec utilisateur, horodatage et identifiant du dossier.
> Observé : une ligne EXPORT_CSV existe avec utilisateur et horodatage, mais l'objet (identifiant du dossier) et le résultat sont absents. La connexion, la consultation et la déconnexion sont présentes. Le défaut est une journalisation d'export incomplète, pas l'absence totale d'une ligne d'export.
> 
> Pièce jointe : SEC-210_audit.png
> 
> Commentaires :
> 19 sept 10:22 - Boréal : Fix déployé sur l'environnement de validation. Pour nous c'est réglé.
> 19 sept 14:05 - Sophie : Merci. Nous devons refaire notre scénario et confirmer nous-mêmes. Ne pas fermer avant validation sécurité.
> 26 sept 15:40 - Sophie : Re-test planifié. Statut maintenu EN VALIDATION.

### Un statut « vert » contredit les validations restantes

Le rapport de statut présente des volets comme terminés ; les tickets et le comité ultérieurs maintiennent des conditions ouvertes.

Source : 04_Documents_projet/Rapport_Statut_21sept.pdf — Page 1.

> [page 1] Rapport de statut fictif
> Page 1
>  RAPPORT DE STATUT - NOVA - 21 SEPTEMBRE
>  2026
> Synthèse
>  Dimension
> Statut
> Commentaire
> Échéancier
> VERT
> Cible 22 octobre
> Budget
> VERT
> Sous le plafond contractuel
> Sécurité
> VERT
> Correctif SEC-210 livré
> Accessibilité
> VERT
> Correctifs appliqués
> Exploitation
> JAUNE
> Runbook à finaliser
> Commentaire de gestion
> Le projet est présenté comme globalement sous contrôle. Le rapport a été préparé avant la dernière
> vérification détaillée de certains tickets.

Source : 03_Tickets/ACC-303.txt — Ticket complet.

> TICKET ACC-303
> Titre : tab dans popup
> Créé : 17 septembre 2026
> Demandeur : Mélissa Gagnon
> Priorité : Haute
> Statut : OUVERT
> 
> Description initiale :
> Je peux ouvrir la popup au clavier mais après c'est bizarre. Tab ne va pas partout et j'ai dû prendre la souris pour sauver.
> 
> Pièce jointe : ACC-303_focus.png
> 
> Commentaires :
> 17 sept 13:14 - Mélissa : Reproduit sur Chrome et Edge. Le focus reste entre le champ Nom et Commentaire; le bouton Enregistrer n'est jamais atteint avec Tab.
> 18 sept 09:50 - Boréal : On a reproduit. Le composant modal intercepte le focus avec une liste d'éléments focusables incomplète.
> 26 sept 11:03 - Mélissa : Toujours ouvert. Correctif annoncé pour la prochaine build.

Source : 03_Tickets/OPS-601.txt — Ticket complet.

> TICKET OPS-601
> Titre : runbook pas prêt
> Créé : 25 septembre 2026
> Demandeur : Olivier Côté
> Priorité : Haute
> Statut : OUVERT
> 
> Description initiale :
> Le doc est pas prêt pour prod.
> 
> Pièce jointe : OPS-601_runbook.png
> 
> Commentaires :
> 25 sept - Olivier : Il manque au minimum la procédure de rollback. La capture jointe identifie aussi une autre étape à compléter. J'ai besoin de quelque chose qu'une autre personne peut exécuter sans appeler l'équipe projet.
> 26 sept - Nicolas : D'accord. Ceci fait partie des conditions de go-live du comité.
> 29 sept - Olivier : Toujours pas reçu la version finale.

Source : 03_Tickets/SEC-210.txt — Ticket complet.

> TICKET SEC-210
> Titre : Audit admin incomplet sur export
> Créé : 12 septembre 2026
> Demandeur : Sophie Lambert
> Priorité : Bloquante avant production
> Statut : EN VALIDATION
> 
> Description :
> Les actions administratives sensibles doivent être traçables. Lors d'un export CSV, l'événement détaillé attendu n'apparaît pas dans le journal.
> 
> Étapes :
> 1. Se connecter avec un compte administrateur.
> 2. Ouvrir un dossier.
> 3. Exporter les données en CSV.
> 4. Consulter le journal d'audit.
> 
> Attendu : événement EXPORT_CSV avec utilisateur, horodatage et identifiant du dossier.
> Observé : une ligne EXPORT_CSV existe avec utilisateur et horodatage, mais l'objet (identifiant du dossier) et le résultat sont absents. La connexion, la consultation et la déconnexion sont présentes. Le défaut est une journalisation d'export incomplète, pas l'absence totale d'une ligne d'export.
> 
> Pièce jointe : SEC-210_audit.png
> 
> Commentaires :
> 19 sept 10:22 - Boréal : Fix déployé sur l'environnement de validation. Pour nous c'est réglé.
> 19 sept 14:05 - Sophie : Merci. Nous devons refaire notre scénario et confirmer nous-mêmes. Ne pas fermer avant validation sécurité.
> 26 sept 15:40 - Sophie : Re-test planifié. Statut maintenu EN VALIDATION.

### Un risque clos reste ouvert dans le registre

Le registre conserve le risque du connecteur ouvert, alors que le ticket d’intégration atteste sa fermeture. Vérifier la date de suivi de la ligne.

Source : 04_Documents_projet/Registre_Risques_29sept.xlsx — Ligne du risque connecteur.

> R-01 | Retard du connecteur interne | Moyenne | Élevé | Marc Gervais | Ouvert | Suivi fournisseur hebdomadaire | Suivi au 9 septembre 2026

Source : 03_Tickets/INT-101.txt — Ticket complet.

> TICKET INT-101
> Titre : Ça marche pas avec le connecteur
> Créé : 5 septembre 2026
> Demandeur : Marc Gervais
> Priorité : Haute
> Statut : Fermé
> 
> Description initiale :
> Ça marche pas. On cherche un dossier existant et on a rien. Voir capture.
> 
> Pièce jointe : INT-101_aucun_resultat.png
> 
> Commentaires :
> 05 sept 09:41 - Marc : C'était OK hier en DEV. Là en INT toutes les recherches par numéro retournent vide.
> 05 sept 11:18 - Boréal : On voit des 401 sur l'appel vers le service interne. Le jeton de service semble expiré après le changement de secret.
> 08 sept 16:02 - Marc : Le remplacement du secret est fait mais il reste des erreurs intermittentes. Ça met en risque le 15 octobre si on n'a pas de stabilité cette semaine.
> 17 sept 14:23 - Boréal : Correctif déployé. 120 recherches rejouées, 120 réponses valides.
> 17 sept 16:10 - Marc : Validé côté intégration. Je ferme.
> 
> Résolution : rotation du secret + correction de la logique de renouvellement du jeton.
