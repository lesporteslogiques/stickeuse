# Lexique — Stickeuse QL-570

> Les mots techniques croisés dans le code et la doc, définis **simplement et une
> seule fois**. À enrichir au fil de l'eau.

**backend** — la « voie » par laquelle le programme parle à l'imprimante : ici
`linux_kernel` (en passant par un nœud `lpX`) ou `pyusb` (en s'adressant
directement au bus USB).

**constructeur** — la fonction qui s'exécute quand on *crée* un objet (en Python,
`__init__`). Un *dataclass* le fabrique automatiquement à partir des champs déclarés.

**dataclass** — une classe « boîte à données » : on déclare des champs (port,
modèle…), et Python génère pour nous le constructeur et un affichage lisible.

**docstring** — le texte entre triples guillemets placé en première ligne d'un
module, d'une classe ou d'une fonction. Il documente son rôle et reste accessible
via `help()`. Contrairement à un commentaire `#`, il est conservé dans l'objet.

**espace de noms** — la table « nom → objet » que Python consulte pour savoir à
quoi correspond un nom. Plusieurs tables empilées (locale, module, intégrés),
fouillées du plus interne au plus externe ; le premier trouvé gagne.

**exception** — un signal « je ne peux pas continuer ». On la « lève » avec
`raise`, et un autre bout de code peut la « rattraper » avec `except`.

**f-string** — une chaîne préfixée par `f` qui insère la valeur d'une variable
directement dans le texte : `f"trouvée sur {port}"`.

**glob** — module standard qui liste les fichiers correspondant à un *motif*
(avec des *jokers* façon *shell*).

**hexadécimal (`0x…`)** — une façon d'écrire les nombres en base 16, courante pour
les codes USB. `0x04f9` est le même nombre que celui noté `04f9` dans udev.

**idVendor / idProduct** — deux codes USB qui identifient le fabricant
(`04f9` = Brother) et le modèle (`2028` = QL-570).

**joker** (*wildcard*) — caractère spécial d'un motif représentant une partie
variable : `*` = n'importe quelle suite de caractères, `?` = exactement un caractère.

**motif** (*pattern*) — un modèle de texte qu'une famille de chaînes peut
« remplir ». Ex. : `/dev/usb/lp*` désigne `lp0`, `lp1`, `lp3`…

**nœud `/dev/usb/lpX`** — le fichier-périphérique par lequel le noyau expose une
imprimante USB. Le numéro `X` varie selon les branchements : jamais codé en dur.

**noyau** (*kernel*) — le cœur du système d'exploitation, qui parle au matériel.

**pyudev** — bibliothèque Python pour lire *udev* : interroger les périphériques
et suivre leurs branchements.

**pyusb** — bibliothèque Python pour parler directement aux périphériques USB
(via libusb), sans passer par un nœud `lpX`.

**shell** — la « coquille » du système : l'interpréteur de commandes (bash, zsh…)
par lequel on tape des ordres, qu'il transmet au noyau.

**udev** — le sous-système Linux qui décrit les périphériques et réagit à leurs
branchements et débranchements.

**`__name__` / `__main__`** — `__name__` vaut `"__main__"` quand on lance un
fichier directement, et le nom du module quand on l'importe. D'où le garde-fou
`if __name__ == "__main__":`, qui n'exécute le bloc de test que lors d'un
lancement direct.
