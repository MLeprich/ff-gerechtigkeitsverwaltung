from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """Hole einen Wert aus einem Dictionary mit einem variablen Key"""
    if dictionary is None:
        return 0
    return dictionary.get(key, 0)
