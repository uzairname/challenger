#minecraft is

client = []


#wut

import string
import random

# Generate a random string of fixed length
def gen_random(length):
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(length))

