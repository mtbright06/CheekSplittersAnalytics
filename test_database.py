from app.database.health import database_health

print()

print("===================================")

print("SharpStack Database Test")

print("===================================")

print()

if database_health():

    print("Database Connected")

else:

    print("FAILED")
