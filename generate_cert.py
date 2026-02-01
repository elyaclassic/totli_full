from OpenSSL import crypto

# Create a key pair
key = crypto.PKey()
key.generate_key(crypto.TYPE_RSA, 2048)

# Create a self-signed cert
cert = crypto.X509()
cert.get_subject().CN = "10.243.49.144"
cert.set_serial_number(1000)
cert.gmtime_adj_notBefore(0)
cert.gmtime_adj_notAfter(365*24*60*60)  # Valid for 1 year
cert.set_issuer(cert.get_subject())
cert.set_pubkey(key)
cert.sign(key, 'sha256')

# Save certificate
with open("cert.pem", "wb") as f:
    f.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))

# Save private key
with open("key.pem", "wb") as f:
    f.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, key))

print("✅ SSL sertifikat yaratildi!")
print("   cert.pem - Sertifikat")
print("   key.pem - Private key")
