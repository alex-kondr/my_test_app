count_char = int(input("Введіть кількість літер: "))
count_char_copy = count_char

count_symbol = 1
summ_alphabet = 0

while summ_alphabet + count_symbol < count_char + 1:
    count_symbol += 1
    summ_alphabet += count_symbol
print(count_symbol)

count_alpha = 0
count = count_symbol
for i in range(count_char_copy):
    count_char -= 1
    if count_alpha == 0:
        count_alpha += count - count_symbol
        if count_char_copy < 7:
            if count_alpha == 0:
                print(" " * (count_symbol-1)*2 + chr(65 + i))
            else:
                if count_char == 0:
                    print(" " * (count_symbol-1)*2 + chr(65 + i), end="")
                else:
                    print(" " * (count_symbol-1)*2 + chr(65 + i), end=" ")
        elif count_char_copy < 11:
            if count_alpha == 0:
                print(" " * ((count_symbol-1)*2) + chr(65 + i))
            else:
                if count_char == 0:
                    print(" " * ((count_symbol-1)*2) + chr(65 + i), end="")
                else:
                    print(" " * ((count_symbol-1)*2) + chr(65 + i), end=" ")
        elif count_char_copy < 13:
            if count_alpha == 0:
                print(" " * ((count_symbol-1)*2+1) + chr(65 + i))
            else:
                if count_char == 0:
                    print(" " * ((count_symbol-1)*2+1) + chr(65 + i), end="")
                else:
                    print(" " * ((count_symbol-1)*2+1) + chr(65 + i), end=" ")
        elif count_char_copy < 16:
            if count_alpha == 0:
                print(" " * ((count_symbol-1)*2) + chr(65 + i))
            else:
                if count_char == 0:
                    print(" " * ((count_symbol-1)*2) + chr(65 + i), end="")
                else:
                    print(" " * ((count_symbol-1)*2) + chr(65 + i), end=" ")
        elif count_char_copy < 19:
            if count_alpha == 0:
                print(" " * ((count_symbol-1)*2+1) + chr(65 + i))
            else:
                if count_char == 0:
                    print(" " * ((count_symbol-1)*2+1) + chr(65 + i), end="")
                else:
                    print(" " * ((count_symbol-1)*2+1) + chr(65 + i), end=" ")
        elif count_char_copy < 22:
            if count_alpha == 0:
                print(" " * ((count_symbol-1)*2) + chr(65 + i))
            else:
                if count_char == 0:
                    print(" " * ((count_symbol-1)*2) + chr(65 + i), end="")
                else:
                    print(" " * ((count_symbol-1)*2) + chr(65 + i), end=" ")
        elif count_char_copy < 30:
            if count_alpha == 0:
                print(" " * ((count_symbol-1)*2+1) + chr(65 + i))
            else:
                if count_char == 0:
                    print(" " * ((count_symbol-1)*2+1) + chr(65 + i), end="")
                else:
                    print(" " * ((count_symbol-1)*2+1) + chr(65 + i), end=" ")

        count_symbol -= 1
    else:
        count_alpha -= 1
        if count_char == 0:
            print(chr(65 + i), end="")
            break
        else:
            if count_alpha == 0:
                print(chr(65 + i))
            else:
                print(chr(65 + i), end=" ")
