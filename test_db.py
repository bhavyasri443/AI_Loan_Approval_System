import mysql.connector

try:
    conn = mysql.connector.connect(
        host="127.0.0.1",
        port=3306,
        user="root",
        password="bhavya123"
    )

    print("Connected!")

except Exception as e:
    print(e)