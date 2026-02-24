#!/usr/bin/env python3
"""
Convert JWK private key to PEM format for Okta SDK.
"""

import json
import base64
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa

def jwk_to_pem(jwk_dict):
    """Convert JWK to PEM format."""

    # Decode base64url encoded values
    def decode_value(val):
        # Add padding if needed
        val = val + '=' * (4 - len(val) % 4)
        return int.from_bytes(base64.urlsafe_b64decode(val), 'big')

    n = decode_value(jwk_dict['n'])
    e = decode_value(jwk_dict['e'])
    d = decode_value(jwk_dict['d'])
    p = decode_value(jwk_dict['p'])
    q = decode_value(jwk_dict['q'])
    dmp1 = decode_value(jwk_dict['dp'])
    dmq1 = decode_value(jwk_dict['dq'])
    iqmp = decode_value(jwk_dict['qi'])

    # Create RSA private key
    public_numbers = rsa.RSAPublicNumbers(e=e, n=n)
    private_numbers = rsa.RSAPrivateNumbers(
        p=p, q=q, d=d,
        dmp1=dmp1, dmq1=dmq1, iqmp=iqmp,
        public_numbers=public_numbers
    )

    private_key = private_numbers.private_key(backend=default_backend())

    # Convert to PEM format
    pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )

    return pem.decode('utf-8')

if __name__ == "__main__":
    # Your JWK private key
    jwk = {
        "kty": "RSA",
        "use": "sig",
        "kid": "1DpncTCBrFUmw9hWNrwiEDqao4zNJGpjmjP9k4lRTBk",
        "n": "mAqBIrfxR1GP7wE6D9qYdAisipvfGs48LTU27QLfZgFRAOF4bhMC4nfYvww9qFkViR0D3PsB3s4yVy1ze_7ePMwldx59rIM3iig-UcNtE-9CFQDnT0ZrqQWn8R49jhmPx_hzQIIeGk0hUgOTrmGYOTWNZfQMwhzVJZ8I64ZZcjhcaZjZ0B1X-r7gBngTF7i_Fe5pRxFF0_arwl1hWZdeQnATtBdEWVtQ5AzoJenRqF2k4RO74JjGtsL1d809ARCqjqrE5NyRlXnklmw-3voP6rZLGWQIq16CwRPiuop9p16B-VPe3W3EMGMDVVFpQ8HZFllMzy-g6gPgpYNeCZeBOQ",
        "e": "AQAB",
        "d": "GF_SvQilJyxVuVjGgKUoPK3pT11Wwprefdbio9OKkfVTEaOT5X2pwDm7Z0FknxkNAUrEBEi_T4NaAazZLz84TKHjvbmHJ0FwBXeXKg987K22N9zJuGVPPC0ac-bHsoC5krLrcyOJBOlplpbZNaMSvtUtgnNCGlp590qMKQoES_Gq59brUD60C81A-pLYwwJ_FbpUqcbmzzgYEmrVikOnPrOi3nF-bzbNHJdy8N1kDVy8ceLhjcAjdmE9luH3iBS9HBl3UQXz9j60LtU9FSAJSaEeg-BbLiHKB0h0_c5QghkaXJcEtRuuDV1aiZt-qEyb5tqgNCd3gjWZt4HE-O1GSQ",
        "p": "x-ehaUPq_7OL7avMPPfX11RM3A2iMWPTQXVzhUFRIV1BZfwVHJnuf0dHFJG6CdIYD-9BC58cm7Aury9whRrbRQdyjjCO_y51roxh9coRdAE3LXfHJd0zJ5CVfjt9kquMkp7JESBZSkzHzlFIHQ6To_y9-BjZUlazHD6uLjpEls0",
        "q": "wrSHro4GEKFSMGf0c2Klm9COpXpa7Vosw79NJtWwnnjOTDRjKKTr5BvTvRTd7O2IwEOfm178xzLDAk-iTzKsnThoBYWl4ucEvJlNHGXivS39xBlZj8qHBEZNMPGivGkS63NQIrYjce67SYInPKSZYDRDKV7ogqc4QcYODqSkHB0",
        "dp": "SbvhKH-ZtVkXesHMYoyUO2Nnuh75PThx2ook4vjVoPXRwnk5nEQW2TGEQU0DDs5Ee9Qm7M9ycOaKQanA2geu6wY1NccpZ2xOkeRL2an_yAcOwCGW_htZ2_UTfu0YgzntbsNMrJl-9c3eQPZwH--Ze3ok49beieVayUdBXeG2HN0",
        "dq": "ptjM7GgICngzVge_EqGWCM_PbT5MbNi5Q4TLOFwl3aboIaVC07F_8xlleMJI6p8icJ-CRkI_mvOE6JYVIIjsIk4T1aeRX79X78Xurkcg5bxjmYefl_iVerRDsY1fRtVDwUAvi49JEHjjRTqjJPRn-mjOpMUPueZR7wspQKMVfoE",
        "qi": "TCAGxezqIrfgCef1J6aoVHWOoRj8IRRcuR8AqpIRXBBJEcEicSOY0E9_gJ-ahxZNS6qQ-kElUmiXkTs9I5ZeTeUnTxWMunfpcknlQTWXYuTYA5XQ4kOM-DyHYllH7-quCm8GyIN5dLTd_UoyE5HiBQho1EqdU1ZUGmi5bNFhm54"
    }

    print("Converting JWK to PEM format...")
    print()

    pem = jwk_to_pem(jwk)

    print("PEM Private Key:")
    print("=" * 70)
    print(pem)
    print("=" * 70)
    print()
    print("Copy the above key (including BEGIN/END lines) to use in your config.")
