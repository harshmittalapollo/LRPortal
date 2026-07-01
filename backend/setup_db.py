import pymysql

# Try to connect with root credentials
try:
    conn = pymysql.connect(host='127.0.0.1', user='root', password='1234')
    print('Connection successful!')
    cursor = conn.cursor()
    
    # Check if database exists
    cursor.execute('SHOW DATABASES LIKE "lrportal"')
    if cursor.fetchone():
        print('Database lrportal already exists')
    else:
        print('Database lrportal does not exist - creating it...')
        cursor.execute('CREATE DATABASE lrportal')
        print('Database created successfully')
    
    conn.commit()
    conn.close()
except Exception as e:
    print(f'Error: {e}')
