import random
from django.contrib.auth.hashers import make_password

def generate_otp():
    """Generate a random 6-digit OTP"""
    otp = str(random.randint(100000, 999999))
    return otp, make_password(otp)  # Return both plain and hashed

    