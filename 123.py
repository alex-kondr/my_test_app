count_char = int(input("Введіть кількість літер: "))
count_char_copy = count_char

count_symbol = 1
summ_alphabet = 0

while summ_alphabet + count_symbol < count_char + 1:
    count_symbol += 1
    summ_alphabet += count_symbol

symbols = 1
start_number_symbol = 65
for i in range(count_symbol):
    j = 0
    for k in range(count_symbol):
        if k <= count_symbol - symbols * 2:
            print(" ", end="")
        if k > count_symbol - symbols * 2:
            print(" " + chr(start_number_symbol + j), end="")
            j += 1
    
    symbols += 1
    start_number_symbol += j
    print()