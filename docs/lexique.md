# Lexique — Stickeuse QL-570

> Les mots techniques croisés dans le code et la doc, définis **simplement et une
> seule fois**. À enrichir au fil de l'eau.

**autostart** — le mécanisme qui lance un programme à l'ouverture de session.
Sous Linux, il suffit d'y déposer un fichier `.desktop` : celui de l'agent vit
dans `/etc/xdg/autostart/`, donc pour tous les comptes du poste.

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

**environnement virtuel (venv)** — un Python isolé, avec ses propres paquets, qui
n'interfère pas avec celui du système. Celui de l'appli vit dans `/opt/ql570/venv/`.
`sys.prefix` en donne la racine depuis le code — c'est ainsi qu'on retrouve
`brother_ql` sans dépendre du PATH.

**espace de noms** — la table « nom → objet » que Python consulte pour savoir à
quoi correspond un nom. Plusieurs tables empilées (locale, module, intégrés),
fouillées du plus interne au plus externe ; le premier trouvé gagne.

**événement (`threading.Event`)** — un interrupteur partagé entre deux fils
d'exécution : l'un le lève (`.set()`), l'autre le consulte (`.is_set()`). Sert ici
au bouton « Annuler » pour dire stop au fil qui imprime.

**exception** — un signal « je ne peux pas continuer ». On la « lève » avec
`raise`, et un autre bout de code peut la « rattraper » avec `except`.

**fil d'exécution (thread)** — une seconde ligne de travail à l'intérieur du même
programme, qui avance en même temps que la première. L'appli imprime dans un fil
séparé pour que la fenêtre reste vivante pendant ce temps. Règle absolue avec
Tkinter : seul le fil de l'interface touche aux widgets ; les autres lui passent
leurs messages par `after(0, …)`.

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

**mire** — image de contrôle. Celles de la Stickeuse (`test-stickeuse-*.png`, une
par rouleau et par orientation) réunissent sur une seule étiquette de quoi juger
la densité, la finesse de trait, l'échelle (une réglette de 30 mm à mesurer avec
une vraie règle) et l'orientation. Le mot est du vocabulaire d'imprimerie : il
figure sur l'étiquette imprimée, mais pas dans le nom du fichier, que doit
comprendre quelqu'un qui n'est pas du métier.

**prédécoupé** (*die-cut*) — rouleau dont chaque étiquette est déjà découpée à
une taille fixe (DK-11xxx). L'image doit donc faire exactement ces dimensions, au
pixel près. Par opposition au rouleau **continu** (DK-22xxx), une bande dont seule
la largeur est imposée et que la machine coupe à la longueur voulue.

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

**sudoers** — le fichier qui liste les comptes autorisés à utiliser `sudo`, donc
à exécuter des commandes en administrateur. Un compte absent de cette liste
obtient « n'est pas dans le fichier sudoers » : c'est le cas des postes du
FabLab, où l'on passe alors par `su -` et le mot de passe root.

**udev** — le sous-système Linux qui décrit les périphériques et réagit à leurs
branchements et débranchements.

**`__name__` / `__main__`** — `__name__` vaut `"__main__"` quand on lance un
fichier directement, et le nom du module quand on l'importe. D'où le garde-fou
`if __name__ == "__main__":`, qui n'exécute le bloc de test que lors d'un
lancement direct.

**XDG (`xdg-user-dir`)** — la convention qui définit les dossiers standards du
compte (Images, Documents, Bureau…), et la petite commande qui en donne le
chemin. Elle évite de coder `~/Images` en dur : selon la langue du poste, le
dossier s'appelle Pictures, Bilder, Imágenes…

---

*Lexique du projet Stickeuse QL-570 — Vitally LUBIN, FabLab Les Portes Logiques (2026) — CC BY.*
