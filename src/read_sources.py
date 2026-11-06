"""Human-readable permitted webpage sources, kept with the user's app data."""
from pathlib import Path
from typing import Dict, List

DEFAULT_SOURCES = {
    'english': [
        ('The Guardian', 'theguardian.com'), ('CNN', 'cnn.com'), ('Financial Times', 'ft.com'),
        ('Reuters', 'reuters.com'), ('BBC', 'bbc.com'), ('The New York Times', 'nytimes.com'),
        ('The Economist', 'economist.com'), ('Associated Press', 'apnews.com'), ('Law.com', 'law.com'),
        ('Law360', 'law360.com'), ('Politico', 'politico.com'), ('NPR', 'npr.org'),
        ('The Washington Post', 'washingtonpost.com'), ('CNBC', 'cnbc.com'), ('The Independent', 'independent.co.uk'),
    ],
    'german': [
        ('Die Zeit', 'zeit.de'), ('Bild', 'bild.de'), ('Der Spiegel', 'spiegel.de'),
        ('Frankfurter Allgemeine Zeitung', 'faz.net'), ('Süddeutsche Zeitung', 'sueddeutsche.de'),
        ('Handelsblatt', 'handelsblatt.com'), ('Die Welt', 'welt.de'), ('Tagesschau', 'tagesschau.de'),
        ('Legal Tribune Online', 'lto.de'), ('JUVE', 'juve.de'), ('taz', 'taz.de'),
        ('Focus', 'focus.de'), ('Stern', 'stern.de'), ('n-tv', 'n-tv.de'), ('RND', 'rnd.de'),
    ],
    'french': [
        ('Le Monde', 'lemonde.fr'), ('Le Figaro', 'lefigaro.fr'), ('Libération', 'liberation.fr'),
        ("L’Équipe", 'lequipe.fr'), ('Les Échos', 'lesechos.fr'), ('Franceinfo', 'francetvinfo.fr'),
        ('Ouest-France', 'ouest-france.fr'), ('Mediapart', 'mediapart.fr'), ('Le Parisien', 'leparisien.fr'),
        ('20 Minutes', '20minutes.fr'), ("L’Express", 'lexpress.fr'), ('Le Point', 'lepoint.fr'),
        ('La Croix', 'la-croix.com'), ('Challenges', 'challenges.fr'), ('Actu-Juridique', 'actu-juridique.fr'),
    ],
}


def initialize_sources(root: Path) -> None:
    folder = root / 'read-sources'
    folder.mkdir(parents=True, exist_ok=True)
    for language, sources in DEFAULT_SOURCES.items():
        try:
            with (folder / f'{language}.txt').open('x', encoding='utf-8') as file:
                file.write('# Allowed webpage sources: publication | domain\n')
                for name, domain in sources:
                    file.write(f'{name} | {domain}\n')
        except FileExistsError:
            pass


def read_sources(root: Path, language: str) -> List[Dict[str, str]]:
    if language not in DEFAULT_SOURCES:
        return []
    path = root / 'read-sources' / f'{language}.txt'
    sources = []
    for line in path.read_text(encoding='utf-8').splitlines():
        if not line.strip() or line.lstrip().startswith('#') or '|' not in line:
            continue
        name, domain = (part.strip() for part in line.split('|', 1))
        domain = domain.lower().rstrip('.')
        if name and domain and all(part and part.replace('-', '').isalnum() for part in domain.split('.')):
            sources.append({'name': name, 'domain': domain})
    return sources
