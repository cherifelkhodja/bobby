# Polices embarquées

Ces fichiers sont utilisés par `contrat_at.html` (génération PDF WeasyPrint).
L'image Docker de production n'embarque que Liberation / DejaVu / Carlito :
les polices de la charte doivent donc être versionnées ici, sinon WeasyPrint
retombe silencieusement sur une police de substitution.

| Police | Usage | Licence |
|--------|-------|---------|
| Space Grotesk | Titres, intitulés, labels | SIL Open Font License 1.1 |
| Hanken Grotesk | Corps de texte | SIL Open Font License 1.1 |

Les deux familles sont sous SIL OFL 1.1, qui autorise la redistribution
embarquée. Fichiers récupérés depuis Google Fonts (graisses 400/500/600/700).
