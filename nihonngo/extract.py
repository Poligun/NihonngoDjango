import urllib.request, urllib.parse
import re, codecs, os.path

from bs4 import BeautifulSoup, NavigableString

class WordExtractor(object):
    DictionaryURL = 'http://dict.hjenglish.com/jp/jc/{0}'
    UselessChars = ['\n', '\r', '   ', ' ', '【', '】', '\u3000']
    PunctuationDict = {
        ';' : '；',
        '.' : '。',
        ',' : '，',
        '(' : '（',
        ')' : '）',
    }
    ClassSeparators = '[•・·･▪，.【】]'

    @staticmethod
    def remove_useless_chars(string):
        for char in WordExtractor.UselessChars:
            string = string.replace(char, '')
        return string

    @staticmethod
    def convert_punctuation(string):
        for key, value in WordExtractor.PunctuationDict.items():
            string = string.replace(key, value)
        return string
                

    def __init__(self, mapping_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'class_mapping.txt')):
        super(WordExtractor, self).__init__()
        self.reload_mapping(mapping_file)

    def reload_mapping(self, mapping_file):
        fin = codecs.open(mapping_file, 'r', 'utf-8')
        self.class_mapping = {}
        for line in fin.read().split('\n')[:-1]:
            components = line.split(' ')
            key, value = components[0], components[1:]
            self.class_mapping[key] = value
        fin.close()

    def extract(self, word):
        url = WordExtractor.DictionaryURL.format(urllib.parse.quote(word))
        soup = BeautifulSoup(urllib.request.urlopen(url).read())
        return self.analyze(soup)

    def analyze(self, soup):
        number_of_words = len(soup.select('.jp_title_td'))
        words = []

        for i in range(number_of_words):
            word = {}

            word['kannji'] = soup.select('.jp_title_td .jpword')[i].text
            word['kana'] = WordExtractor.remove_useless_chars(soup.select('#kana_{0}'.format(i))[0].text)
            word['meanings'] = []

            meaning_span = soup.select('#comment_{0}'.format(i))[0]
            word_classes_string = ''
            meaning_string = ''

            for child in meaning_span.children:
                if child.name == 'p' and 'wordtype' in child['class']:
                    if isinstance(child.string, str):
                        word_classes_string += WordExtractor.convert_punctuation(child.string)
                elif child.name == 'img':
                    meaning_string += '*'
                elif isinstance(child, NavigableString):
                    string = WordExtractor.remove_useless_chars(child.string)
                    string = string.replace('（1）', '').replace('1、', '')
                    string = re.sub('（[0-9]+）', '#', string)
                    string = re.sub('[0-9]+、', '#', string)
                    meaning_string += WordExtractor.convert_punctuation(string)

            word['word_classes'] = []
            for component in re.sub(WordExtractor.ClassSeparators, '#', word_classes_string).split('#'):
                word_class = self.remove_useless_chars(component)
                if word_class == '':
                    continue
                elif word_class in self.class_mapping:
                    word['word_classes'] += self.class_mapping[word_class]
                else:
                    try:
                        print('Unrecognized word class(es): "{0}".'.format(word_class))
                    except:
                        pass
            word['word_classes'] = list(set(word['word_classes']))

            for entry in meaning_string.split('#'):
                if entry == '': continue
                components = entry.split('*')
                word['meanings'].append({'text': components[0], 'examples': components[1:]})

            words.append(word)

        return words


if __name__ == '__main__':
    extractor = WordExtractor()
    #words = extractor.analyze(BeautifulSoup(open('test.html').read()))
    #words = extractor.extract('錆びる')
    #words = extractor.extract('背景')
    #words = extractor.extract('容貌')
    words = extractor.extract('主人')
    print(words)
