'''
Created on

@author: Raja CSP Raman

source:
    https://chatgpt.com/share/a67b7b0e-7c54-444a-89d1-00fca80aed25
'''

import random

def mutate_word(word, num_variants=5):
    letters = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
    variants = []

    for _ in range(num_variants):
        # Randomly decide to either substitute or insert a character
        if random.choice([True, False]):
            # Substitute a character
            mutated = list(word)
            index_to_mutate = random.randint(0, len(mutated) - 1)
            mutated[index_to_mutate] = random.choice(letters)
        else:
            # Insert a character
            mutated = list(word)
            index_to_insert = random.randint(0, len(mutated))
            mutated.insert(index_to_insert, random.choice(letters))

        # Join the list back into a string
        mutated_word = ''.join(mutated)
        variants.append(mutated_word)

    return variants

def startpy():

    # print("Tact101")

    # Example usage
    input_word = 'Toronto'
    output_variants = mutate_word(input_word)
    for variant in output_variants:
        print(variant)

    input_word = 'Montreal'
    output_variants = mutate_word(input_word)
    for variant in output_variants:
        print(variant)

if __name__ == '__main__':
    startpy()