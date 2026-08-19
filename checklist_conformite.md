# Checklist de conformité MEMTRACE

## État général

Le projet est désormais dans un état de prototype fonctionnel avec des éléments validés, mais il reste un projet de démonstration scientifique et non un produit de production complet.

## Tableau de conformité

| Exigence / point | Statut | Observation |
|---|---|---|
| Ingestion de traces JSONL | OK | La route `/ingest` lit un fichier JSONL, valide les épisodes, stocke en SQLite et relance un recalcul de score. |
| Validation des invariants temporels | OK | Les modèles Pydantic vérifient `seq` croissant, `ts` monotone, `ts_end >= ts_start` et cohérence du premier/dernier événement. |
| Protection contre fuite de contenu brut | OK | Le test de sécurité vérifie que le texte sensible ne passe pas dans la sortie normalisée. |
| Stockage SQLite | OK | Les épisodes sont stockés avec leur JSON serialisé dans la table `episodes`. |
| Extraction de descripteurs ML | OK | Le script d’extraction calcule plusieurs features pertinentes : nombre d’événements, durée, outils, écritures mémoire, lectures, scores, latence moyenne. |
| Entraînement du modèle | OK | Utilisation d’une régression logistique avec séparation train/test et AUROC sur le jeu de test. |
| Sauvegarde des scores | OK | Les scores sont recalculés et écrits dans la base. |
| API de recalcul | OK | Route `/retrain` disponible pour relancer le score sur les données stockées. |
| Interface web | PARTIEL | L’UI affiche un tableau de scores, mais reste limitée et ne montre pas encore le détail complet d’un épisode ou l’analyse forensique avancée. |
| Qualité de la donnée | PARTIEL | Le dataset synthétique reste simplifié ; il est utile pour un prototype, mais pas pour un benchmark scientifique robuste. |
| Réproductibilité / conteneurisation | OK | Dockerfile et docker-compose sont présents et le lancement est standardisé. |
| CI / validation de code | OK | La CI vérifie syntaxe et exécute les tests. |
| Production / robustesse avancée | PARTIEL | L’API est fonctionnelle, mais manque encore de robustesse réelle, de gestion avancée des erreurs et d’outils d’investigation. |

## Résultat synthétique

- Conforme pour le cœur de la preuve de concept : OUI
- Conforme pour un projet de démonstration robuste : OUI
- Conforme pour un outil de production / benchmark de recherche sérieux : PARTIEL

## Points à améliorer pour aller au niveau complet

1. Ajouter des scénarios plus variés et réalistes dans le dataset.
2. Ajouter plus de familles d’attaques de mémoire et de contexte.
3. Rendre l’interface d’investigation plus détaillée.
4. Ajouter une vraie page d’analyse d’un épisode spécifique.
5. Ajouter plus de contrôles de sécurité API / validations sur les uploads.
6. Vérifier la qualité ML sur un jeu de données plus riche et plus représentatif.

## Conclusion

Le projet a atteint un état stable et exploitable comme prototype de détection forensique, avec la structure, la validation, la base de données, le calcul de score et la CI correctement positionnés.

Il reste un projet à finaliser scientifiquement et fonctionnellement, mais la base de conformité technique est maintenant en place.
