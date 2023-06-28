text = '''
C makes it easy for you to shoot yourself in the foot. C++ makes that harder, but when you do, it blows away your whole leg. (с) Bjarne Stroustrup
'''


def find_unique_sym(text):
    words = (text
             .replace('-', '')
             .replace('"', '')
             .replace('.', '')
             .split()
             )
    
    unique_char = []
    
    for word in words:
        chars = list(word)
        for char in chars:
            if chars.count(char) == 1:
                unique_char.append(char)
                break
            
    for char in unique_char:
        if unique_char.count(char) == 1:
            return char


print(find_unique_sym(text))
