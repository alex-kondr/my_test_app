string = 'D010200059'
encode_str = ''

for char in string:
    encode_str += hex(ord(char))[2:]

print(encode_str)