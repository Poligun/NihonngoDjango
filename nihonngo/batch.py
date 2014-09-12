from models import *
from api import *

def batch_import_from_string(string, word_separator =  '\n', component_separator = '||', meaning_separator = '#', example_separator = '*'):
    line_count = 0
    message = ''

    for word_string in string.split(word_separator):
        components = word_string.split(component_separator)
        if len(components) != 4:
            message += ''