
import os
import sys

try:
    with open('syspath.txt', 'r', encoding='utf-16') as f:
        print(f.read())
except:
    try:
        with open('syspath.txt', 'r', encoding='utf-8') as f:
            print(f.read())
    except:
        with open('syspath.txt', 'rb') as f:
            print(f.read())
