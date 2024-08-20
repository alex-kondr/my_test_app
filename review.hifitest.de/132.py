string = "Fernseher Google TV Ultra HD und 8K"

cats = string.split()
cats_ = []
for i, cat in enumerate(cats):
    if cat[0].isupper():
        cats_.append(cat)
    else:
        cats_[i-1] += ' ' + ' '.join(cats[i:])
        break

print(cats_)