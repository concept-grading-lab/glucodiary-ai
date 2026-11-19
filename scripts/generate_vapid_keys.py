"""Generate VAPID EC P-256 keypair. Keep the private key secret.
This script is a development convenience, NOT a private-key backup service.
"""
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
import base64
key=ec.generate_private_key(ec.SECP256R1())
priv=key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode().strip()
pub=key.public_key().public_bytes(serialization.Encoding.X962,serialization.PublicFormat.UncompressedPoint)
pub=base64.urlsafe_b64encode(pub).decode().rstrip('=')
print('VAPID_PUBLIC_KEY='+pub)
print('VAPID_PRIVATE_KEY='+priv.replace('\n','\\n'))
print('VAPID_SUBJECT=mailto:YOUR_EMAIL_HERE')
print('Store VAPID_PRIVATE_KEY in Render environment secrets, not GitHub source code.')
