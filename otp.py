import random
def genotp():
    otp=""
    caps=[chr(i) for i in range(ord('A'),ord('Z'))]
    small=[chr(i) for i in range(ord('a'),ord('z'))]
    for i in range(2):
        otp+=random.choice(caps)
        otp+=str(random.randint(0,9))
        otp+=random.choice(small)
    return otp