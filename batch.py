from nihonngo.api import *
from nihonngo.models import *

WORD_LIST_PATH = '/Users/zhaoyuhan/Documents/word_list.txt'

def batch_insert(input_file, line_range = None):
	lines = open(input_file, 'r').read().split('\n')[:-1]
	
	if not line_range:
		line_range = range(len(lines))

	for i in line_range:
		components = lines[i].split('||')

		message, new_word = api_create_word(components[0], components[1])
		print(message.message)

		for word_class in components[2].replace('，', ',').split(','):
			message, index = api_get_class_index(word_class)
			print(message.message)

			if (message.success):
				message, new_word_class = api_create_word_class(new_word.id, index)
				print(message.message)

		for meaning in components[3].split('#'):
			items = meaning.split('*')

			message, new_meaning = api_create_meaning(new_word.id, items[0])
			print(message.message)

			for example in items[1:]:
				message, new_example = api_create_example(new_meaning.id, example)
				print(message.message)

def clean_db():
	Word.objects.all().delete()
	WordClass.objects.all().delete()
	Meaning.objects.all().delete()
	Example.objects.all().delete()

def test():
	batch_insert(WORD_LIST_PATH)
