import string, random
def gen_code(n=6):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=n))
