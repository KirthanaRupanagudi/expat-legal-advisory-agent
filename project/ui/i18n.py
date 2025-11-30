TRANSLATIONS = {
    'en': {'title': 'Expat Legal Aid Advisor', 'welcome': 'Welcome', 'disclaimer': 'Privacy Notice'},
    'es': {'title': 'Asesor Legal', 'welcome': 'Bienvenido', 'disclaimer': 'Aviso de privacidad'},
    'fr': {'title': 'Conseiller Juridique', 'welcome': 'Bienvenue', 'disclaimer': 'Avis de confidentialité'},
    'nl': {'title': 'Expat Juridisch Advies', 'welcome': 'Welkom', 'disclaimer': 'Privacyverklaring'},
    'de': {'title': 'Expat-Rechtsberatung', 'welcome': 'Willkommen', 'disclaimer': 'Datenschutzerklärung'}
}

LANGUAGE_MAP = {
    'en': 'English',
    'es': 'Spanish',
    'fr': 'French',
    'nl': 'Dutch',
    'de': 'German'
}

def t(key, lang='en'):
    return TRANSLATIONS.get(lang, TRANSLATIONS['en']).get(key, key)

def get_language_name(lang_code):
    """Return human-readable language name for LLM prompt."""
    return LANGUAGE_MAP.get(lang_code, lang_code)
