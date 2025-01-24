import mysql.connector

try:
    connection = mysql.connector.connect(
        host='localhost',
        database='infy',
        user='root',
        password='root',
        use_pure=True
    )
    if connection.is_connected():
        print("Successfully connected to MySQL!")
        print("MySQL Server version:", connection.get_server_info())
except mysql.connector.Error as e:
    print(f"Error connecting to MySQL: {e}")
