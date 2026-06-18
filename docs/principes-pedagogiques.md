# Principes pédagogiques — Stickeuse QL-570

> Le code de cette application doit être **lisible par quelqu'un qui apprend Python**.
> Pas une boîte noire : un code qui s'explique.

## Le cap

Quelqu'un qui débute en Python doit pouvoir ouvrir un fichier du projet et
**comprendre vraiment** ce qu'il fait — y compris ce que les développeurs
expérimentés jugent « évident ». Ici, expliquer l'évident n'est pas du bruit :
c'est le but.

## Règles de style

1. **Docstrings en français clair.** Chaque module, classe et fonction dit en
   une ou deux phrases *à quoi il sert* et *pourquoi*.
2. **Commenter le pourquoi et les concepts**, pas seulement la mécanique. Un
   concept nouveau (motif, nœud, dataclass, exception…) est expliqué **la
   première fois** qu'il apparaît.
3. **Deux garde-fous, valables pour tout commentaire :**
   - *Un commentaire doit rester vrai.* S'il décrit une ligne mot à mot et que
     la ligne change, il se met à mentir. On préfère donc expliquer
     l'**intention** (stable) plutôt que le détail (volatil).
   - *Un terme se définit une seule fois.* Les définitions vivent dans le
     lexique (`lexique.md`) ; on ne les répète pas partout.

## Les deux supports

- **Le code** porte les docstrings et les commentaires « pourquoi ».
- **Le lexique** (`lexique.md`) porte les définitions simples des termes, posées
  une seule fois. C'est ce qui permet aux commentaires de rester légers.

## Filiation

Cette idée — du code tissé avec sa prose explicative — porte un nom : la
*programmation lettrée* (Donald Knuth). Notre touche : le faire **simplement,
pour de vrais débutants**.
