import codecs

if __name__ == '__main__':
    with open('api.txt', 'w') as fout:
        fout.write('\n'.join([l for l in codecs.open('api_new.py', 'r', 'utf-8').read().split('\n') if 'def api_' in l]))
        fout.close()
