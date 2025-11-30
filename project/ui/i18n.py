from typing import Dict

TRANSLATIONS: Dict[str, Dict[str, str]] = {
    'en': {'title': 'Expat Legal Aid Advisor', 'welcome': 'Welcome', 'disclaimer': 'Privacy Notice'},
    'es': {'title': 'Asesor Legal', 'welcome': 'Bienvenido', 'disclaimer': 'Aviso de privacidad'},
    'fr': {'title': 'Conseiller Juridique', 'welcome': 'Bienvenue', 'disclaimer': 'Avis de confidentialité'},
    'nl': {'title': 'Expat Juridisch Advies', 'welcome': 'Welkom', 'disclaimer': 'Privacyverklaring'},
    'de': {'title': 'Expat-Rechtsberatung', 'welcome': 'Willkommen', 'disclaimer': 'Datenschutzerklärung'}
}

LANGUAGE_MAP: Dict[str, str] = {
    'en': 'English',
    'es': 'Spanish',
    'fr': 'French',
    'nl': 'Dutch',
    'de': 'German'
}

def t(key: str, lang: str = 'en') -> str:
    """
    Get translated text for a key in specified language.
    
    Args:
        key: Translation key
        lang: Language code (default: 'en')
        
    Returns:
        Translated text or key if not found
    """
    return TRANSLATIONS.get(lang, TRANSLATIONS['en']).get(key, key)

def get_language_name(lang_code: str) -> str:
    """
    Return human-readable language name for LLM prompt.
    
    Args:
        lang_code: ISO language code (e.g., 'en', 'es')
        
    Returns:
        Full language name (e.g., 'English', 'Spanish')
    """
    return LANGUAGE_MAP.get(lang_code, lang_code)
